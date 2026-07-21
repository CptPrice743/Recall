from __future__ import annotations

from urllib.parse import urlparse

from .article import fetch_article_document
from .instagram import fetch_instagram_document
from .reddit import fetch_reddit_document
from .source_types import SourceDocument
from .x_post import fetch_x_document
from .youtube import fetch_youtube_document


SUPPORTED_SOURCES = ("youtube", "instagram", "reddit", "x", "article")
SOURCE_FOLDERS = {
    "youtube": "YouTube",
    "instagram": "Instagram",
    "reddit": "Reddit",
    "x": "X",
    "article": "Articles",
}


def detect_source(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]

    if host in {"youtube.com", "m.youtube.com", "youtu.be"}:
        return "youtube"
    if host in {"instagram.com"}:
        return "instagram"
    if host in {"reddit.com", "old.reddit.com", "redd.it"}:
        return "reddit"
    if host in {"x.com", "twitter.com"}:
        return "x"
    if host:
        return "article"
    raise RuntimeError(f"Could not detect source from URL: {url}")


def fetch_source_document(url: str, *, source_override: str | None = None) -> SourceDocument:
    source = source_override or detect_source(url)
    if source == "youtube":
        return fetch_youtube_document(url)
    if source == "instagram":
        return fetch_instagram_document(url)
    if source == "reddit":
        return fetch_reddit_document(url)
    if source == "x":
        return fetch_x_document(url)
    if source == "article":
        return fetch_article_document(url)
    raise RuntimeError(f"Unsupported source '{source}'. Supported values: {', '.join(SUPPORTED_SOURCES)}")


def source_folder_for(source: str) -> str:
    folder = SOURCE_FOLDERS.get(source)
    if not folder:
        raise RuntimeError(f"Unsupported source '{source}'. Supported values: {', '.join(SUPPORTED_SOURCES)}")
    return folder
