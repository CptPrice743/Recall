from __future__ import annotations

import unittest

from backend.recall.source_router import detect_source


class DetectSourceTests(unittest.TestCase):
    def test_detects_known_sources(self) -> None:
        self.assertEqual(detect_source("https://www.youtube.com/watch?v=abc"), "youtube")
        self.assertEqual(detect_source("https://reddit.com/r/python/comments/abc/title"), "reddit")
        self.assertEqual(detect_source("https://x.com/user/status/1"), "x")
        self.assertEqual(detect_source("https://instagram.com/p/xyz"), "instagram")

    def test_defaults_to_article_for_other_hosts(self) -> None:
        self.assertEqual(detect_source("https://example.com/blog/post"), "article")


if __name__ == "__main__":
    unittest.main()
