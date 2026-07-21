from __future__ import annotations

from google import genai
from google.genai import types

from .config import (
    DOCUMENT_TASK_TYPE,
    EMBEDDING_DIMENSION,
    EMBEDDING_MODEL,
    QUERY_TASK_TYPE,
)


class GeminiClient:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)

    def embed_document(self, text: str) -> list[float]:
        return self._embed(text, DOCUMENT_TASK_TYPE)

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text, QUERY_TASK_TYPE)

    def caption_image(self, image_path: "Path", *, model: str) -> str:  # noqa: F821
        """Generate a descriptive text caption for a local image file (D29).

        Used for intentionally saved Instagram/X images and carousels.
        The caption is written into the note body and embedded as text,
        giving better retrieval than direct multimodal embedding for
        text-heavy content (infographics, slides, product shots).

        Args:
            image_path: Path to a local image file.
            model: Gemini model name (summary_model from settings).

        Returns:
            A detailed prose description of the image.
        """
        from pathlib import Path
        from google.genai import types as _types

        image_bytes = Path(image_path).read_bytes()
        # Guess MIME type from extension
        ext = Path(image_path).suffix.lower()
        mime_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".gif": "image/gif",
        }
        mime_type = mime_map.get(ext, "image/jpeg")

        prompt = (
            "Describe this image in detail for a personal knowledge archive. "
            "Include: the main subject, any visible text or numbers, key objects, "
            "colours, layout, and any information that would help retrieve this image "
            "later via a natural-language query. "
            "If this is an infographic or slide, transcribe or summarise all text content. "
            "Write as clear, searchable prose — not bullet points."
        )
        response = self.client.models.generate_content(
            model=model,
            contents=[
                _types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                prompt,
            ],
        )
        text = getattr(response, "text", None)
        if not text:
            raise RuntimeError("Gemini Vision caption response did not contain text")
        return text.strip()

    def generate_note_title(self, *, body_text: str, model: str, max_words: int = 7) -> str:
        """Generate a short, descriptive note title from body content.

        Used as the human-readable prefix in the note filename so that the
        Obsidian vault is navigable without needing to open every note.
        e.g. "carbonara-traditional-technique--abc123ef.md"

        Args:
            body_text: The note body text (transcript, caption, article text, etc.)
            model: Gemini generative model name.
            max_words: Maximum number of words in the title (default 7).

        Returns:
            A plain-text title of at most max_words words. Falls back to an
            empty string if the API call fails — the caller must handle that.
        """
        snippet = body_text[:4000]  # enough context, not the whole note
        prompt = (
            f"Write a descriptive title for this content in {max_words} words or fewer.\n"
            "Rules:\n"
            "- Be specific, not generic (avoid words like 'post', 'video', 'note', 'content', 'article')\n"
            "- Use plain English words, no hashtags, no emojis, no punctuation\n"
            "- Output ONLY the title, nothing else\n"
            "\n"
            f"Content:\n{snippet}"
        )
        try:
            response = self.client.models.generate_content(model=model, contents=prompt)
            title = getattr(response, "text", "") or ""
            # Strip any quotes/punctuation Gemini sometimes wraps the title in
            title = title.strip().strip('"\' ')
            # Keep only the first line if the model adds explanation
            title = title.splitlines()[0].strip() if title else ""
            return title
        except Exception:  # noqa: BLE001
            return ""

    def summarize_youtube(self, *, title: str, transcript: str, model: str) -> str:
        return self.summarize_source_text(
            source_label="YouTube",
            title=title,
            source_text=transcript,
            model=model,
        )

    def summarize_transcript_chunk(self, *, title: str, chunk: str, chunk_number: int, model: str) -> str:
        return self.summarize_source_chunk(
            source_label="YouTube",
            title=title,
            chunk=chunk,
            chunk_number=chunk_number,
            model=model,
        )

    def combine_youtube_summaries(self, *, title: str, chunk_summaries: list[str], model: str) -> str:
        return self.combine_source_summaries(
            source_label="YouTube",
            title=title,
            chunk_summaries=chunk_summaries,
            model=model,
        )

    def summarize_source_text(
        self,
        *,
        source_label: str,
        title: str,
        source_text: str,
        model: str,
        comment_context: str | None = None,
    ) -> str:
        comment_block = ""
        if comment_context:
            comment_block = f"""

Community discussion (comments — use for context only; do NOT quote individual comments verbatim):
{comment_context}
"""
        prompt = f"""Summarise this {source_label} source for a personal knowledge archive.

Write a concise but useful Markdown summary with:
- a 2-4 sentence overview of the post/content itself
- key details worth retrieving later (names, products, places, links, claims)
- if community discussion is provided below: a short "Community response" section
  describing the general consensus, dominant opinions, and notable disagreements —
  written as a prose summary, not a list of individual comments

Title: {title}

Source text:
{source_text}{comment_block}"""
        response = self.client.models.generate_content(model=model, contents=prompt)
        text = getattr(response, "text", None)
        if not text:
            raise RuntimeError("Gemini summary response did not contain text")
        return text.strip()

    def summarize_source_chunk(
        self,
        *,
        source_label: str,
        title: str,
        chunk: str,
        chunk_number: int,
        model: str,
    ) -> str:
        prompt = f"""Summarize chunk {chunk_number} from this {source_label} source.

Keep details that may be useful for retrieval later: entities, products, places, claims, examples, and concrete facts.

Title: {title}

Source chunk:
{chunk}
"""
        response = self.client.models.generate_content(model=model, contents=prompt)
        text = getattr(response, "text", None)
        if not text:
            raise RuntimeError("Gemini chunk summary response did not contain text")
        return text.strip()

    def combine_source_summaries(
        self,
        *,
        source_label: str,
        title: str,
        chunk_summaries: list[str],
        model: str,
        comment_context: str | None = None,
    ) -> str:
        joined = "\n\n".join(
            f"Chunk {index} summary:\n{summary}"
            for index, summary in enumerate(chunk_summaries, start=1)
        )
        comment_block = ""
        if comment_context:
            comment_block = f"""

Community discussion (comments — use for context only; do NOT quote individual comments verbatim):
{comment_context}
"""
        prompt = f"""Combine these {source_label} chunk summaries into one concise Markdown archive note.

Use:
- a 2-4 sentence overview
- key details worth retrieving later
- notable names, products, places, links, or claims if present
- if community discussion is provided below: a short "Community response" section
  describing the general consensus and notable opinions as prose

Title: {title}

{joined}{comment_block}"""
        response = self.client.models.generate_content(model=model, contents=prompt)
        text = getattr(response, "text", None)
        if not text:
            raise RuntimeError("Gemini combined summary response did not contain text")
        return text.strip()

    def _embed(self, text: str, task_type: str) -> list[float]:
        # D19: document and query embeddings intentionally use different task_type values.
        response = self.client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=EMBEDDING_DIMENSION,
            ),
        )
        return _extract_embedding_values(response)


def _extract_embedding_values(response: object) -> list[float]:
    embeddings = getattr(response, "embeddings", None)
    if embeddings:
        values = getattr(embeddings[0], "values", None)
        if values:
            return list(values)

    embedding = getattr(response, "embedding", None)
    if embedding is not None:
        values = getattr(embedding, "values", None)
        if values:
            return list(values)

    raise RuntimeError("Gemini embedding response shape was not recognized")
