from __future__ import annotations

import json
import time
import urllib.parse
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener

from .config import load_settings
from .source_types import SourceDocument


# ---------------------------------------------------------------------------
# Exception type for retryable / temporary failures
# ---------------------------------------------------------------------------

class TemporaryBlockedError(RuntimeError):
    """
    Raised when Reddit ingestion cannot proceed right now but *might* succeed
    later: expired session, rate limit, transient server error.  The pipeline
    should treat this as a retryable failure, not a permanent one.
    """


# ---------------------------------------------------------------------------
# Cookie extraction — reads Firefox's SQLite cookie store (no Keychain access)
# ---------------------------------------------------------------------------

def _get_firefox_cookiejar():
    """Return an http.cookiejar.CookieJar loaded with reddit.com cookies
    from the user's Firefox profile.  Raises ImportError if browser-cookie3
    is not installed, TemporaryBlockedError if Firefox has no Reddit session."""
    try:
        import browser_cookie3  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "browser-cookie3 is required for Reddit ingestion but is not installed.\n"
            "Run:  pip install browser-cookie3"
        ) from exc

    try:
        cookiejar = browser_cookie3.firefox(domain_name=".reddit.com")
    except Exception as exc:
        raise TemporaryBlockedError(
            f"Could not read Firefox cookies for reddit.com: {exc}\n"
            "Make sure Firefox is installed on this Mac."
        ) from exc

    # Confirm we actually have a live session cookie
    session_cookie_names = {"token_v2", "reddit_session", "session"}
    found = any(
        c.name in session_cookie_names
        for c in cookiejar
        if ".reddit.com" in c.domain or "reddit.com" in c.domain
    )
    if not found:
        raise TemporaryBlockedError(
            "No active Reddit session found in Firefox.\n"
            "Open Firefox, go to reddit.com, log in, then retry."
        )

    return cookiejar


# ---------------------------------------------------------------------------
# Low-level HTTP helper (cookie-authenticated, no bearer token)
# ---------------------------------------------------------------------------

def _make_request(url: str, cookiejar, user_agent: str, *, retries: int = 3) -> object:
    """Make a GET request with Firefox session cookies injected.
    Returns the parsed JSON payload (list or dict).
    Maps HTTP errors to TemporaryBlockedError where appropriate."""
    opener = build_opener(HTTPCookieProcessor(cookiejar))
    req = Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )

    attempt = 0
    while True:
        attempt += 1
        try:
            with opener.open(req, timeout=25) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            try:
                return json.loads(raw)
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    f"Reddit returned non-JSON response from {url!r}.\n"
                    "The session may have been redirected to a login page."
                ) from exc

        except HTTPError as exc:
            code = exc.code
            if code in {401, 403}:
                raise TemporaryBlockedError(
                    f"Reddit rejected the request (HTTP {code}). "
                    "Your Firefox Reddit session may have expired — log back in at reddit.com in Firefox."
                ) from exc
            if code == 429:
                # Respect rate-limit: back off and retry
                if attempt <= retries:
                    wait = 2 ** attempt  # 2, 4, 8 seconds
                    print(f"  Reddit rate-limited (HTTP 429). Waiting {wait}s before retry {attempt}/{retries}...")
                    time.sleep(wait)
                    continue
                raise TemporaryBlockedError(
                    "Reddit API rate limit repeatedly hit (HTTP 429). Wait a few minutes and retry."
                ) from exc
            if code >= 500:
                if attempt <= retries:
                    wait = 2 ** attempt
                    print(f"  Reddit server error (HTTP {code}). Waiting {wait}s before retry {attempt}/{retries}...")
                    time.sleep(wait)
                    continue
                raise TemporaryBlockedError(
                    f"Reddit server error (HTTP {code}) persisted after {retries} retries. Retry later."
                ) from exc
            raise  # any other HTTP error is unexpected — re-raise as-is

        except TemporaryBlockedError:
            raise
        except RuntimeError:
            raise
        except Exception as exc:
            if attempt <= retries:
                wait = 2 ** attempt
                print(f"  Reddit request error ({exc}). Waiting {wait}s before retry {attempt}/{retries}...")
                time.sleep(wait)
                continue
            raise TemporaryBlockedError(
                f"Reddit request to {url!r} failed after {retries} retries: {exc}"
            ) from exc


