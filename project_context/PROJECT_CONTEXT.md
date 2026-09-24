# TLD Systems Phase 1 — Regulatory Monitoring & Discovery System Context

> **AI Agent Memory & Context Document**  
> *Last Updated: September 2026*  
> *Maintainer Note*: Update this document and related files in `project_context/` whenever making architectural or functional changes to this repository.

---

## 1. Project Overview & Objective

This repository contains the **Phase 1 Regulatory Monitoring Service** for **TLD Systems**. 

The goal of the system is to discover, evaluate, approve, and extract official U.S. state and federal government regulations and administrative standards concerning:
1. Health information privacy
2. Health information security
3. Medical record confidentiality
4. Patient information privacy
5. Use or disclosure of health information
6. Patient access rights to medical records
7. Records retention and destruction/disposal for medical records
8. Security safeguards and data breach notifications involving health information

The architecture separates **Candidate Discovery & Triage** (finding and evaluating candidate URLs using AI) from **Production Extraction** (scraping structured regulatory text from TLD-approved sources only).

---

## 2. High-Level Architecture Flow

```text
Official Government Seed / Discovery Page (config/source_repository.json)
        ↓
    Crawl4AI (Link & Document Traversal)
        ↓
  Link Priority & Filtering (`is_unrelated_nav_link`, `calculate_crawl_priority`)
        ↓
  URL Normalization & Deduplication (`normalize_url`)
        ↓
  Page Classification (`classify_page`: REGULATORY_DISCOVERY / SOURCE vs ACTUAL_REGULATION)
        ↓
 ┌──────────────────────────────────────────────────┐
 │  REGULATORY_DISCOVERY / REGULATORY_SOURCE INDEX  │
 └────────────────────────┬─────────────────────────┘
                          ↓
          Aggressively Expand Child Links
                          ↓
 ┌──────────────────────────────────────────────────┐
 │  ACTUAL_REGULATION / STATUTE / REGULATORY_DOC   │
 └────────────────────────┬─────────────────────────┘
                          ↓
 ┌──────────────────────────────────────────────────┐
 │           Grok Relevance Evaluator               │
 │ (TLD Privacy/Security Scope vs Unrelated Health) │
 └────────────────────────┬─────────────────────────┘
                          ↓
 ┌────────────────────────┴─────────────────────────┐
 │       RELEVANT / NOT_RELEVANT / UNCERTAIN        │
 └────────────────────────┬─────────────────────────┘
           ┌──────────────┼──────────────┐
           ↓              ↓              ↓
       RELEVANT       NOT_RELEVANT     UNCERTAIN
           ↓              ↓              ↓
     Expand Links        STOP           STOP
           ↓                             ↓
      TLD Review                 `crawl_review.txt`
           ↓
      TLD APPROVED
           ↓
   Production Extraction (.txt structured records)
```

---

## 3. Core Component Responsibilities

| Component | Responsible Module | Primary Function |
| :--- | :--- | :--- |
| **Source Repository** | [`config/source_repository.json`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/config/source_repository.json) | Authoritative seed configuration containing source metadata, base URLs, seed URLs, and domain boundaries (`allowed_domains`). |
| **Candidate Discovery Engine** | [`app/services/discovery_engine.py`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/app/services/discovery_engine.py) | Priority-guided candidate discovery using Crawl4AI up to `max_depth`. |
| **URL Normalizer & Cleaner** | [`app/services/content_cleaner.py`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/app/services/content_cleaner.py) | `normalize_url()` handles casing, fragment removal (`#sec`), trailing slashes (`/about/` = `/about`), navigation filtering (`is_unrelated_nav_link`), page classification (`classify_page`), and priority calculation (`calculate_crawl_priority`). |
| **Agent Reach Reader** | [`app/services/agent_reach_reader.py`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/app/services/agent_reach_reader.py) | Access/read layer. Opens web pages and PDFs, extracts headings and text for evaluation without performing link crawling or classification. |
| **Grok Relevance Evaluator** | [`app/services/grok_relevance_evaluator.py`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/app/services/grok_relevance_evaluator.py) | LLM semantic classifier using xAI API (or auto-detected Groq free tier). Categorizes content as `RELEVANT`, `NOT_RELEVANT`, or `UNCERTAIN`. Enforces legal guardrails (no legal advice/interpretation) and distinguishes TLD privacy/security scope from general health regulations. |
| **TLD Approval Boundary** | [`app/services/approval_service.py`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/app/services/approval_service.py) | Manages status transition from `RELEVANT_CANDIDATE` to `APPROVED`. Grok **never** sets `APPROVED` status automatically. |
| **Production Crawler Engine** | [`app/services/crawler_engine.py`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/app/services/crawler_engine.py) | Performs targeted extraction on approved sources. Traverses discovery index pages down to actual regulations. Expands crawl branches for `RELEVANT` text pages and structural discovery portals. |
| **Storage Manager** | [`app/services/file_storage.py`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/app/services/file_storage.py) | Saves extracted regulatory content as structured `.txt` files and creates a single `crawl_review.txt` per crawl run for `NOT_RELEVANT`, `UNCERTAIN`, and `EVALUATION_ERROR` pages. |

