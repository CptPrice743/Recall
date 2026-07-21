from __future__ import annotations

import re
from html import unescape
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .source_types import SourceDocument


USER_AGENT = "RecallBot/1.2 (+https://github.com/CptPrice743/Recall)"


def fetch_article_document(url: str) -> SourceDocument:
    html = _fetch_html(url)
    title = _extract_meta_content(html, "property", "og:title") or _extract_title(html) or "Untitled article"
    creator = (
        _extract_meta_content(html, "name", "author")
        or _extract_meta_content(html, "property", "article:author")
        or urlparse(url).netloc
    )
    published = (
        _extract_meta_content(html, "property", "article:published_time")
        or _extract_meta_content(html, "name", "date")
        or ""
    )
    text = _extract_article_text(html)
    if not text:
        raise RuntimeError("Could not extract readable text from article URL")

    domain = urlparse(url).netloc
    return SourceDocument(
        source="article",
        source_folder="Articles",
        source_url=url,
        title=title,
        creator=creator,
        body_text=text,
        body_section_title="Extracted Content",
        published=published,
        extra_frontmatter={"domain": domain},
    )


def _fetch_html(url: str) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=20) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        body = response.read()
    return body.decode(charset, errors="replace")


def _extract_title(html: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return _clean_text(match.group(1))


def _extract_meta_content(html: str, attr_name: str, attr_value: str) -> str:
    pattern = (
        rf"<meta[^>]*\b{attr_name}\s*=\s*['\"]{re.escape(attr_value)}['\"][^>]*\bcontent\s*=\s*['\"](.*?)['\"]"
        rf"|<meta[^>]*\bcontent\s*=\s*['\"](.*?)['\"][^>]*\b{attr_name}\s*=\s*['\"]{re.escape(attr_value)}['\"]"
    )
    match = re.search(pattern, html, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return _clean_text(next(group for group in match.groups() if group))


def _extract_article_text(html: str) -> str:
    scripts_stripped = re.sub(
        r"<(script|style)[^>]*>.*?</\1>",
        " ",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    article_match = re.search(
        r"<article[^>]*>(.*?)</article>",
        scripts_stripped,
        flags=re.IGNORECASE | re.DOTALL,
    )
    article_html = article_match.group(1) if article_match else scripts_stripped
    paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", article_html, flags=re.IGNORECASE | re.DOTALL)
    if not paragraphs:
        return _clean_text(re.sub(r"<[^>]+>", " ", article_html))

    cleaned = [_clean_text(paragraph) for paragraph in paragraphs]
    cleaned = [line for line in cleaned if line]
    return "\n\n".join(cleaned)


def _clean_text(raw: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw)
    text = unescape(text)
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text