# ---------------------------------------------------------------------------
# URL parsing
# ---------------------------------------------------------------------------

def extract_reddit_ids(url: str, *, user_agent: str | None = None) -> tuple[str, str]:
    """Parse a reddit.com post URL and return (subreddit, post_id).

    Handles:
    - https://www.reddit.com/r/{sub}/comments/{id}/...
    - https://old.reddit.com/r/{sub}/comments/{id}/...
    - https://redd.it/{id}   (follows redirect via unauthenticated HEAD)
    """
    from urllib.parse import urlparse

    parsed = urlparse(url)
    netloc = parsed.netloc.lower().removeprefix("www.")
    path_parts = [p for p in parsed.path.split("/") if p]

    # Short URL: redd.it/POST_ID — follow the redirect without cookies
    if netloc == "redd.it":
        ua = user_agent or "Mozilla/5.0 (compatible; RecallBot/1.2)"
        req = Request(url, headers={"User-Agent": ua})
        try:
            from urllib.request import urlopen
            with urlopen(req, timeout=15) as resp:
                resolved = resp.geturl()
        except Exception as exc:
            raise TemporaryBlockedError(
                f"Could not resolve redd.it short URL {url!r}: {exc}"
            ) from exc
        return extract_reddit_ids(resolved, user_agent=user_agent)

    if netloc not in {"reddit.com", "old.reddit.com"}:
        raise ValueError(f"Not a recognised Reddit domain: {netloc!r}")

    # /r/{sub}/comments/{post_id}[/{slug}]
    if len(path_parts) >= 4 and path_parts[0] == "r" and path_parts[2] == "comments":
        return path_parts[1], path_parts[3]

    raise ValueError(
        f"Cannot extract subreddit/post-ID from Reddit URL: {url!r}\n"
        "Expected format: https://www.reddit.com/r/<sub>/comments/<id>/..."
    )


# ---------------------------------------------------------------------------
# Local cache (avoids re-fetching the same thread)
# ---------------------------------------------------------------------------

def _cache_path(vault_root: Path, post_id: str) -> Path:
    cache_dir = vault_root / "Media" / "Reddit" / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{post_id}.json"


def _save_cache(vault_root: Path, post_id: str, data: dict) -> None:
    path = _cache_path(vault_root, post_id)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_cache(vault_root: Path, post_id: str) -> dict | None:
    path = _cache_path(vault_root, post_id)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


# ---------------------------------------------------------------------------
# Comment-tree parsing
# ---------------------------------------------------------------------------

def _parse_nodes(
    nodes: list[dict],
    parent_fullname: str,
    all_comments: dict,
    children_order: dict,
    more_queue: list,
) -> None:
    """Recursively walk a listing of Reddit comment nodes.

    Populates:
      all_comments    — {comment_id: comment_dict}
      children_order  — {parent_fullname: [child_id, ...]}  (preserves order)
      more_queue      — list of "more" stubs to expand later
    """
    if parent_fullname not in children_order:
        children_order[parent_fullname] = []

    for node in nodes:
        kind = node.get("kind")
        data = node.get("data", {})

        if kind == "t1":                        # regular comment
            cid = data.get("id")
            if not cid:
                continue
            comment_fullname = data.get("name") or f"t1_{cid}"

            # Preserve position in parent's child list
            if cid not in children_order[parent_fullname]:
                children_order[parent_fullname].append(cid)

            all_comments[cid] = {
                "id": cid,
                "name": comment_fullname,
                "parent_id": data.get("parent_id") or parent_fullname,
                "author": data.get("author") or "[deleted]",
                "score": data.get("score", 0),
                "created_utc": data.get("created_utc"),
                "body": (data.get("body") or "").strip(),
                "distinguished": data.get("distinguished"),
                "stickied": data.get("stickied", False),
                "edited": data.get("edited", False),
                "total_awards_received": data.get("total_awards_received", 0),
            }

            # Recurse into inline replies
            replies = data.get("replies")
            if isinstance(replies, dict):
                reply_nodes = replies.get("data", {}).get("children", [])
                _parse_nodes(reply_nodes, comment_fullname, all_comments, children_order, more_queue)

        elif kind == "more":                    # collapsed branch stub
            stub_id = data.get("id", "")
            child_ids = data.get("children", [])
            # id == "_" means "continue this thread" deep link — skip
            if stub_id and stub_id != "_" and child_ids:
                # Register placeholder positions under the parent
                for cid in child_ids:
                    if cid not in children_order[parent_fullname]:
                        children_order[parent_fullname].append(cid)
                more_queue.append({
                    "parent_fullname": parent_fullname,
                    "child_ids": child_ids,
                    "post_fullname": None,  # filled in by caller
                })


