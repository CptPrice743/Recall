from __future__ import annotations

from yt_dlp.utils import DownloadError
from yt_dlp import YoutubeDL


def fetch_metadata(url: str, *, allow_browser_cookies: bool = False) -> dict:
    opts = {
        "quiet": True,
        "skip_download": True,
        "noplaylist": True,
        "extract_flat": False,
    }
    try:
        return _extract_info(url, opts)
    except DownloadError:
        if not allow_browser_cookies:
            raise

    for browser in ("safari", "chrome", "firefox"):
        cookie_opts = dict(opts)
        cookie_opts["cookiesfrombrowser"] = (browser,)
        try:
            return _extract_info(url, cookie_opts)
        except DownloadError:
            continue
    raise RuntimeError(
        "yt-dlp could not extract metadata for this URL, including browser-cookie retries."
    )


def _extract_info(url: str, opts: dict) -> dict:
    with YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)
