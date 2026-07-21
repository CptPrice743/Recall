"""X (Twitter) post and thread ingestion.

Strategy (D28, D29, D30):
- Text-only posts: tweet text becomes body_text directly.
- Posts with video: yt-dlp extracts audio as .m4a →
  Groq Whisper transcribes. If transcript is empty/short, fall back to
  tweet text (D30 — silent demo videos handled via post text only).
- Posts with images: X's yt-dlp extractor raises "No video could be found"
  for image tweets. We catch this and use a direct page-scrape approach to
  extract pbs.twimg.com image URLs from the tweet's HTML (Open Graph tags),
  then caption each with Gemini Vision (D29).
- Threads: yt-dlp returns a playlist for threads. Each tweet is processed
  individually (text + optional media) and concatenated in the note.

Auth: yt-dlp with Firefox cookies (same pattern as Reddit/Instagram, D24).
X/pbs.twimg.com image URLs are generally public — no auth needed to
download them once we have the URL.
"""

from __future__ import annotations

import re
import tempfile
import urllib.request
from pathlib import Path

from .config import load_settings
from .groq_transcribe import transcribe_audio
from .media_download import download_audio_m4a, download_images
from .source_types import SourceDocument

# Maximum number of tweets to process in a thread
_MAX_THREAD_TWEETS = 20

# Regex to extract image URLs from pbs.twimg.com in page source
_TWIMG_RE = re.compile(r'https://pbs\.twimg\.com/media/[A-Za-z0-9_\-]+\?format=\w+&name=\w+')


def fetch_x_document(url: str) -> SourceDocument:
    """Fetch and return a SourceDocument for an X post or thread."""
    settings = load_settings()
    info = _extract_with_cookies(url)

    if info and info.get("_type") == "playlist":
        return _process_thread(url=url, info=info, settings=settings)
    elif info:
        return _process_single_tweet(url=url, info=info, settings=settings)
    else:
        # Fallback: couldn't extract any info — try image-scrape approach
        return _fallback_image_tweet(url=url, settings=settings)


# ── Single tweet ─────────────────────────────────────────────────────────────


def _process_single_tweet(*, url: str, info: dict, settings) -> SourceDocument:
    title = _best_title(info)
    creator = _creator(info)
    tweet_text = (info.get("description") or "").strip()
    upload_date = info.get("upload_date") or ""
    source_url = info.get("webpage_url") or url
    duration = info.get("duration")

    is_video = bool(duration and float(duration) > 0)
    # Check for image formats in the yt-dlp info
    image_urls = _collect_image_urls(info)

    if is_video:
        body_text, section_title = _handle_video(
            url=source_url,
            tweet_text=tweet_text,
            settings=settings,
        )
    elif image_urls:
        body_text, section_title = _handle_images(
            image_urls=image_urls,
            tweet_text=tweet_text,
            settings=settings,
        )
    else:
        body_text = tweet_text or "No post text was returned."
        section_title = "Post Content"

    return SourceDocument(
        source="x",
        source_folder="X",
        source_url=source_url,
        title=title,
        creator=creator,
        body_text=body_text,
        body_section_title=section_title,
        published=upload_date,
        duration_seconds=int(duration) if is_video and duration else None,
        extra_frontmatter={"extractor": str(info.get("extractor_key") or "")},
    )


def _fallback_image_tweet(*, url: str, settings) -> SourceDocument:
    """Fallback for image-only tweets where yt-dlp returns nothing.

    Scrapes the tweet page for pbs.twimg.com image URLs via Open Graph
    meta tags and page source regex, then captions with Gemini Vision.
    """
    tweet_text, image_urls = _scrape_tweet_page(url)
    if image_urls:
        body_text, section_title = _handle_images(
            image_urls=image_urls,
            tweet_text=tweet_text,
            settings=settings,
        )
    else:
        body_text = tweet_text or "No post content could be retrieved."
        section_title = "Post Content"

    return SourceDocument(
        source="x",
        source_folder="X",
        source_url=url,
        title=(tweet_text[:80] if tweet_text else "Untitled X post"),
        creator="Unknown",
        body_text=body_text,
        body_section_title=section_title,
        published="",
        duration_seconds=None,
        extra_frontmatter={"extractor": "twitter_fallback"},
    )


# ── Thread ────────────────────────────────────────────────────────────────────


def _process_thread(*, url: str, info: dict, settings) -> SourceDocument:
    """Process a thread: all tweets concatenated into one note."""
    entries = (info.get("entries") or [])[:_MAX_THREAD_TWEETS]
    thread_title = _best_title(info) or "X Thread"
    creator = _creator(info)
    upload_date = info.get("upload_date") or ""
    source_url = info.get("webpage_url") or url

    tweet_sections: list[str] = []
    for idx, entry in enumerate(entries, start=1):
        tweet_text = (entry.get("description") or "").strip()
        duration = entry.get("duration")
        is_video = bool(duration and float(duration) > 0)
        image_urls = _collect_image_urls(entry)
        tweet_url = entry.get("webpage_url") or entry.get("url") or url

        if is_video:
            body, _ = _handle_video(
                url=tweet_url,
                tweet_text=tweet_text,
                settings=settings,
            )
        elif image_urls:
            body, _ = _handle_images(
                image_urls=image_urls,
                tweet_text=tweet_text,
                settings=settings,
            )
        else:
            body = tweet_text or "(no text)"

        tweet_sections.append(f"**Tweet {idx}:**\n{body}")

    body_text = "\n\n---\n\n".join(tweet_sections) if tweet_sections else "No thread content retrieved."

    return SourceDocument(
        source="x",
        source_folder="X",
        source_url=source_url,
        title=thread_title,
        creator=creator,
        body_text=body_text,
        body_section_title="Thread",
        published=upload_date,
        duration_seconds=None,
        extra_frontmatter={
            "extractor": str(info.get("extractor_key") or ""),
            "thread_tweet_count": len(entries),
        },
    )


