from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


EMBEDDING_MODEL = "gemini-embedding-2"
EMBEDDING_DIMENSION = 768
DOCUMENT_TASK_TYPE = "RETRIEVAL_DOCUMENT"
QUERY_TASK_TYPE = "RETRIEVAL_QUERY"


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    qdrant_url: str
    qdrant_api_key: str
    qdrant_collection: str
    vault_root: Path
    summary_model: str
    reddit_user_agent: str
    groq_api_key: str


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        qdrant_url=os.getenv("QDRANT_URL", "").strip(),
        qdrant_api_key=os.getenv("QDRANT_API_KEY", "").strip(),
        qdrant_collection=os.getenv("QDRANT_COLLECTION", "recall_v1").strip(),
        vault_root=Path(os.getenv("VAULT_ROOT", "./vault")).expanduser(),
        summary_model=os.getenv("SUMMARY_MODEL", "gemini-3.1-flash-lite").strip(),
        reddit_user_agent=os.getenv("REDDIT_USER_AGENT", "RecallBot/1.2 (+https://github.com/CptPrice743/Recall)").strip(),
        groq_api_key=os.getenv("GROQ_API_KEY", "").strip(),
    )


def require_settings(settings: Settings, *, for_summary: bool = False) -> None:
    missing = []
    if not settings.gemini_api_key:
        missing.append("GEMINI_API_KEY")
    if not settings.qdrant_url:
        missing.append("QDRANT_URL")
    if not settings.qdrant_api_key:
        missing.append("QDRANT_API_KEY")
    if for_summary and not settings.summary_model:
        missing.append("SUMMARY_MODEL")
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(f"Missing required .env value(s): {joined}")

