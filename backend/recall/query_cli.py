from __future__ import annotations

import argparse
import textwrap

from .config import load_settings, require_settings
from .gemini import GeminiClient
from .qdrant_store import QdrantStore


def run(question: str, *, limit: int = 5) -> None:
    settings = load_settings()
    require_settings(settings)
    gemini = GeminiClient(settings.gemini_api_key)
    store = QdrantStore(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        collection=settings.qdrant_collection,
    )
    query_vector = gemini.embed_query(question)
    results = store.search(query_vector=query_vector, limit=limit)
    if not results:
        print("No Qdrant results returned.")
        return

    for index, result in enumerate(results, start=1):
        payload = getattr(result, "payload", {}) or {}
        score = getattr(result, "score", None)
        text = payload.get("text", "")
        print(f"\n[{index}] score={score}")
        print(f"source_path={payload.get('source_path')}")
        print(f"source_url={payload.get('source_url')}")
        print(f"chunk_index={payload.get('chunk_index')}")
        print(textwrap.shorten(text.replace("\n", " "), width=900, placeholder=" ..."))


def main() -> None:
    parser = argparse.ArgumentParser(description="Query Recall's Qdrant index from the CLI.")
    parser.add_argument("question", help="Plain-language question to search for")
    parser.add_argument("--limit", type=int, default=5, help="Number of chunks to return")
    args = parser.parse_args()
    run(args.question, limit=args.limit)


if __name__ == "__main__":
    main()

