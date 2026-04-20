"""
fetcher.py — Stateless static HTML fetcher.
Only supports GET on static HTML pages (no JS rendering).
"""
from __future__ import annotations

import logging

import requests
from requests.exceptions import SSLError, Timeout, RequestException

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; XPathGenerator/1.0; "
        "+https://github.com/your-org/xpath-selector-generator)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# Pages that render via JS are out of scope per PRD
UNSUPPORTED_CONTENT_TYPES = {"application/json", "application/xml", "text/xml"}


def fetch_html(url: str, timeout: int = 20) -> tuple[str, str]:
    """
    Fetch static HTML from URL.

    Returns:
        (html_text, error_string) — on success error is empty string.
    """
    if not url or not url.startswith(("http://", "https://")):
        return "", "URL must start with http:// or https://"

    try:
        resp = requests.get(
            url,
            headers=DEFAULT_HEADERS,
            timeout=timeout,
            allow_redirects=True,
        )
    except SSLError:
        try:
            resp = requests.get(
                url,
                headers=DEFAULT_HEADERS,
                timeout=timeout,
                allow_redirects=True,
                verify=False,
            )
        except RequestException as e:
            return "", f"SSL error and retry failed: {e}"
    except Timeout:
        return "", f"Request timed out after {timeout}s"
    except RequestException as e:
        return "", f"Request failed: {e}"

    if resp.status_code != 200:
        return "", f"HTTP {resp.status_code}: {url}"

    ct = resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
    if ct in UNSUPPORTED_CONTENT_TYPES:
        return "", f"Unsupported content type '{ct}'. Only static HTML is supported."

    try:
        html = resp.content.decode(resp.apparent_encoding or "utf-8", errors="replace")
    except Exception:
        html = resp.text

    return html, ""