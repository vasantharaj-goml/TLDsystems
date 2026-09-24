# TLD Systems Phase 1 — Regulatory Candidate Discovery & Grok Triage Documentation

This directory contains comprehensive phase-by-phase technical documentation for the candidate discovery and Grok relevance triage system implemented for TLD Systems Phase 1 Regulatory Monitoring.

## Phase Documentation Index

1. [`phase_1_repository_inspection.md`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/docs-phases/phase_1_repository_inspection.md): Inspection of existing codebase, Crawl4AI usage, and insertion point analysis.
2. [`phase_2_architecture_design.md`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/docs-phases/phase_2_architecture_design.md): System architecture, responsibility isolation, AI abstraction, and legal guardrails.
3. [`phase_3_candidate_discovery.md`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/docs-phases/phase_3_candidate_discovery.md): `CandidateDiscoveryEngine` implementation and deterministic keyword pre-filtering.
4. [`phase_4_agent_reach_access.md`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/docs-phases/phase_4_agent_reach_access.md): `AgentReachReader` access capability layer and content reading.
5. [`phase_5_grok_relevance_evaluation.md`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/docs-phases/phase_5_grok_relevance_evaluation.md): `GrokRelevanceEvaluator` implementation, system prompts, JSON formatting, and legal sanitizer.
6. [`phase_6_candidate_output_schemas.md`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/docs-phases/phase_6_candidate_output_schemas.md): Pydantic schemas for candidate records, Grok outputs, and API models.
7. [`phase_7_tld_approval_boundary.md`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/docs-phases/phase_7_tld_approval_boundary.md): `ApprovalService` ensuring AI output never auto-approves candidate sources.
8. [`phase_8_production_crawler_handoff.md`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/docs-phases/phase_8_production_crawler_handoff.md): Handoff workflow from approved candidates to existing production crawler.
9. [`phase_9_testing_suite.md`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/docs-phases/phase_9_testing_suite.md): Pytest unit and integration testing suite (`tests/test_relevance_evaluator.py`, `tests/test_discovery.py`).
10. [`phase_10_end_to_end_verification.md`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/docs-phases/phase_10_end_to_end_verification.md): Verification results running full discovery, triage, approval, and extraction pipeline.

---

## All Added & Modified Files Index

### Configuration & Routing
* [`app/config.py`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/app/config.py): Grok API credentials & storage directories.
* [`app/api/router.py`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/app/api/router.py): Mounted `/discovery` endpoint group.

### Schemas
* [`app/schemas/discovery.py`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/app/schemas/discovery.py): Candidate, Grok evaluation, discovery run, and approval models.

### Service Layer
* [`app/services/agent_reach_reader.py`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/app/services/agent_reach_reader.py): Agent Reach page access capability wrapper.
* [`app/services/relevance_evaluator.py`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/app/services/relevance_evaluator.py): Abstract evaluator interface & `MockRelevanceEvaluator`.
* [`app/services/grok_relevance_evaluator.py`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/app/services/grok_relevance_evaluator.py): Grok LLM classifier & legal guardrails.
* [`app/services/discovery_engine.py`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/app/services/discovery_engine.py): Candidate discovery & pre-filtering orchestrator.
* [`app/services/approval_service.py`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/app/services/approval_service.py): TLD approval state manager & production crawler handoff.

### API Layer
* [`app/api/v1/endpoints/discovery.py`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/app/api/v1/endpoints/discovery.py): API endpoints `POST /api/v1/discovery/run` and `POST /api/v1/discovery/approve`.

### Tests & Scripts
* [`tests/test_relevance_evaluator.py`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/tests/test_relevance_evaluator.py): Classification & legal sanitizer tests.
* [`tests/test_discovery.py`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/tests/test_discovery.py): Pre-filter, discovery flow, and approval boundary tests.
* [`scripts/verify_flow.py`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/scripts/verify_flow.py): End-to-end verification script.
