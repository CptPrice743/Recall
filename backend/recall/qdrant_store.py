from __future__ import annotations

from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.http import models

from .config import EMBEDDING_DIMENSION


class QdrantStore:
    def __init__(self, *, url: str, api_key: str, collection: str):
        self.client = QdrantClient(url=url, api_key=api_key)
        self.collection = collection

    def ensure_collection(self) -> None:
        exists = self.client.collection_exists(self.collection)
        if not exists:
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=models.VectorParams(
                    size=EMBEDDING_DIMENSION,
                    distance=models.Distance.COSINE,
                ),
            )
        self._ensure_payload_index("source_path")

    def delete_source(self, source_path: str) -> None:
        # D14: every insert path clears existing vectors for the same source_path first.
        self.client.delete(
            collection_name=self.collection,
            points_selector=models.FilterSelector(filter=_source_filter(source_path)),
            wait=True,
        )

    def upsert_chunks(
        self,
        *,
        source_path: str,
        source_url: str,
        chunks: list[str],
        vectors: list[list[float]],
    ) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have the same length")
        points = [
            models.PointStruct(
                # D13: Qdrant point IDs are UUIDs; source_path is payload, not the ID.
                id=str(uuid4()),
                vector=vector,
                payload={
                    "source_path": source_path,
                    "source_url": source_url,
                    "chunk_index": index,
                    "text": chunk,
                },
            )
            for index, (chunk, vector) in enumerate(zip(chunks, vectors))
        ]
        if points:
            self.client.upsert(collection_name=self.collection, points=points, wait=True)

    def search(self, *, query_vector: list[float], limit: int = 5) -> list[object]:
        try:
            response = self.client.query_points(
                collection_name=self.collection,
                query=query_vector,
                limit=limit,
                with_payload=True,
            )
            return list(response.points)
        except AttributeError:
            return list(
                self.client.search(
                    collection_name=self.collection,
                    query_vector=query_vector,
                    limit=limit,
                    with_payload=True,
                )
            )

    def _ensure_payload_index(self, field_name: str) -> None:
        try:
            self.client.create_payload_index(
                collection_name=self.collection,
                field_name=field_name,
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
        except Exception:
            pass


def _source_filter(source_path: str) -> models.Filter:
    return models.Filter(
        must=[
            models.FieldCondition(
                key="source_path",
                match=models.MatchValue(value=source_path),
            )
        ]
    )
