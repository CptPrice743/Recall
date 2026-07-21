from __future__ import annotations

from .config import EMBEDDING_DIMENSION, load_settings, require_settings
from .gemini import GeminiClient
from .qdrant_store import QdrantStore


def main() -> None:
    settings = load_settings()
    require_settings(settings)

    gemini = GeminiClient(settings.gemini_api_key)
    vector = gemini.embed_document("Recall healthcheck document embedding.")
    print(f"Gemini embedding OK: {len(vector)} dimensions")
    if len(vector) != EMBEDDING_DIMENSION:
        raise RuntimeError(f"Expected {EMBEDDING_DIMENSION} dimensions, got {len(vector)}")

    store = QdrantStore(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        collection=settings.qdrant_collection,
    )
    store.ensure_collection()
    print(f"Qdrant collection OK: {settings.qdrant_collection}")


if __name__ == "__main__":
    main()

