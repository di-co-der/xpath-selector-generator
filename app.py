"""
app.py — XPath Selector Generator: Flask entry point.

Routes:
    GET  /                   → UI
    POST /api/fetch-html     → fetch + clean page HTML
    POST /api/generate       → LLM XPath generation
    POST /api/preview        → run selectors against fetched HTML
    POST /api/highlight      → return HTML with matched nodes highlighted
"""

import logging
import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from extractor import ArticleNotFound, MissingSelectors, extract_articles, highlight_nodes
from fetcher import fetch_html
from llm_service import clean_html_for_llm, generate_selectors

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")


# ── UI ────────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ── API ───────────────────────────────────────────────────────────────────────

@app.route("/api/fetch-html", methods=["POST"])
def api_fetch_html():
    """
    Fetch and clean HTML from a URL.
    Body: { url: str }
    Returns: { raw_html: str, cleaned_html: str, char_count: int, error: str }
    """
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()

    if not url:
        return jsonify(error="url is required"), 400

    raw_html, err = fetch_html(url)
    if err:
        return jsonify(error=err), 422

    cleaned = clean_html_for_llm(raw_html)
    return jsonify(
        raw_html=raw_html,
        cleaned_html=cleaned,
        char_count=len(raw_html),
        cleaned_char_count=len(cleaned),
    )


@app.route("/api/generate", methods=["POST"])
def api_generate():
    """
    Generate XPath selectors via LLM from cleaned HTML.
    Body: { cleaned_html: str, hint?: str }
    Returns: { selectors: {...}, reasoning: str, error: str }
    """
    data = request.get_json(silent=True) or {}
    cleaned_html = (data.get("cleaned_html") or "").strip()
    hint = (data.get("hint") or "").strip()

    if not cleaned_html:
        return jsonify(error="cleaned_html is required"), 400

    selectors, err = generate_selectors(cleaned_html, hint=hint)
    if err:
        return jsonify(error=err), 422

    reasoning = selectors.pop("reasoning", "")
    return jsonify(selectors=selectors, reasoning=reasoning)


@app.route("/api/preview", methods=["POST"])
def api_preview():
    """
    Run XPath selectors against fetched HTML, return extracted articles.
    Body: { html: str, selectors: { stories_selector, url_selector, ... } }
    Returns: { articles: [...], count: int, error: str }
    """
    data = request.get_json(silent=True) or {}
    html = (data.get("html") or "").strip()
    selectors = data.get("selectors") or {}

    if not html:
        return jsonify(error="html is required"), 400
    if not selectors:
        return jsonify(error="selectors is required"), 400

    try:
        articles = extract_articles(html, selectors)
        return jsonify(articles=articles, count=len(articles))
    except (MissingSelectors, ArticleNotFound) as e:
        return jsonify(error=str(e), articles=[], count=0), 422
    except Exception as e:
        logger.exception("Unexpected error in /api/preview")
        return jsonify(error=f"Extraction error: {e}", articles=[], count=0), 500


@app.route("/api/highlight", methods=["POST"])
def api_highlight():
    """
    Return raw HTML with matched story containers highlighted.
    Body: { html: str, stories_selector: str }
    Returns: { highlighted_html: str }
    """
    data = request.get_json(silent=True) or {}
    html = (data.get("html") or "").strip()
    stories_selector = (data.get("stories_selector") or "").strip()

    if not html or not stories_selector:
        return jsonify(error="html and stories_selector are required"), 400

    highlighted = highlight_nodes(html, {"stories_selector": stories_selector})
    return jsonify(highlighted_html=highlighted)


if __name__ == "__main__":
    app.run(debug=True, port=5050)