# ── Media handlers ────────────────────────────────────────────────────────────


def _handle_video(*, url: str, tweet_text: str, settings) -> tuple[str, str]:
    """Download audio and transcribe via Groq (D28).

    D30: if transcript is empty (silent demo, music, no speech), fall back
    to tweet text only.
    """
    if not settings.groq_api_key:
        print("[x_post] GROQ_API_KEY not set; using tweet text as body text.")
        return (tweet_text or "No post text was returned."), "Post Content"

    with tempfile.TemporaryDirectory(prefix="recall_x_") as tmp:
        tmp_path = Path(tmp)
        try:
            audio_path = download_audio_m4a(url, tmp_path, browser_cookies=True)
            transcript = transcribe_audio(audio_path, api_key=settings.groq_api_key)
        except Exception as exc:  # noqa: BLE001
            print(f"[x_post] audio transcription failed ({exc}); using tweet text.")
            transcript = ""

    if transcript:
        body = transcript
        if tweet_text:
            body = f"{tweet_text}\n\n---\n\n{body}"
        return body, "Video Transcript"
    else:
        return (tweet_text or "No post text was returned."), "Post Content"


def _handle_images(
    *,
    image_urls: list[str],
    tweet_text: str,
    settings,
) -> tuple[str, str]:
    """Download images and caption each with Gemini Vision (D29)."""
    from .gemini import GeminiClient

    if not image_urls:
        return (tweet_text or "No post content was returned."), "Post Content"

    gemini = GeminiClient(settings.gemini_api_key)

    with tempfile.TemporaryDirectory(prefix="recall_x_img_") as tmp:
        tmp_path = Path(tmp)
        local_images = download_images(image_urls, tmp_path)

        captions: list[str] = []
        for idx, img_path in enumerate(local_images, start=1):
            try:
                img_caption = gemini.caption_image(img_path, model=settings.summary_model)
                label = f"**Image {idx}:**" if len(local_images) > 1 else ""
                captions.append(f"{label}\n{img_caption}".strip())
            except Exception as exc:  # noqa: BLE001
                print(f"[x_post] Gemini Vision failed for image {idx} ({exc}); skipping.")

    if not captions:
        return (tweet_text or "No image content could be described."), "Post Content"

    body_parts: list[str] = []
    if tweet_text:
        body_parts.append(tweet_text)
    body_parts.extend(captions)
    body = "\n\n---\n\n".join(body_parts)
    section_title = "Image Captions" if len(local_images) > 1 else "Image Caption"
    return body, section_title


# ── yt-dlp extraction ─────────────────────────────────────────────────────────


def _extract_with_cookies(url: str) -> dict | None:
    """Run yt-dlp with Firefox cookies.

    Returns None (instead of raising) when yt-dlp explicitly says there is
    no video in the tweet — image-only tweets are handled via page scraping.
    """
    from yt_dlp import YoutubeDL
    from yt_dlp.utils import DownloadError, ExtractorError

    opts: dict = {
        "quiet": True,
        "skip_download": True,
        "noplaylist": False,
        "extract_flat": False,
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
        except (DownloadError, ExtractorError) as exc:
            msg = str(exc).lower()
            if "no video could be found" in msg or "no video formats" in msg:
                # Image-only tweet — return None to trigger page-scrape fallback
                return None
            if not attempt_cookies:
                raise
        except Exception:  # noqa: BLE001
            if not attempt_cookies:
                raise

    return None


# ── Page-scrape fallback for image tweets ─────────────────────────────────────


def _scrape_tweet_page(url: str) -> tuple[str, list[str]]:
    """Scrape an X/Twitter page to extract tweet text and image URLs.

    Returns (tweet_text, list_of_image_urls). Both may be empty strings/lists
    if the page is not accessible without auth.

    X image attachments are served from pbs.twimg.com and are public.
    The tweet page itself may require auth, but we try without first.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }
    tweet_text = ""
    image_urls: list[str] = []

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        # Extract og:description (tweet text)
        og_desc = re.search(r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\'](.*?)["\']', html, re.IGNORECASE)
        if og_desc:
            tweet_text = og_desc.group(1).strip()

        # Extract pbs.twimg.com image URLs from page source
        found = _TWIMG_RE.findall(html)
        # Deduplicate while preserving order; prefer 'large' or 'orig' name
        seen: set[str] = set()
        for img_url in found:
            # Normalize to 'large' quality
            img_url = re.sub(r'name=\w+', 'name=large', img_url)
            if img_url not in seen:
                seen.add(img_url)
                image_urls.append(img_url)

    except Exception as exc:  # noqa: BLE001
        print(f"[x_post] page scrape failed for {url}: {exc}")

    return tweet_text, image_urls


# ── Helpers ───────────────────────────────────────────────────────────────────


def _best_title(info: dict) -> str:
    return (
        info.get("title")
        or info.get("description", "")[:80]
        or "Untitled X post"
    ).strip()


def _creator(info: dict) -> str:
    return (
        info.get("uploader")
        or info.get("uploader_id")
        or info.get("channel")
        or "Unknown"
    ).strip()


def _collect_image_urls(info: dict) -> list[str]:
    """Extract pbs.twimg.com image attachment URLs from yt-dlp metadata."""
    urls: list[str] = []
    formats = info.get("formats") or []
    for fmt in formats:
        furl = fmt.get("url", "")
        if "pbs.twimg.com/media" in furl and furl not in urls:
            urls.append(furl)

    direct = info.get("url", "")
    if "pbs.twimg.com/media" in direct and direct not in urls:
        urls.append(direct)

    return urls
