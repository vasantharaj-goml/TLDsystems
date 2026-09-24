# Phase 8: Production Crawler Handoff

## Overview
Phase 8 connected the approved candidate sources to the existing production crawler infrastructure without modifying or rebuilding the core crawler.

## Implementation Details

* **File Modified**: [`app/services/approval_service.py`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/app/services/approval_service.py)

### Handoff Workflow
1. When `ApprovalRequest` is submitted with `run_production_crawl=True`:
   * Retrieves approved candidate URLs.
   * Copies the original source configuration from `config/source_repository.json` using `get_source_by_id`.
   * Replaces `seed_urls` with only the **approved URLs**.
   * Sets `max_depth = 1` for targeted structured extraction.
   * Invokes `execute_source_crawl(prod_config)` in [`app/services/crawler_engine.py`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/app/services/crawler_engine.py).
2. Saves extracted Markdown files, computes combined SHA-256 hash, and outputs results under `storage/extracted_content/<source_id>/<timestamp>/`.
3. Attaches production extraction summary to the `ApprovalResponse`.