def _expand_more_comments(
    more_queue: list,
    post_fullname: str,
    all_comments: dict,
    children_order: dict,
    cookiejar,
    user_agent: str,
) -> None:
    """Drain the more_queue by calling /api/morechildren until all accessible
    comments have been fetched.  Batches are capped at 100 IDs per request
    (Reddit's documented limit)."""
    base_url = (
        "https://www.reddit.com/api/morechildren"
        "?raw_json=1&api_type=json"
        f"&link_id={urllib.parse.quote(post_fullname)}"
    )

    while more_queue:
        stub = more_queue.pop(0)
        parent_fn = stub["parent_fullname"]
        child_ids = stub["child_ids"]

        for i in range(0, len(child_ids), 100):
            batch = child_ids[i : i + 100]
            children_param = urllib.parse.quote(",".join(batch))
            url = f"{base_url}&children={children_param}"

            print(f"  Expanding {len(batch)} collapsed comment(s)...")
            time.sleep(0.6)  # polite pacing — Reddit asks for ≤1 req/sec

            resp = _make_request(url, cookiejar, user_agent)

            # morechildren wraps its payload: {"json": {"data": {"things": [...]}}}
            things = []
            if isinstance(resp, dict):
                things = resp.get("json", {}).get("data", {}).get("things", [])

            sub_queue: list = []
            _parse_nodes(things, parent_fn, all_comments, children_order, sub_queue)

            # Patch post_fullname into newly queued stubs and re-enqueue
            for s in sub_queue:
                s["post_fullname"] = post_fullname
            more_queue.extend(sub_queue)


# ---------------------------------------------------------------------------
# Markdown rendering helpers
# ---------------------------------------------------------------------------

def _fmt_comment_meta(c: dict) -> str:
    parts = [f"u/{c['author']}", f"score: {c['score']}"]

    ts = c.get("created_utc")
    if ts:
        parts.append(datetime.fromtimestamp(ts, UTC).strftime("%Y-%m-%d %H:%M UTC"))

    if c.get("distinguished"):
        parts.append(f"distinguished: {c['distinguished']}")
    if c.get("stickied"):
        parts.append("stickied")

    edited = c.get("edited")
    if edited:
        if isinstance(edited, bool):
            parts.append("edited")
        elif isinstance(edited, (int, float)):
            parts.append(f"edited: {datetime.fromtimestamp(edited, UTC).strftime('%Y-%m-%d')}")

    awards = c.get("total_awards_received", 0)
    if awards:
        parts.append(f"awards: {awards}")

    return f"({', '.join(parts)})"


def _render_comment_tree(
    comment_ids: list[str],
    all_comments: dict,
    children_order: dict,
    depth: int = 0,
) -> list[str]:
    lines: list[str] = []
    indent = "  " * depth

    for cid in comment_ids:
        comment = all_comments.get(cid)
        if not comment:
            continue

        meta = _fmt_comment_meta(comment)
        body_lines = comment["body"].splitlines()
        body_indented = "\n".join(f"{indent}  {ln}" for ln in body_lines)

        lines.append(f"{indent}- {meta}")
        if body_indented.strip():
            lines.append(body_indented)

        child_ids = children_order.get(comment["name"], [])
        if child_ids:
            lines.extend(
                _render_comment_tree(child_ids, all_comments, children_order, depth + 1)
            )

    return lines


