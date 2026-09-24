# Phase 7: TLD Approval Boundary

## Overview
Phase 7 established the TLD Source Approval Boundary, ensuring candidate sources are never automatically marked as approved by AI models.

## Implementation Details

* **File Added**: [`app/services/approval_service.py`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/app/services/approval_service.py)
* **Core Class**: `ApprovalService`

### Boundary Enforcement
1. **AI Output Limitation**: Grok evaluates relevance (`RELEVANT`, `NOT_RELEVANT`, `UNCERTAIN`). Grok **never** sets `status: APPROVED`.
2. **Explicit TLD Approval**: Candidate URLs transition to `CandidateStatusEnum.APPROVED` only through an explicit `POST /api/v1/discovery/approve` API call or TLD administrative action.
3. **Persistence**: Approved candidate records are saved under `storage/approved_sources/<source_id>/<timestamp>/approved.json`.
