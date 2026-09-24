# Phase 3: Candidate Discovery Implementation

## Overview
Phase 3 implemented the `CandidateDiscoveryEngine` which uses Crawl4AI to discover internal HTML and PDF links from configured government seed URLs up to `max_depth`.

## Implementation Details

* **File Added**: [`app/services/discovery_engine.py`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/app/services/discovery_engine.py)
* **Core Class**: `CandidateDiscoveryEngine`

### Discovery Workflow
1. Loads source metadata from `config/source_repository.json` using `get_source_by_id`.
2. Uses Crawl4AI `AsyncWebCrawler` with `CrawlerRunConfig(cache_mode=CacheMode.BYPASS)` to crawl the seed URL.
3. Classifies extracted links using `classify_links()` into HTML sub-pages and PDF downloads while respecting `allowed_domains`.
4. Constructs `CandidateURLRecord` items with metadata (`source_id`, `jurisdiction`, `depth`, `parent_url`, `content_type`, `discovery_method`).
5. Applies deterministic keyword pre-filtering (`deterministic_prefilter`) to skip obvious irrelevant administrative links (e.g., parking, vehicle, restaurant) before calling Grok.

### Deterministic Pre-filtering Signals
* **Positive Signals**: `medical`, `medical-record`, `patient`, `health-information`, `health-information-privacy`, `confidentiality`, `hipaa`, `privacy-rights`.
* **Negative Signals**: `restaurant`, `vehicle`, `tourism`, `tax`, `building`, `employment`, `procurement`, `road`, `transportation`, `parking`.