---

## 4. Key Business Rules & Guardrails

1. **Regulatory Discovery Index Traversal**:
   - `REGULATORY_DISCOVERY` and `REGULATORY_SOURCE` pages (index listings of laws, rules, chapters, administrative codes) are structural discovery portals. They are **not** stopped as `NOT_RELEVANT` at the index level. Their child links are aggressively followed to reach `ACTUAL_REGULATION` text pages.
   - Once actual regulation text is reached, full TLD relevance evaluation is performed.

2. **Relevance-Guided Expansion**:
   - `RELEVANT` pages -> crawl child regulatory links.
   - `NOT_RELEVANT` pages -> **STOP** expanding child links on that branch.
   - `UNCERTAIN` pages -> **STOP** expanding child links on that branch.
   - `EVALUATION_ERROR` pages -> **STOP** expanding branch without marking as `NOT_RELEVANT` or `UNCERTAIN`.

3. **Deduplication & Link Filtering**:
   - Every URL is normalized via `normalize_url(url)` before checking `visited_urls`.
   - Obvious site navigation (About, Careers, Contact, Staff, Login, Social Media) is skipped unless it matches explicit regulatory path patterns.
   - Discovered links are assigned priorities (`HIGH`, `MEDIUM`, `LOW`, `SKIP`) and queued accordingly.

4. **Scope Boundaries (TLD Scope vs General Health Regulations)**:
   - General health regulations (food safety, solid waste, tobacco control, radiation safety, emergency preparedness, general licensing) that do NOT address health information privacy, security, confidentiality, medical records, or breach notification are classified as `NOT_RELEVANT`.

5. **Storage Format**:
   - Extracted regulatory pages are stored as structured `.txt` files with header metadata (`SOURCE ID`, `JURISDICTION`, `AGENCY`, `DOCUMENT TYPE`, `TITLE`, `PAGE TITLE`, `CHAPTER`, `SECTION`, `CITATION`, `SOURCE URL`, `PARENT/DISCOVERY URL`, `EFFECTIVE DATE`, `LAST UPDATED`, `STATUS`, `TLD RELEVANCE`), `CONTENT`, and `DISCOVERED LINKS`.
   - Each crawl run outputs exactly **one** `crawl_review.txt` summarizing all `NOT_RELEVANT`, `UNCERTAIN`, and `EVALUATION_ERROR` URLs evaluated.

6. **Legal Boundary**:
   - Grok evaluates **content relevance only**.
   - Grok output is sanitized to strip legal advice phrasing (`This law requires...`, `Compliance mandated`).

7. **AI Memory & Knowledge Recovery**:
   - Refer to [`project_context/ANALYSIS_PATTERNS.md`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/project_context/ANALYSIS_PATTERNS.md) for instant context recovery on Groq free-tier fallback, `EVALUATION_ERROR` isolation, PDF relevance evaluation, and domain boundary troubleshooting.


