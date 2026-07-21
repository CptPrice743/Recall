from __future__ import annotations

import argparse

from .config import load_settings, require_settings
from .gemini import GeminiClient
from .indexing import embed_note_file, source_path_for_note
from .notes import existing_source_note_path, render_source_note, source_note_path, write_note_once
from .qdrant_store import QdrantStore
from .source_router import SUPPORTED_SOURCES, detect_source, fetch_source_document, source_folder_for
from .summaries import summarize_source_text


def run(url: str, *, source: str | None = None, force_index_existing: bool = False) -> None:
    settings = load_settings()
    require_settings(settings, for_summary=True)

    detected_source = source or detect_source(url)
    source_folder = source_folder_for(detected_source)
    # D15: check URL-hash duplicate before source download/parse work.
    existing = existing_source_note_path(settings.vault_root, source_folder, url)
    if existing and not force_index_existing:
        print(f"Duplicate URL skipped by filename check (D15): {existing}")
        return

    source_document = fetch_source_document(url, source_override=detected_source)

    gemini = GeminiClient(settings.gemini_api_key)

    # Generate an AI-derived note title from the content body so the filename
    # is descriptive and navigable in Obsidian — not a raw platform title like
    # "Video by theformaledit". Falls back to the platform title if generation fails.
    ai_title = gemini.generate_note_title(
        body_text=source_document.body_text,
        model=settings.summary_model,
    )
    note_title = ai_title or source_document.title
    print(f"Note title: {note_title!r}")

    note_path = existing_source_note_path(
        settings.vault_root,
        source_document.source_folder,
        source_document.source_url,
    ) or source_note_path(
        settings.vault_root,
        source_folder=source_document.source_folder,
        source_url=source_document.source_url,
        title=note_title,
    )

    store = QdrantStore(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        collection=settings.qdrant_collection,
    )
    summary = summarize_source_text(
        gemini=gemini,
        source_label=source_document.source_folder,
        title=note_title,
        text=source_document.body_text,
        model=settings.summary_model,
        comment_context=source_document.comment_context,
    )
    note = render_source_note(source_document, summary)
    created = write_note_once(note_path, note)
    if not created:
        print(f"Note already exists; re-indexing existing note: {note_path}")

    chunk_count = embed_note_file(
        note_path=note_path,
        vault_root=settings.vault_root,
        source_url=source_document.source_url,
        gemini=gemini,
        store=store,
    )
    source_path = source_path_for_note(settings.vault_root, note_path)
    print(f"Wrote note: {note_path}")
    print(f"Indexed {chunk_count} chunk(s) into Qdrant source_path={source_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest one supported URL into Recall v1.2.")
    parser.add_argument("url", help="Source URL to ingest")
    parser.add_argument(
        "--source",
        choices=SUPPORTED_SOURCES,
        help="Optional source override. By default, source is auto-detected from URL.",
    )
    parser.add_argument(
        "--force-index-existing",
        action="store_true",
        help="If the note already exists, re-index it instead of skipping.",
    )
    args = parser.parse_args()
    run(args.url, source=args.source, force_index_existing=args.force_index_existing)


if __name__ == "__main__":
    main()
