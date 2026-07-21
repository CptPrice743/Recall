from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from backend.recall.notes import existing_source_note_path, source_note_path, write_note_once
from backend.recall.reddit import (
    TemporaryBlockedError,
    _build_source_document,
    _fmt_comment_meta,
    _parse_nodes,
    _render_comment_tree,
    extract_reddit_ids,
)


class ExtractRedditIdsTests(unittest.TestCase):
    def test_standard_www_url(self) -> None:
        sub, pid = extract_reddit_ids(
            "https://www.reddit.com/r/python/comments/abc123/some_title/"
        )
        self.assertEqual(sub, "python")
        self.assertEqual(pid, "abc123")

    def test_old_reddit_url(self) -> None:
        sub, pid = extract_reddit_ids(
            "https://old.reddit.com/r/browsers/comments/1uq11jo/mv2_status"
        )
        self.assertEqual(sub, "browsers")
        self.assertEqual(pid, "1uq11jo")

    def test_no_trailing_slug(self) -> None:
        sub, pid = extract_reddit_ids(
            "https://reddit.com/r/learnpython/comments/xyz789/"
        )
        self.assertEqual(sub, "learnpython")
        self.assertEqual(pid, "xyz789")

    def test_invalid_domain_raises(self) -> None:
        with self.assertRaises(ValueError):
            extract_reddit_ids("https://example.com/r/python/comments/abc/title")

    def test_missing_comments_segment_raises(self) -> None:
        with self.assertRaises(ValueError):
            extract_reddit_ids("https://www.reddit.com/r/python/")


class ParseNodesTests(unittest.TestCase):
    def _make_comment_node(self, cid: str, author: str, body: str, parent: str, replies=None) -> dict:
        data = {
            "id": cid,
            "name": f"t1_{cid}",
            "parent_id": parent,
            "author": author,
            "score": 10,
            "body": body,
            "distinguished": None,
            "stickied": False,
            "edited": False,
            "total_awards_received": 0,
        }
        if replies:
            data["replies"] = {"data": {"children": replies}}
        return {"kind": "t1", "data": data}

    def test_flat_comments(self) -> None:
        nodes = [
            self._make_comment_node("c1", "alice", "Hello", "t3_post1"),
            self._make_comment_node("c2", "bob", "World", "t3_post1"),
        ]
        all_comments: dict = {}
        children_order: dict = {}
        more_queue: list = []

        _parse_nodes(nodes, "t3_post1", all_comments, children_order, more_queue)

        self.assertIn("c1", all_comments)
        self.assertIn("c2", all_comments)
        self.assertEqual(children_order["t3_post1"], ["c1", "c2"])

    def test_nested_replies(self) -> None:
        child_node = self._make_comment_node("c2", "bob", "Reply", "t1_c1")
        nodes = [self._make_comment_node("c1", "alice", "Top", "t3_post1", replies=[child_node])]

        all_comments: dict = {}
        children_order: dict = {}
        more_queue: list = []

        _parse_nodes(nodes, "t3_post1", all_comments, children_order, more_queue)

        self.assertIn("c1", all_comments)
        self.assertIn("c2", all_comments)
        self.assertEqual(children_order["t3_post1"], ["c1"])
        self.assertEqual(children_order["t1_c1"], ["c2"])

    def test_more_stub_queued(self) -> None:
        nodes = [
            {
                "kind": "more",
                "data": {
                    "id": "stub1",
                    "name": "more_stub1",
                    "parent_id": "t3_post1",
                    "children": ["x1", "x2", "x3"],
                },
            }
        ]
        all_comments: dict = {}
        children_order: dict = {}
        more_queue: list = []

        _parse_nodes(nodes, "t3_post1", all_comments, children_order, more_queue)

        self.assertEqual(len(more_queue), 1)
        self.assertEqual(more_queue[0]["child_ids"], ["x1", "x2", "x3"])

    def test_continue_thread_stub_skipped(self) -> None:
        """More stub with id='_' should not be queued (it's a 'continue thread' link)."""
        nodes = [
            {
                "kind": "more",
                "data": {
                    "id": "_",
                    "name": "more__",
                    "parent_id": "t1_deep",
                    "children": ["deep1"],
                },
            }
        ]
        all_comments: dict = {}
        children_order: dict = {}
        more_queue: list = []

        _parse_nodes(nodes, "t1_deep", all_comments, children_order, more_queue)

        self.assertEqual(more_queue, [])


