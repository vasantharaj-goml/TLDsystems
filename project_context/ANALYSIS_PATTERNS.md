# TLD Systems Phase 1 — Frequent Analysis Patterns & Knowledge Recovery

> **AI Memory & Analysis Playbook**  
> *Target Audience*: AI Agents, Pair Programmers, Developers  
> *Purpose*: Quick context recovery and diagnostic workflows for common issues in this codebase.

---

## 1. Fast Context Recovery Checklist

When resuming work or starting a new turn on this repository, inspect these key files in order:
1. **Source Configuration**: [`config/source_repository.json`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/config/source_repository.json)
2. **Environment & API Keys**: [`.env`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/.env)
3. **Core Crawler Engine**: [`app/services/crawler_engine.py`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/app/services/crawler_engine.py)
4. **Grok Evaluator & Guardrails**: [`app/services/grok_relevance_evaluator.py`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/app/services/grok_relevance_evaluator.py)
5. **Storage & Review Writer**: [`app/services/file_storage.py`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/app/services/file_storage.py)

---

## 2. Common Diagnostic & Troubleshooting Patterns

### Pattern A: Crawl Fails to Follow Redirects or External Government Links
* **Symptom**: Seed URL crawls fine, but external state code pages (e.g. `legislature.state.al.us`) are skipped.
* **Root Cause**: Domain boundary restriction in `allowed_domains`.
* **Fix**: Ensure exact domain host strings are in `allowed_domains` in `config/source_repository.json`:
  ```json
  "allowed_domains": [
    "alabamapublichealth.gov",
    "legislature.state.al.us",
    "state.al.us",
    "adph.org"
  ]
  ```
  *Note*: Use domain hostnames (e.g. `legislature.state.al.us`), NOT full URLs with `https://`.

### Pattern B: API Key Rejection (xAI `xai-` vs. Groq `gsk_`)
* **Symptom**: `Grok API HTTP error 400: Incorrect API key provided`.
* **Root Cause**: Key in `.env` starts with `gsk_` (Groq API key) while `GROK_API_BASE` points to `https://api.x.ai/v1`.
* **Automatic Handling**: `GrokRelevanceEvaluator` auto-detects `gsk_` keys and routes requests to Groq's 100% Free Tier API (`https://api.groq.com/openai/v1`) using `llama-3.3-70b-versatile`.
* **API Key Errors**: If key is invalid/revoked, the engine emits `EVALUATION_ERROR` and halts branch expansion **without misclassifying pages as `NOT_RELEVANT` or `UNCERTAIN`**.

### Pattern C: PDF Extraction & Relevance Checks
* **Rule**: PDFs discovered on HTML pages undergo text extraction via PyPDF AND Grok relevance evaluation before saving.
* **Behavior**:
  - `RELEVANT` PDFs → Saved as structured `.txt` files in `storage/extracted_content/`.
  - `NOT_RELEVANT` / `UNCERTAIN` PDFs → Added to `review_records` and summarized in `crawl_review.txt`.

### Pattern D: Deduplication & Trailing Slashes
* **Rule**: All URLs are passed through `normalize_url(url)` in [`app/services/content_cleaner.py`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/app/services/content_cleaner.py#L16-L38).
* **Behavior**: Strips fragment identifiers (`#sec`), lowercases scheme/netloc, strips trailing slashes (`/about/` = `/about`). Prevents duplicate scraping.

---

## 3. Verification & Execution Commands

```bash
# Run full pytest suite (10 unit/integration tests)
.\venv\Scripts\python.exe -m pytest tests/ -v

# Run end-to-end verification script
$env:PYTHONPATH="."; .\venv\Scripts\python.exe scripts/verify_flow.py

# Launch API server locally
uvicorn app.main:app --reload --port 8000
```
