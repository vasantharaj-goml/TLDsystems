# Phase 1: Repository Inspection

## Overview
Phase 1 focused on analyzing the existing codebase structure, identifying reusable components, understanding Crawl4AI integration, and locating the exact insertion point for the candidate discovery and relevance triage workflow.

## Existing Architecture Summary

### 1. Existing Crawler Flow
* **API Entrypoint**: `POST /api/v1/crawl/run` in [`app/api/v1/endpoints/crawl.py`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/app/api/v1/endpoints/crawl.py).
* **Config Lookup**: Reads government seed parameters from [`config/source_repository.json`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/config/source_repository.json) using [`app/services/config_loader.py`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/app/services/config_loader.py).
* **Execution**: Executed by [`execute_source_crawl`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/app/services/crawler_engine.py) using Crawl4AI (`AsyncWebCrawler`).
* **Content Cleaning & Storage**: Formats HTML to Markdown using `format_to_clean_markdown` ([`app/services/content_cleaner.py`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/app/services/content_cleaner.py)), extracts PDFs using `download_and_extract_pdf` ([`app/services/pdf_processor.py`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/app/services/pdf_processor.py)), and saves results to `storage/extracted_content/<source_id>/<timestamp>/` via `save_crawl_results` ([`app/services/file_storage.py`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/app/services/file_storage.py)).

### 2. Crawl4AI Usage
* Instantiated inside `_crawl_html_pages` using `AsyncWebCrawler`.
* Configured via `_build_crawler_config` with universal boilerplate exclusions, tag filtering, timeout controls, and `CacheMode.BYPASS`.

### 3. Reusable Utilities Identified
* `classify_links`, `is_allowed_domain`, `is_pdf_url`, `is_binary_download`, `calculate_sha256` from `app.services.content_cleaner`.
* `download_and_extract_pdf` from `app.services.pdf_processor`.
* `get_source_by_id`, `load_all_sources` from `app.services.config_loader`.
* `save_crawl_results` from `app.services.file_storage`.

### 4. Agent Reach Status
* Folder `Agent-Reach` located in repository root, providing internet capability.
* Unhooked from `app/` prior to Phase 1. Designed to be integrated as an access layer (`AgentReachReader`) without performing relevance classification or legal interpretation.

### 5. Workflow Insertion Point
Discovery & triage sits **upstream** of the existing production crawler:
`Seed URL → Crawl4AI Discovery → Candidate URL Queue → Deterministic Pre-filter → Agent Reach Reader → Grok Relevance Evaluator → TLD Review & Approval → Production Crawler`.
