"""Media download utilities for Instagram and X ingestion.

Two responsibilities:
1. download_audio_m4a() — extracts audio from a video URL using yt-dlp and
   writes a .m4a file to a temp directory (D28).
2. download_images() — downloads image URLs to a temp directory for Gemini
   Vision captioning (D29).

All functions return paths inside a caller-managed temporary directory.
The caller is responsible for cleanup (use tempfile.TemporaryDirectory).
"""

from __future__ import annotations

import time
import urllib.request
from pathlib import Path


def download_audio_m4a(url: str, dest_dir: Path, *, browser_cookies: bool = True) -> Path:
    """Extract audio from a video URL as an .m4a file using yt-dlp.

    Args:
        url: URL of the video (Instagram Reel, X video, etc.)
        dest_dir: Directory to write the output file into.
        browser_cookies: If True, try Firefox cookies for authenticated content.

    Returns:
        Path to the downloaded .m4a file.

    Raises:
        RuntimeError: If yt-dlp fails to download or extract audio.
    """
    from yt_dlp import YoutubeDL
    from yt_dlp.utils import DownloadError

    output_template = str(dest_dir / "%(id)s.%(ext)s")
    opts: dict = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a",
            }
        ],
        "quiet": True,
        "noplaylist": True,
    }

    if browser_cookies:
        opts["cookiesfrombrowser"] = ("firefox",)

    try:
        with YoutubeDL(opts) as ydl:
            ydl.download([url])
    except DownloadError as exc:
        raise RuntimeError(f"yt-dlp audio extraction failed for {url}: {exc}") from exc

    # Find the downloaded file
    m4a_files = list(dest_dir.glob("*.m4a"))
    if not m4a_files:
        # ffmpeg may not be installed; fall back to whatever yt-dlp produced
        any_files = [p for p in dest_dir.iterdir() if p.is_file()]
        if not any_files:
            raise RuntimeError(f"yt-dlp produced no output file for {url}")
        return any_files[0]
    return m4a_files[0]


def download_images(image_urls: list[str], dest_dir: Path) -> list[Path]:
    """Download a list of image URLs to dest_dir.

    Args:
        image_urls: HTTP(S) image URLs to download.
        dest_dir: Directory to write images into.

    Returns:
        List of local Path objects for successfully downloaded images,
        in the same order as image_urls. Failures are skipped with a warning.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
    }
    paths: list[Path] = []
    for idx, img_url in enumerate(image_urls):
        # Derive a safe filename from the index
        suffix = _guess_extension(img_url)
        dest = dest_dir / f"image_{idx:03d}{suffix}"
        try:
            req = urllib.request.Request(img_url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                dest.write_bytes(resp.read())
            paths.append(dest)
        except Exception as exc:  # noqa: BLE001
            print(f"[media_download] warning: could not download image {img_url}: {exc}")
        # Small delay to avoid hammering CDNs
        time.sleep(0.2)
    return paths


def _guess_extension(url: str) -> str:
    """Guess a file extension from a URL path."""
    from urllib.parse import urlparse
    path = urlparse(url).path.lower()
    for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        if path.endswith(ext):
            return ext
    return ".jpg"
