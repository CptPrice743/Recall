"""Instagram ingestion: Reels (video) and posts (images/carousels).

Strategy (D28, D29):
- Reels / videos: yt-dlp extracts audio as .m4a → Groq Whisper transcribes it.
  If transcript is empty (music-only), fall back to post caption text.
- Image posts / carousels: each image is downloaded and described by Gemini
  Vision (D29). Captions are joined into body_text and embedded as text.

yt-dlp uses Firefox cookies (same approach as Reddit, D24) so that private
or semi-private Instagram content is accessible.

Post type detection:
- yt-dlp returns entries (playlist) → carousel of images or mixed
- info contains a non-zero "duration" → video/reel
- Otherwise → single image or text-only post

Note on image-only posts: yt-dlp raises "No video formats found" for
pure image posts. We set `ignore_no_formats_error=True` and
`extract_flat="discard_in_playlist"` so metadata is returned even when
no video stream exists. Image URLs are collected from entry thumbnails.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from .config import load_settings
from .groq_transcribe import transcribe_audio
from .media_download import download_audio_m4a, download_images
from .source_types import SourceDocument


def fetch_instagram_document(url: str) -> SourceDocument:
    """Fetch and return a SourceDocument for an Instagram post or Reel."""
    settings = load_settings()
    info = _extract_with_cookies(url)

    title = _best_title(info)
    creator = (info.get("uploader") or info.get("channel") or "Unknown").strip()
    caption = (info.get("description") or "").strip()
    upload_date = info.get("upload_date") or ""
    source_url = info.get("webpage_url") or url
    duration = info.get("duration")  # None or 0 for image posts

    # ── Determine post type ──────────────────────────────────────────────────
    entries = info.get("entries") or []
    is_video = bool(duration and float(duration) > 0)

    if is_video:
        body_text, section_title = _handle_video(
            url=url,
            caption=caption,
            settings=settings,
        )
    else:
        # Collect image URLs: from carousel entries or thumbnail fallback
        image_urls = _collect_image_urls_from_entries(entries)
        if not image_urls:
            # Single image post — thumbnail is the image
            thumb = info.get("thumbnail") or ""
            if thumb:
                image_urls = [thumb]

        if image_urls:
            body_text, section_title = _handle_images(
                image_urls=image_urls,
                caption=caption,
                settings=settings,
            )
        else:
            body_text = caption or "No caption text was returned."
            section_title = "Caption"

    return SourceDocument(
        source="instagram",
        source_folder="Instagram",
        source_url=source_url,
        title=title,
        creator=creator,
        body_text=body_text,
        body_section_title=section_title,
        published=upload_date,
        duration_seconds=int(duration) if is_video and duration else None,
        extra_frontmatter={"extractor": str(info.get("extractor_key") or "")},
    )


# ── Private helpers ──────────────────────────────────────────────────────────


def _extract_with_cookies(url: str) -> dict:
    """Run yt-dlp with Firefox cookies.

    Uses ignore_no_formats_error so image-only posts don't raise an exception.
    Falls back to no-cookies for public posts if Firefox session is unavailable.
    """
    from yt_dlp import YoutubeDL

    opts: dict = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": False,
        "extract_flat": "discard_in_playlist",
        "ignore_no_formats_error": True,
        "cookiesfrombrowser": ("firefox",),
    }

    for attempt_cookies in (True, False):
        current_opts = dict(opts)
        if not attempt_cookies:
            current_opts.pop("cookiesfrombrowser", None)
        try:
            with YoutubeDL(current_opts) as ydl:
                result = ydl.extract_info(url, download=False)
            if result:
                return result
        except Exception:  # noqa: BLE001
            if not attempt_cookies:
                raise

    raise RuntimeError(f"yt-dlp could not extract info for Instagram URL: {url}")


def _best_title(info: dict) -> str:
    return (
        info.get("title")
        or info.get("description", "")[:80]
        or "Untitled Instagram post"
    ).strip()


def _handle_video(*, url: str, caption: str, settings) -> tuple[str, str]:
    """Download audio and transcribe via Groq. Falls back to caption if silent."""
    if not settings.groq_api_key:
        print("[instagram] GROQ_API_KEY not set; using post caption as body text.")
        return (caption or "No caption text was returned."), "Caption"

    with tempfile.TemporaryDirectory(prefix="recall_ig_") as tmp:
        tmp_path = Path(tmp)
        try:
            audio_path = download_audio_m4a(url, tmp_path, browser_cookies=True)
            transcript = transcribe_audio(audio_path, api_key=settings.groq_api_key)
        except Exception as exc:  # noqa: BLE001
            print(f"[instagram] audio transcription failed ({exc}); using caption.")
            transcript = ""

    if transcript:
        body = transcript
        if caption:
            body = f"{caption}\n\n---\n\n{body}"
        return body, "Reel Transcript"
    else:
        return (caption or "No caption text was returned."), "Caption"


def _handle_images(
    *,
    image_urls: list[str],
    caption: str,
    settings,
) -> tuple[str, str]:
    """Download images and caption each with Gemini Vision (D29)."""
    from .gemini import GeminiClient

    if not image_urls:
        return (caption or "No image or caption text was returned."), "Caption"

    gemini = GeminiClient(settings.gemini_api_key)

    with tempfile.TemporaryDirectory(prefix="recall_ig_img_") as tmp:
        tmp_path = Path(tmp)
        local_images = download_images(image_urls, tmp_path)

        captions: list[str] = []
        for idx, img_path in enumerate(local_images, start=1):
            try:
                img_caption = gemini.caption_image(img_path, model=settings.summary_model)
                label = f"**Image {idx}:**" if len(local_images) > 1 else ""
                captions.append(f"{label}\n{img_caption}".strip())
            except Exception as exc:  # noqa: BLE001
                print(f"[instagram] Gemini Vision failed for image {idx} ({exc}); skipping.")

    if not captions:
        return (caption or "No image content could be described."), "Caption"

    body_parts: list[str] = []
    if caption:
        body_parts.append(caption)
    body_parts.extend(captions)
    body = "\n\n---\n\n".join(body_parts)
    section_title = "Image Captions" if len(local_images) > 1 else "Image Caption"
    return body, section_title


def _collect_image_urls_from_entries(entries: list[dict]) -> list[str]:
    """Extract image URLs from carousel playlist entries.

    yt-dlp returns flat entry dicts for image carousels. The image URL
    may be in 'url', 'thumbnail', or 'thumbnails'.
    """
    urls: list[str] = []
    for entry in entries:
        # Prefer direct URL if it looks like an image (not a video embed)
        direct = entry.get("url") or ""
        thumb = entry.get("thumbnail") or ""
        thumbnails = entry.get("thumbnails") or []
        best_thumb = thumbnails[-1].get("url", "") if thumbnails else ""

        candidate = direct or best_thumb or thumb
        if candidate and candidate not in urls:
            urls.append(candidate)
    return urls
