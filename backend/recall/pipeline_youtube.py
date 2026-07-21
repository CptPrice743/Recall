from __future__ import annotations

import argparse

from .config import load_settings, require_settings
from .gemini import GeminiClient
from .indexing import embed_note_file, source_path_for_note
from .notes import existing_youtube_note_path, render_youtube_note, write_note_once, youtube_note_path
from .qdrant_store import QdrantStore
from .summaries import summarize_source_text
from .youtube import fetch_youtube_video


def run(url: str, *, force_index_existing: bool = False) -> None:
    settings = load_settings()
    require_settings(settings, for_summary=True)

    gemini = GeminiClient(settings.gemini_api_key)
    store = QdrantStore(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        collection=settings.qdrant_collection,
    )

    existing = existing_youtube_note_path(settings.vault_root, url)
    if existing and not force_index_existing:
        print(f"Duplicate URL skipped by filename check (D15): {existing}")
        return

    video = fetch_youtube_video(url)
    note_path = existing_youtube_note_path(settings.vault_root, video.url) or youtube_note_path(
        settings.vault_root, video
    )

    if note_path.exists() and not force_index_existing:
        print(f"Duplicate URL skipped by filename check (D15): {note_path}")
        return

    summary = summarize_source_text(
        gemini=gemini,
        source_label="YouTube",
        title=video.title,
        text=video.transcript,
        model=settings.summary_model,
    )
    note = render_youtube_note(video, summary)
    created = write_note_once(note_path, note)
    if not created:
        print(f"Note already exists; re-indexing existing note: {note_path}")

    chunk_count = embed_note_file(
        note_path=note_path,
        vault_root=settings.vault_root,
        source_url=video.webpage_url,
        gemini=gemini,
        store=store,
    )
    source_path = source_path_for_note(settings.vault_root, note_path)
    print(f"Wrote note: {note_path}")
    print(f"Indexed {chunk_count} chunk(s) into Qdrant source_path={source_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest one YouTube URL into Recall.")
    parser.add_argument("url", help="YouTube URL to ingest")
    parser.add_argument(
        "--force-index-existing",
        action="store_true",
        help="If the note already exists, re-index it instead of skipping.",
    )
    args = parser.parse_args()
    run(args.url, force_index_existing=args.force_index_existing)


if __name__ == "__main__":
    main()
