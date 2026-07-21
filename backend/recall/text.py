from __future__ import annotations

import re


def approximate_token_count(text: str) -> int:
    # Rough English token estimate; good enough for v1.1 thresholding without a tokenizer dependency.
    return max(1, len(re.findall(r"\S+", text)))


def compact_whitespace(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text.strip())


def chunk_text(text: str, *, chunk_tokens: int = 430, overlap_tokens: int = 50) -> list[str]:
    words = re.findall(r"\S+", text)
    if not words:
        return []
    if chunk_tokens <= overlap_tokens:
        raise ValueError("chunk_tokens must be greater than overlap_tokens")

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + chunk_tokens, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = end - overlap_tokens
    return chunks

