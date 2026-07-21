"""
delete_note.py — remove a note and its Qdrant vectors from the Recall index.

Usage
-----
# By file path (absolute or relative to cwd):
python -m backend.recall.delete_note /path/to/vault/Media/YouTube/some-note--abc123.md

# By source URL (finds the note via URL-hash filename lookup):
python -m backend.recall.delete_note "https://www.youtube.com/watch?v=VIDEO_ID"
python -m backend.recall.delete_note "https://www.reddit.com/r/sub/comments/abc/title/"
python -m backend.recall.delete_note "https://example.com/some/article"

Flags
-----
--dry-run     Show what would be deleted without actually deleting anything.
--vectors-only  Delete Qdrant vectors but keep the note file on disk.
--file-only     Delete the note file but skip Qdrant (use if the file is already gone).

Works for every source type (YouTube, Reddit, articles, Instagram, X).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse

from .config import load_settings, require_settings
from .indexing import delete_note_vectors
from .notes import existing_source_note_path
from .qdrant_store import QdrantStore

# Source folder map — must match source_router.SOURCE_FOLDERS
_SOURCE_FOLDERS = {
    "youtube.com": "YouTube",
    "youtu.be": "YouTube",
    "m.youtube.com": "YouTube",
    "reddit.com": "Reddit",
    "old.reddit.com": "Reddit",
    "redd.it": "Reddit",
    "instagram.com": "Instagram",
    "x.com": "Twitter",
    "twitter.com": "Twitter",
}


def _guess_source_folder(url: str) -> str | None:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    return _SOURCE_FOLDERS.get(host)


def _find_note_by_url(vault_root: Path, url: str) -> Path | None:
    """Try every known source folder until a URL-hash match is found."""
    # Try the obvious folder first
    hint = _guess_source_folder(url)
    candidates = [hint] if hint else []
    # Then fall back to all known folders
    all_folders = ["YouTube", "Reddit", "Articles", "Instagram", "Twitter", "X"]
    candidates += [f for f in all_folders if f not in candidates]

    for folder in candidates:
        match = existing_source_note_path(vault_root, folder, url)
        if match:
            return match

    # Last-ditch: scan all Media sub-folders
    media_dir = vault_root / "Media"
    if media_dir.is_dir():
        for sub in sorted(media_dir.iterdir()):
            if sub.is_dir() and sub.name != ".cache":
                match = existing_source_note_path(vault_root, sub.name, url)
                if match:
                    return match
    return None


def run(
    target: str,
    *,
    dry_run: bool = False,
    vectors_only: bool = False,
    file_only: bool = False,
) -> None:
    settings = load_settings()
    require_settings(settings)

    # ----- Resolve note path -----
    target_path = Path(target)
    if target_path.exists() and target_path.suffix == ".md":
        note_path = target_path.resolve()
    else:
        # Treat target as a URL
        note_path = _find_note_by_url(settings.vault_root, target)
        if not note_path:
            print(
                f"No note found in vault for URL: {target}\n"
                "If the file was already deleted, use --file-only to skip\n"
                "the file-deletion step and only clean Qdrant, or pass the\n"
                "exact file path directly.",
                file=sys.stderr,
            )
            sys.exit(1)

    if not note_path.is_relative_to(settings.vault_root):
        print(
            f"Note path {note_path} is outside the configured vault root "
            f"({settings.vault_root}).  Aborting for safety.",
            file=sys.stderr,
        )
        sys.exit(1)

    source_rel = note_path.relative_to(settings.vault_root).as_posix()
    print(f"Note  : {note_path}")
    print(f"Vector source_path: {source_rel}")

    if dry_run:
        print("[dry-run] Would delete the above — no changes made.")
        return

    # ----- Delete Qdrant vectors -----
    if not file_only:
        store = QdrantStore(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            collection=settings.qdrant_collection,
        )
        delete_note_vectors(
            note_path=note_path,
            vault_root=settings.vault_root,
            store=store,
        )

    # ----- Delete note file -----
    if not vectors_only:
        if note_path.exists():
            note_path.unlink()
            print(f"Deleted file: {note_path}")
        else:
            print(f"File already gone (skipping): {note_path}")

    print("Done.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Delete a Recall note and its Qdrant vectors.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "target",
        help="Absolute path to a .md note file, OR a source URL.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be deleted without making any changes.",
    )
    parser.add_argument(
        "--vectors-only",
        action="store_true",
        help="Delete Qdrant vectors but leave the note file on disk.",
    )
    parser.add_argument(
        "--file-only",
        action="store_true",
        help="Delete the note file but skip Qdrant (file already removed).",
    )
    args = parser.parse_args()

    if args.vectors_only and args.file_only:
        print("Error: --vectors-only and --file-only are mutually exclusive.", file=sys.stderr)
        sys.exit(1)

    run(
        args.target,
        dry_run=args.dry_run,
        vectors_only=args.vectors_only,
        file_only=args.file_only,
    )


if __name__ == "__main__":
    main()
