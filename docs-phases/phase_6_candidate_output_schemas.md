# Phase 6: Candidate Output & API Schemas

## Overview
Phase 6 created standardized Pydantic data schemas for candidates, Grok evaluation responses, discovery requests/responses, and TLD approval workflows.

## Implementation Details

* **File Added**: [`app/schemas/discovery.py`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/app/schemas/discovery.py)

### Key Enums & Schemas
1. **`RelevanceClassificationEnum`**: `RELEVANT`, `NOT_RELEVANT`, `UNCERTAIN`
2. **`CandidateStatusEnum`**: `DISCOVERED`, `RELEVANT_CANDIDATE`, `NOT_RELEVANT`, `UNCERTAIN`, `APPROVED`
3. **`CandidateURLRecord`**:
   * `url`: Target URL
   * `source_id`: Source configuration ID
   * `jurisdiction`: State/country details
   * `depth`: Crawl depth
   * `parent_url`: Referrer URL
   * `title`: Webpage title
   * `content_type`: `html` or `pdf`
   * `content_preview`: Snippet text
   * `discovery_method`: `seed_url` or `internal_link`
   * `status`: Workflow state
4. **`GrokEvaluationResponse`**:
   * `classification`: Verdict
   * `confidence`: Score (0.0 to 1.0)
   * `reason`: Factual rationale
   * `matched_topics`: Topics matched
5. **`DiscoveryRunResponse`**: Summarizes candidate counts (`discovered_count`, `relevant_count`, `not_relevant_count`, `uncertain_count`) and returns candidate records.
