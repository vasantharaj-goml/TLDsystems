# TLD Systems Phase 1 — System Architecture & Technical Specification

> **AI Technical Reference Document**  
> *Target Audience*: AI Coding Assistants, System Architects, Developers

---

## 1. Directory & File Map

```text
web-crawler-and-scrapper/
├── app/
│   ├── api/
│   │   ├── router.py                  # Mounts /crawl, /sources, /discovery routers
│   │   └── v1/
│   │       └── endpoints/
│   │           ├── crawl.py           # Production crawl endpoint (POST /api/v1/crawl/run)
│   │           ├── sources.py         # Source registry endpoint (GET /api/v1/sources)
│   │           └── discovery.py       # Candidate discovery & TLD approval endpoints
│   ├── config.py                      # Global settings (Grok API keys, paths, CORS)
│   ├── main.py                        # FastAPI lifespan, CORS, health check
│   ├── schemas/
│   │   ├── crawl.py                   # Production crawl request/response Pydantic models
│   │   ├── source.py                  # Source repository JSON Pydantic models
│   │   └── discovery.py               # Candidate, Grok, Discovery, and Approval models
│   └── services/
│       ├── agent_reach_reader.py      # Page access capability reader (HTML/PDF)
│       ├── approval_service.py        # TLD approval workflow & production handoff
│       ├── config_loader.py           # JSON config loader for source_repository.json
│       ├── content_cleaner.py         # URL normalizer, SHA-256, structured .txt formatter
│       ├── crawler_engine.py          # Crawl4AI orchestrator & relevance-guided BFS crawler
│       ├── discovery_engine.py        # Candidate discovery & deterministic pre-filter engine
│       ├── file_storage.py            # Storage manager (.txt writer & crawl_review.txt builder)
│       ├── grok_relevance_evaluator.py# xAI Grok LLM relevance evaluator & legal sanitizer
│       ├── pdf_processor.py           # PyPDF text extraction service
│       └── relevance_evaluator.py     # Abstract RelevanceEvaluator interface & MockEvaluator
├── config/
│   └── source_repository.json         # Authoritative government source registry
├── docs-phases/                       # Phase-by-phase development documentation (Phase 1-10)
├── project_context/                   # AI memory & project context documentation
├── scripts/
│   └── verify_flow.py                 # End-to-end verification script
├── storage/                           # Disk storage
│   ├── approved_sources/              # TLD-approved candidate sources
│   ├── discovered_candidates/         # Candidate discovery JSON runs
│   └── extracted_content/             # Extracted structured .txt regulatory content
├── tests/
│   ├── test_crawler_rules.py          # Tests for URL normalization, .txt output & review file
│   ├── test_discovery.py              # Tests for candidate pre-filtering & discovery engine
│   ├── test_enhanced_crawler.py       # Tests for page classification, priority queue & scope filtering
│   └── test_relevance_evaluator.py    # Tests for Grok classification & legal guardrails
├── .env                               # Environment configuration
└── pyproject.toml / requirements.txt  # Dependencies
```

---

## 2. API Endpoints

### A. Candidate Discovery
* **Endpoint**: `POST /api/v1/discovery/run`
* **Request**:
  ```json
  {
    "source_id": "US-CA-OAG-MP",
    "override_max_depth": 2,
    "bypass_prefilter": false
  }
  ```
* **Response**:
  ```json
  {
    "source_id": "US-CA-OAG-MP",
    "status": "completed",
    "discovered_count": 125,
    "relevant_count": 18,
    "not_relevant_count": 97,
    "uncertain_count": 10,
    "candidates": [
      {
        "url": "https://oag.ca.gov/privacy/medical-privacy",
        "classification": "RELEVANT",
        "confidence": 0.95,
        "status": "RELEVANT_CANDIDATE",
        "reason": "Official government regulatory discovery index or administrative source portal.",
        "matched_topics": ["medical record"],
        "page_classification": "REGULATORY_DISCOVERY",
        "crawl_priority": "HIGH"
      }
    ]
  }
  ```

### B. TLD Source Approval & Handoff
* **Endpoint**: `POST /api/v1/discovery/approve`
* **Request**:
  ```json
  {
    "source_id": "US-CA-OAG-MP",
    "urls": [
      "https://oag.ca.gov/privacy/medical-privacy"
    ],
    "run_production_crawl": true
  }
  ```
* **Response**: Transitions candidate status to `APPROVED`, saves approval manifest to `storage/approved_sources/`, and launches production crawler on approved URLs.

### C. Direct Production Crawl
* **Endpoint**: `POST /api/v1/crawl/run`
* **Request**: `{"source_id": "US-CA-OAG-MP"}`

---

## 3. Storage Directory Layout

Every crawl run creates a timestamped folder under `storage/extracted_content/<source_id>/<timestamp>/`:

```text
storage/extracted_content/US-CA-OAG-MP/20260924_182236/
├── crawl_summary.json                                      # Metadata summary & SHA-256 combined hash
├── 001_html_oag.ca.gov_privacy_medical-privacy.txt         # Structured .txt regulatory file
├── 002_pdf_oag.ca.gov_sites_all_files_agweb_pdfs...txt     # Structured .txt parsed PDF file
└── crawl_review.txt                                        # Single review report for NOT_RELEVANT/UNCERTAIN URLs
```

### Structured `.txt` File Format:
```text
SOURCE ID: US-CA-OAG-MP
JURISDICTION: California
AGENCY: Official State Agency
DOCUMENT TYPE: Administrative Regulation
TITLE: Medical Privacy
PAGE TITLE: Medical Privacy
CHAPTER: N/A
SECTION: N/A
CITATION: N/A
SOURCE URL: https://oag.ca.gov/privacy/medical-privacy
PARENT/DISCOVERY URL: N/A
EFFECTIVE DATE: N/A
LAST UPDATED: N/A
STATUS: RELEVANT
TLD RELEVANCE: RELEVANT

CONTENT
--------------------------------
<clean extracted regulatory content>

DISCOVERED LINKS
--------------------------------
- https://oag.ca.gov/privacy/facts/patient-rights
- https://oag.ca.gov/sites/all/files/agweb/pdfs/privacy/CIS_7_Patient_Privacy_DOJ.pdf
```

### Single `crawl_review.txt` Format:
```text
TLD CRAWL REVIEW
=================

NOT_RELEVANT
----------------
URL: https://example.gov/about
Reason: General agency information unrelated to health information privacy or security.

UNCERTAIN
----------------
URL: https://example.gov/records
Reason: Page discusses records but health regulatory connection is unclear.
```

---

## 4. Environment Variables (`.env`)

```env
PROJECT_NAME="TLD Regulatory Monitoring Crawler Service"
VERSION="1.0.0"
ENVIRONMENT="development"
DEBUG=True
HOST="0.0.0.0"
PORT=8000

# Grok / xAI LLM Settings
GROK_API_KEY="xai-..."
GROK_MODEL="grok-beta"
GROK_API_BASE="https://api.x.ai/v1"
GROK_REQUEST_TIMEOUT=30
```

---

## 5. Execution & Testing Commands

* **Start FastAPI Server**:
  `uvicorn app.main:app --reload --port 8000`
* **Run Test Suite**:
  `python -m pytest tests/ -v`
* **Run End-to-End Verification Flow**:
  `$env:PYTHONPATH="."; .\venv\Scripts\python.exe scripts/verify_flow.py`