class FmtCommentMetaTests(unittest.TestCase):
    def test_basic_fields(self) -> None:
        c = {
            "author": "alice",
            "score": 42,
            "created_utc": 1720000000.0,
            "distinguished": None,
            "stickied": False,
            "edited": False,
            "total_awards_received": 0,
        }
        meta = _fmt_comment_meta(c)
        self.assertIn("u/alice", meta)
        self.assertIn("score: 42", meta)

    def test_distinguished_stickied_awards(self) -> None:
        c = {
            "author": "mod",
            "score": 1,
            "created_utc": None,
            "distinguished": "moderator",
            "stickied": True,
            "edited": True,
            "total_awards_received": 5,
        }
        meta = _fmt_comment_meta(c)
        self.assertIn("distinguished: moderator", meta)
        self.assertIn("stickied", meta)
        self.assertIn("edited", meta)
        self.assertIn("awards: 5", meta)


class RenderCommentTreeTests(unittest.TestCase):
    def test_renders_hierarchy(self) -> None:
        all_comments = {
            "c1": {
                "id": "c1", "name": "t1_c1", "author": "alice",
                "score": 10, "created_utc": None, "body": "Top comment",
                "distinguished": None, "stickied": False,
                "edited": False, "total_awards_received": 0,
            },
            "c2": {
                "id": "c2", "name": "t1_c2", "author": "bob",
                "score": 3, "created_utc": None, "body": "Nested reply",
                "distinguished": None, "stickied": False,
                "edited": False, "total_awards_received": 0,
            },
        }
        children_order = {
            "t3_post": ["c1"],
            "t1_c1": ["c2"],
            "t1_c2": [],
        }
        lines = _render_comment_tree(["c1"], all_comments, children_order)

        joined = "\n".join(lines)
        self.assertIn("u/alice", joined)
        self.assertIn("Top comment", joined)
        self.assertIn("u/bob", joined)
        self.assertIn("Nested reply", joined)
        # Bob's line should be indented (depth=1 → two spaces prefix)
        bob_line = next(ln for ln in lines if "u/bob" in ln)
        self.assertTrue(bob_line.startswith("  "), f"Expected indent: {bob_line!r}")


class BuildSourceDocumentTests(unittest.TestCase):
    def _make_cache(self) -> dict:
        return {
            "url": "https://www.reddit.com/r/test/comments/abc123/the_title/",
            "subreddit": "test",
            "post_id": "abc123",
            "submission": {
                "title": "Test post title",
                "author": "op_user",
                "subreddit_name_prefixed": "r/test",
                "selftext": "This is the post body.",
                "score": 150,
                "upvote_ratio": 0.95,
                "num_comments": 42,
                "created_utc": 1720000000.0,
                "edited": False,
                "stickied": False,
                "distinguished": None,
                "total_awards_received": 2,
            },
            "all_comments": {
                "c1": {
                    "id": "c1", "name": "t1_c1", "author": "commenter1",
                    "score": 99, "created_utc": 1720001000.0,
                    "body": "Great post!", "distinguished": None,
                    "stickied": False, "edited": False,
                    "total_awards_received": 0,
                }
            },
            "children_order": {
                "t3_abc123": ["c1"],
                "t1_c1": [],
            },
        }

    def test_source_document_shape(self) -> None:
        cache = self._make_cache()
        doc = _build_source_document(cache["url"], cache)

        self.assertEqual(doc.source, "reddit")
        self.assertEqual(doc.source_folder, "Reddit")
        self.assertEqual(doc.title, "Test post title")
        self.assertEqual(doc.creator, "u/op_user")
        # body_text contains only the post content — no raw comments
        self.assertIn("r/test", doc.body_text)
        self.assertIn("This is the post body.", doc.body_text)
        self.assertNotIn("Great post!", doc.body_text)
        # comments are in comment_context for the summariser only
        self.assertIsNotNone(doc.comment_context)
        assert doc.comment_context is not None
        self.assertIn("Great post!", doc.comment_context)

    def test_extra_frontmatter_populated(self) -> None:
        cache = self._make_cache()
        doc = _build_source_document(cache["url"], cache)

        self.assertIn("subreddit", doc.extra_frontmatter)
        self.assertIn("score", doc.extra_frontmatter)
        self.assertIn("num_comments", doc.extra_frontmatter)
        self.assertEqual(doc.extra_frontmatter["score"], "150")

    def test_published_from_created_utc(self) -> None:
        cache = self._make_cache()
        doc = _build_source_document(cache["url"], cache)
        # published should be a numeric timestamp string (seconds since epoch)
        self.assertEqual(doc.published, "1720000000")


class NotePathTests(unittest.TestCase):
    def test_existing_source_note_path_finds_hash_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            path = source_note_path(
                vault,
                source_folder="Articles",
                source_url="https://example.com/post",
                title="Example title",
            )
            self.assertTrue(write_note_once(path, "sample content"))
            found = existing_source_note_path(vault, "Articles", "https://example.com/post")
            self.assertEqual(found, path)


if __name__ == "__main__":
    unittest.main()
