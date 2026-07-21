from __future__ import annotations

import hashlib
import re


def source_url_hash(url: str) -> str:
    return hashlib.sha256(url.strip().encode("utf-8")).hexdigest()[:8]


def slugify_title(title: str, *, max_length: int = 70, fallback: str = "source") -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", title.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return (slug[:max_length].strip("-") or fallback)


def source_note_filename(url: str, title: str, *, fallback_slug: str = "source") -> str:
    return f"{slugify_title(title, fallback=fallback_slug)}--{source_url_hash(url)}.md"


def youtube_note_filename(url: str, title: str) -> str:
    # D15: filename is anchored by the source URL hash, so re-adding the same URL is a no-op.
    return source_note_filename(url, title, fallback_slug="youtube")
