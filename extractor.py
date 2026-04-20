"""
extractor.py — Stateless HTML article extraction using XPath selectors.
Adapted from contify/rss_feed/articles_extractor.py (extract_html_articles).
"""

import functools
import re
import logging

import lxml.html
import lxml.etree
from lxml.etree import XPath, XPathError

logger = logging.getLogger(__name__)

_WHITESPACE_RE = re.compile(r"\s+")


class ArticleNotFound(Exception):
    pass


class MissingSelectors(Exception):
    pass


@functools.lru_cache(maxsize=256)
def _cached_compile_xpath(field_name: str, xpath: str) -> XPath:
    """Compile and LRU-cache XPath expressions — avoids re-parsing on repeated calls."""
    try:
        return lxml.etree.XPath(xpath)
    except XPathError:
        raise XPathError(f"Error in {field_name} xpath, please fix and retry")


def _ensure_relative(xpath: str) -> str:
    """Prefix with '.' if not already relative — scopes to story node."""
    xpath = xpath.strip()
    if xpath and not xpath.startswith((".", "@", "(")):
        return "." + xpath
    return xpath


def _normalize(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text).strip()


def _make_text_xp(field: str, xpath: str):
    """Wrap in string() for scalar text extraction; compile and cache."""
    if not xpath:
        return None
    wrapped = xpath if xpath.startswith("string(") else f"string({xpath})"
    return _cached_compile_xpath(field, wrapped)


def parse_html(html_text: str | bytes) -> lxml.html.HtmlElement:
    try:
        return lxml.html.fromstring(html_text)
    except lxml.etree.ParserError:
        if isinstance(html_text, bytes):
            return lxml.html.fromstring(html_text.decode(errors="ignore"))
        return lxml.html.fromstring(html_text.encode("utf-8", errors="ignore"))


def extract_articles(html_text: str | bytes, selector_map: dict) -> list[dict]:
    """
    Extract articles from static HTML using XPath selectors.

    selector_map keys:
        stories_selector  — absolute XPath to repeating story containers (required)
        url_selector      — relative XPath for article URL (required)
        title_selector    — relative XPath for title (optional)
        date_selector     — relative XPath for pub date (optional)
        summary_selector  — relative XPath for summary (optional)

    Returns list of dicts: [{url, title, date, summary}, ...]
    """
    story_xpath = (selector_map.get("stories_selector") or "").strip()
    url_xpath = (selector_map.get("url_selector") or "").strip()

    if not story_xpath:
        raise MissingSelectors("stories_selector is required.")
    if not url_xpath:
        raise MissingSelectors("url_selector is required.")

    # Scope child selectors to story node
    url_scoped     = _ensure_relative(url_xpath)
    title_scoped   = _ensure_relative(selector_map.get("title_selector") or "")
    date_scoped    = _ensure_relative(selector_map.get("date_selector") or "")
    summary_scoped = _ensure_relative(selector_map.get("summary_selector") or "")

    # Compile all XPaths once (cached)
    xp_story   = _cached_compile_xpath("stories_selector", story_xpath)
    xp_url     = _cached_compile_xpath("url", url_scoped)
    xp_title   = _make_text_xp("title", title_scoped)
    xp_date    = _make_text_xp("date", date_scoped)
    xp_summary = _make_text_xp("summary", summary_scoped)

    if not html_text:
        raise ArticleNotFound("No HTML provided.")

    root = parse_html(html_text)
    story_nodes = xp_story(root)

    if not story_nodes:
        raise ArticleNotFound("No story containers found. Check stories_selector.")

    results = []
    seen_urls: set[str] = set()

    for story in story_nodes:
        if not isinstance(story, lxml.html.HtmlElement):
            continue

        raw_urls = xp_url(story)
        if not raw_urls:
            continue

        raw_url = raw_urls[0] if not isinstance(raw_urls, str) else raw_urls
        if not isinstance(raw_url, str) or not raw_url.strip():
            continue

        url = raw_url.strip()
        if url in seen_urls:
            continue
        seen_urls.add(url)

        results.append({
            "url":     url,
            "title":   _normalize(str(xp_title(story)))   if xp_title   else "",
            "date":    _normalize(str(xp_date(story)))     if xp_date    else "",
            "summary": _normalize(str(xp_summary(story))) if xp_summary else "",
        })

    if not results:
        raise ArticleNotFound("Selectors matched containers but no URLs extracted.")

    return results


def highlight_nodes(html_text: str | bytes, selector_map: dict) -> str:
    """
    Return HTML with matched story containers highlighted via inline style.
    Used for the 'magic highlight' UX feature.
    """
    story_xpath = (selector_map.get("stories_selector") or "").strip()
    if not story_xpath:
        return html_text if isinstance(html_text, str) else html_text.decode(errors="ignore")

    root = parse_html(html_text)
    try:
        xp_story = _cached_compile_xpath("stories_selector", story_xpath)
        for node in xp_story(root):
            if isinstance(node, lxml.html.HtmlElement):
                existing = node.get("style", "")
                node.set("style", existing + "; outline: 3px solid #f59e0b; background: rgba(245,158,11,0.1);")
    except XPathError:
        pass

    return lxml.html.tostring(root, encoding="unicode", pretty_print=False)