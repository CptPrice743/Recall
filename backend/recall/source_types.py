from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SourceDocument:
    source: str
    source_folder: str
    source_url: str
    title: str
    creator: str
    body_text: str
    body_section_title: str = "Content"
    published: str | None = None
    duration_seconds: int | None = None
    extra_frontmatter: dict[str, str] = field(default_factory=dict)
    # Optional raw comment text passed to the summariser for context.
    # It is NOT written into the note body and NOT embedded into Qdrant.
    comment_context: str | None = None
