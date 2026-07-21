from __future__ import annotations

from pathlib import Path

from .gemini import GeminiClient
from .qdrant_store import QdrantStore
from .text import chunk_text


def source_path_for_note(vault_root: Path, note_path: Path) -> str:
    return note_path.relative_to(vault_root).as_posix()


def embed_note_file(
    *,
    note_path: Path,
    vault_root: Path,
    source_url: str,
    gemini: GeminiClient,
    store: QdrantStore,
) -> int:
    text = note_path.read_text(encoding="utf-8")
    chunks = chunk_text(text, chunk_tokens=430, overlap_tokens=50)
    vectors = [gemini.embed_document(chunk) for chunk in chunks]
    source_path = source_path_for_note(vault_root, note_path)
    store.ensure_collection()
    store.delete_source(source_path)
    store.upsert_chunks(
        source_path=source_path,
        source_url=source_url,
        chunks=chunks,
        vectors=vectors,
    )
    return len(chunks)


def delete_note_vectors(
    *,
    note_path: Path,
    vault_root: Path,
    store: QdrantStore,
) -> None:
    """Delete all Qdrant vectors belonging to a note file.

    Uses the same source_path filter as D14 (delete-before-insert), so it is
    guaranteed to remove every chunk regardless of how many were originally
    indexed.  Source-agnostic — works for any note type.
    """
    source_path = source_path_for_note(vault_root, note_path)
    store.ensure_collection()
    store.delete_source(source_path)
    print(f"Deleted vectors for source_path={source_path}")
