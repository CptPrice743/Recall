from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from .filenames import source_note_filename, source_url_hash, youtube_note_filename
from .source_types import SourceDocument
from .text import compact_whitespace
from .youtube import YouTubeVideo


def youtube_note_path(vault_root: Path, video: YouTubeVideo) -> Path:
    return vault_root / "Media" / "YouTube" / youtube_note_filename(video.url, video.title)


def existing_youtube_note_path(vault_root: Path, source_url: str) -> Path | None:
    return existing_source_note_path(vault_root, "YouTube", source_url)


def source_note_path(vault_root: Path, *, source_folder: str, source_url: str, title: str) -> Path:
    return vault_root / "Media" / source_folder / source_note_filename(source_url, title)


def existing_source_note_path(vault_root: Path, source_folder: str, source_url: str) -> Path | None:
    source_dir = vault_root / "Media" / source_folder
    if not source_dir.exists():
        return None
    matches = sorted(source_dir.glob(f"*--{source_url_hash(source_url)}.md"))
    return matches[0] if matches else None


def render_youtube_note(video: YouTubeVideo, summary: str) -> str:
    document = SourceDocument(
        source="youtube",
        source_folder="YouTube",
        source_url=video.webpage_url,
        title=video.title,
        creator=video.uploader,
        body_text=video.transcript,
        body_section_title="Transcript",
        published=video.upload_date,
        duration_seconds=video.duration,
        extra_frontmatter={"video_id": video.video_id},
    )
    return render_source_note(document, summary)


def render_source_note(document: SourceDocument, summary: str) -> str:
    duration = _format_duration(document.duration_seconds)
    created_at = datetime.now(UTC).isoformat(timespec="seconds")
    frontmatter_extra = "\n".join(
        f'{key}: "{_escape_yaml(str(value))}"'
        for key, value in sorted(document.extra_frontmatter.items())
        if str(value).strip()
    )
    if frontmatter_extra:
        frontmatter_extra = "\n" + frontmatter_extra

    published = document.published or ""
    return compact_whitespace(
        f"""---
source: {document.source}
source_url: {document.source_url}
title: "{_escape_yaml(document.title)}"
creator: "{_escape_yaml(document.creator)}"
duration: {duration}
published: {published}{frontmatter_extra}
created_at: {created_at}
---

# {document.title}

Source: {document.source_url}

Creator: {document.creator}

## Summary

{summary.strip()}

## {document.body_section_title}

{document.body_text.strip()}
"""
    ) + "\n"


def write_note_once(path: Path, content: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return False
    path.write_text(content, encoding="utf-8")
    return True


def _format_duration(seconds: int | None) -> str:
    if seconds is None:
        return ""
    return str(seconds)


def _escape_yaml(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
