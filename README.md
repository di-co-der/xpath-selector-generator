Here’s your updated README with **`pyenv` instead of `venv`**, keeping it production-clean and developer-friendly:

---

````markdown
# XPath Selector Generator

A lightweight, stateless web tool that fetches a static HTML page and uses an LLM to generate XPath selectors for extracting structured article data (title, URL, date, summary).

## Constraints
- **Static HTML only** — no JS-rendered, authenticated, or infinite-scroll pages
- **Stateless** — no DB, no cache, all in-memory per request

## Stack
- Python 3.11+
- Flask
- lxml (XPath execution)
- BeautifulSoup4 (HTML cleaning)
- Requests (HTTP fetch)
- DeepInfra LLM API

## Setup (using pyenv)

### 1. Install Python via pyenv
```bash
pyenv install 3.11.9
pyenv local 3.11.9
````

### 2. Verify Python version

```bash
python --version
# Expected: Python 3.11.9
```

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Environment variables

```bash
cp .env.example .env
# Edit .env and add your DEEPINFRA_API_KEY
```

## Run

```bash
python app.py
# → http://localhost:5050
```

## API Endpoints

| Method | Path              | Description                         |
| ------ | ----------------- | ----------------------------------- |
| POST   | `/api/fetch-html` | Fetch & clean HTML from URL         |
| POST   | `/api/generate`   | LLM → XPath selectors               |
| POST   | `/api/preview`    | Run selectors, return articles      |
| POST   | `/api/highlight`  | HTML with matched nodes highlighted |

## User Flow

1. Enter URL → **Fetch HTML**
2. Click **Generate Selectors with AI**
3. Review/edit selectors
4. **Preview Extraction** → see articles table
5. Click 🔆 to highlight matched containers in the page

## Architecture

```
app.py          Flask routes + orchestration
fetcher.py      Stateless GET fetcher (static HTML only)
llm_service.py  clean_html_for_llm + call_deepinfra_llm (from service.py)
extractor.py    extract_articles + highlight_nodes (from articles_extractor.py)
templates/      Single-page UI
```

## Notes

* `pyenv` ensures consistent Python version across environments.
* This setup installs dependencies globally for the selected pyenv version.
* For stricter isolation, consider combining `pyenv` with `pyenv-virtualenv`.

```

