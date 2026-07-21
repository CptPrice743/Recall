# Recall Backend v1.2 (in progress)

v1.2 extends the v1.1 core loop with source routing and additional downloader modules. One URL is auto-detected as YouTube / Instagram / Reddit / X / article, converted into one Markdown note in `Media/<Source>/`, chunked, embedded into Qdrant, and then searchable through the CLI.

Design decisions implemented here:

- D13: Qdrant point IDs are random UUIDs; `source_path` is payload.
- D14: inserts delete existing points by `source_path` first.
- D15: source filenames use a URL-hash suffix to make duplicate re-ingest a no-op.
- D19: document embeddings use `RETRIEVAL_DOCUMENT`; query embeddings use `RETRIEVAL_QUERY`.
- D9: summary chunking threshold applies uniformly to all source modules.
- D20: retrieval chunks are about 430 words with 50-word overlap.
- D21: credentials load from `.env`, with `.env.example` containing placeholders only.

## Commands

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m backend.recall.healthcheck
python -m backend.recall.pipeline_ingest "https://www.youtube.com/watch?v=VIDEO_ID"
python -m backend.recall.pipeline_ingest "https://www.reddit.com/r/Python/comments/THREAD_ID/TITLE/"
python -m backend.recall.pipeline_ingest "https://example.com/blog-post"
python -m backend.recall.query_cli "what was this video about?"
python -m unittest discover -s backend/tests -p "test_*.py"
```