# ---------------------------------------------------------------------------
# SourceDocument construction from cached data
# ---------------------------------------------------------------------------

def _build_source_document(url: str, cache: dict) -> SourceDocument:
    submission = cache["submission"]
    all_comments: dict = cache["all_comments"]
    children_order: dict = cache["children_order"]
    post_id: str = cache["post_id"]
    subreddit: str = cache["subreddit"]

    title = (submission.get("title") or "Untitled Reddit thread").strip()
    author = submission.get("author") or "unknown"
    subreddit_display = submission.get("subreddit_name_prefixed") or f"r/{subreddit}"
    selftext = (submission.get("selftext") or "").strip()

    # -----------------------------------------------------------------------
    # Post metadata line
    # -----------------------------------------------------------------------
    score = submission.get("score", 0)
    upvote_ratio = submission.get("upvote_ratio")
    num_comments = submission.get("num_comments", 0)

    meta_parts = [f"Score: {score}"]
    if upvote_ratio is not None:
        meta_parts.append(f"Upvote ratio: {upvote_ratio:.0%}")
    meta_parts.append(f"Comments: {num_comments}")

    created_utc = submission.get("created_utc")
    if created_utc:
        dt = datetime.fromtimestamp(created_utc, UTC)
        meta_parts.append(f"Posted: {dt.strftime('%Y-%m-%d %H:%M UTC')}")

    post_edited = submission.get("edited")
    if post_edited:
        if isinstance(post_edited, bool):
            meta_parts.append("(edited)")
        elif isinstance(post_edited, (int, float)):
            meta_parts.append(f"(edited {datetime.fromtimestamp(post_edited, UTC).strftime('%Y-%m-%d')})")

    if submission.get("stickied"):
        meta_parts.append("[stickied]")
    if submission.get("distinguished"):
        meta_parts.append(f"[{submission['distinguished']}]")

    awards = submission.get("total_awards_received", 0)
    if awards:
        meta_parts.append(f"Awards: {awards}")

    post_meta_line = " | ".join(meta_parts)

    # -----------------------------------------------------------------------
    # body_text — goes into the note AND gets chunked + embedded into Qdrant.
    # Contains ONLY the post content; no raw comments here.
    # -----------------------------------------------------------------------
    body_parts: list[str] = [
        f"Subreddit: {subreddit_display}",
        f"Title: {title}",
        post_meta_line,
    ]
    if selftext:
        body_parts.append(f"\nPost text:\n{selftext}")

    body_text = "\n".join(body_parts).strip()
    if not body_text:
        raise RuntimeError("Reddit thread contained no extractable text.")

    # -----------------------------------------------------------------------
    # comment_context — passed to Gemini for summarisation only.
    # NOT written into the note body, NOT embedded into Qdrant.
    # Capped at ~32 000 chars (~8 000 tokens) so we don't blow the context.
    # Only top-level comments (depth 0) are included; replies are omitted to
    # keep signal density high.
    # -----------------------------------------------------------------------
    comment_context: str | None = None
    top_level_ids = children_order.get(f"t3_{post_id}", [])
    if top_level_ids and all_comments:
        # Sort top-level comments by score descending so Gemini sees the
        # highest-quality signal first.
        top_ids_sorted = sorted(
            top_level_ids,
            key=lambda cid: all_comments.get(cid, {}).get("score", 0),
            reverse=True,
        )
        CHAR_BUDGET = 32_000
        lines: list[str] = []
        used = 0
        for cid in top_ids_sorted:
            c = all_comments.get(cid)
            if not c or not c.get("body"):
                continue
            line = f"- u/{c['author']} (score {c['score']}): {c['body']}"
            if used + len(line) > CHAR_BUDGET:
                break
            lines.append(line)
            used += len(line) + 1
        if lines:
            comment_context = "\n".join(lines)

    # -----------------------------------------------------------------------
    # Frontmatter extras
    # -----------------------------------------------------------------------
    extra_frontmatter: dict[str, str] = {
        "subreddit": subreddit_display,
        "score": str(score),
        "num_comments": str(num_comments),
    }
    if created_utc:
        extra_frontmatter["created_utc"] = str(int(created_utc))
    if upvote_ratio is not None:
        extra_frontmatter["upvote_ratio"] = f"{upvote_ratio:.2f}"
    if awards:
        extra_frontmatter["total_awards_received"] = str(awards)
    if submission.get("distinguished"):
        extra_frontmatter["distinguished"] = str(submission["distinguished"])
    if submission.get("stickied"):
        extra_frontmatter["stickied"] = "true"
    if post_edited:
        extra_frontmatter["edited"] = str(post_edited)

    return SourceDocument(
        source="reddit",
        source_folder="Reddit",
        source_url=url,
        title=title,
        creator=f"u/{author}",
        body_text=body_text,
        body_section_title="Post",
        published=str(int(created_utc)) if created_utc else None,
        extra_frontmatter=extra_frontmatter,
        comment_context=comment_context,
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def fetch_reddit_document(url: str) -> SourceDocument:
    """Fetch a Reddit thread (post + full comment tree) using the authenticated
    session stored in the user's Firefox profile.

    Strategy
    --------
    1. Check the local JSON cache — return immediately if a fresh copy exists.
    2. Extract the reddit.com cookies from Firefox (no Keychain access needed).
    3. Fetch  GET /r/{sub}/comments/{id}.json?raw_json=1&limit=500
       with the session cookies injected as regular HTTP headers.
    4. Recursively expand any "more" stubs via /api/morechildren.
    5. Cache the result to avoid re-hitting the API on duplicate ingestion.
    6. Build and return a SourceDocument matching the shared pipeline shape.

    Errors
    ------
    - TemporaryBlockedError  — session expired / rate-limited / server down
    - ValueError             — URL is not a valid Reddit post URL
    - RuntimeError           — unexpected API shape or empty content
    """
    settings = load_settings()

    try:
        subreddit, post_id = extract_reddit_ids(url, user_agent=settings.reddit_user_agent)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc

    # --- Cache hit ---
    cached = _load_cache(settings.vault_root, post_id)
    if cached is not None:
        print(f"Reddit: loaded thread {post_id!r} from local cache (skipping API call).")
        return _build_source_document(url, cached)

    # --- Live fetch ---
    cookiejar = _get_firefox_cookiejar()

    thread_url = (
        f"https://www.reddit.com/r/{subreddit}/comments/{post_id}.json"
        "?raw_json=1&limit=500&sort=top"
    )
    print(f"Reddit: fetching thread {post_id!r} (r/{subreddit}) ...")

    payload = _make_request(thread_url, cookiejar, settings.reddit_user_agent)

    if not isinstance(payload, list) or len(payload) < 2:
        raise RuntimeError(
            f"Reddit JSON for {url!r} had unexpected shape (expected a 2-element list)."
        )

    # Submission metadata
    sub_listing = payload[0].get("data", {}).get("children", [])
    if not sub_listing:
        raise RuntimeError("Could not read submission data from Reddit response.")
    submission_data: dict = sub_listing[0].get("data", {})

    # First pass — parse the inline comment tree
    initial_nodes = payload[1].get("data", {}).get("children", [])
    all_comments: dict = {}
    children_order: dict = {}
    more_queue: list = []
    post_fullname = f"t3_{post_id}"

    _parse_nodes(initial_nodes, post_fullname, all_comments, children_order, more_queue)

    # Second pass — expand "more" stubs
    if more_queue:
        print(f"Reddit: expanding {len(more_queue)} collapsed comment branch(es)...")
        _expand_more_comments(
            more_queue, post_fullname, all_comments, children_order,
            cookiejar, settings.reddit_user_agent,
        )

    print(f"Reddit: fetched {len(all_comments)} comment(s) total.")

    # Cache raw data so subsequent ingestion runs don't hit the API again
    cache_data = {
        "url": url,
        "subreddit": subreddit,
        "post_id": post_id,
        "submission": submission_data,
        "all_comments": all_comments,
        "children_order": children_order,
    }
    _save_cache(settings.vault_root, post_id, cache_data)

    return _build_source_document(url, cache_data)
