from __future__ import annotations

from .gemini import GeminiClient
from .text import approximate_token_count, chunk_text


def summarize_source_text(
    *,
    gemini: GeminiClient,
    source_label: str,
    title: str,
    text: str,
    model: str,
    comment_context: str | None = None,
) -> str:
    """Summarise a source document's body text.

    comment_context (optional)
    --------------------------
    Raw comment/discussion text that Gemini should consider when writing the
    summary — so it can describe the community response and general consensus —
    but that is deliberately NOT embedded into Qdrant or written into the note
    body.  It is appended to the summarisation prompt only.

    D9: one token-threshold rule applies to body text alone; comment_context
    is appended as-is after chunking decisions have been made for the main text.
    """
    # D9: branch on token count of the *main* body text only.
    if approximate_token_count(text) <= 2500:
        return gemini.summarize_source_text(
            source_label=source_label,
            title=title,
            source_text=text,
            model=model,
            comment_context=comment_context,
        )

    chunks = chunk_text(text, chunk_tokens=2200, overlap_tokens=100)
    print(f"{source_label} text is long; summarising {len(chunks)} chunk(s) before combining.")
    chunk_summaries = [
        gemini.summarize_source_chunk(
            source_label=source_label,
            title=title,
            chunk=chunk,
            chunk_number=index,
            model=model,
        )
        for index, chunk in enumerate(chunks, start=1)
    ]
    return gemini.combine_source_summaries(
        source_label=source_label,
        title=title,
        chunk_summaries=chunk_summaries,
        model=model,
        comment_context=comment_context,
    )
