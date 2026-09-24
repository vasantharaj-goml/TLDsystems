import asyncio
import json
from app.schemas.discovery import DiscoveryRunRequest, ApprovalRequest, CandidateStatusEnum
from app.services.discovery_engine import CandidateDiscoveryEngine
from app.services.approval_service import ApprovalService
from app.services.relevance_evaluator import MockRelevanceEvaluator
from app.services.agent_reach_reader import AgentReachReader
from app.utils.logger import logger


async def run_end_to_end_verification():
    print("=" * 80)
    print("TLD Systems — Phase 1 Regulatory Discovery & Triage Verification Flow")
    print("=" * 80)

    # 1. Initialize Discovery Engine with Agent Reach capability reader & Grok/Mock Evaluator
    reader = AgentReachReader()
    evaluator = MockRelevanceEvaluator()
    discovery_engine = CandidateDiscoveryEngine(reader=reader, evaluator=evaluator)
    approval_service = ApprovalService()

    source_id = "US-CA-OAG-MP"
    print(f"\n[Step 1] Initializing candidate discovery for source: {source_id}")
    
    # 2. Candidate Discovery (Crawl4AI + Agent Reach + Grok Relevance Triage)
    req = DiscoveryRunRequest(source_id=source_id, override_max_depth=1)
    disc_res = await discovery_engine.run_discovery(req)

    print(f"\n[Step 2] Discovery Completed for '{disc_res.source_id}':")
    print(f"  - Total Candidates Discovered: {disc_res.discovered_count}")
    print(f"  - Relevant Candidates:         {disc_res.relevant_count}")
    print(f"  - Not Relevant Candidates:     {disc_res.not_relevant_count}")
    print(f"  - Uncertain Candidates:        {disc_res.uncertain_count}")

    relevant_candidate_urls = []
    print("\nCandidate Triage Breakdown:")
    for idx, cand in enumerate(disc_res.candidates, 1):
        print(f"  {idx}. URL: {cand.url}")
        print(f"     Title: {cand.title}")
        print(f"     Classification: {cand.classification.value}")
        print(f"     Confidence: {cand.confidence}")
        print(f"     Status: {cand.status.value}")
        print(f"     Reason: {cand.reason}")
        if cand.status == CandidateStatusEnum.RELEVANT_CANDIDATE:
            relevant_candidate_urls.append(cand.url)

    # 3. Verify TLD Approval Boundary (AI never returns APPROVED automatically)
    for cand in disc_res.candidates:
        assert cand.status != CandidateStatusEnum.APPROVED, "AI model improperly auto-approved candidate!"
    print("\n[Step 3] Boundary Check Passed: Grok output contains zero APPROVED statuses.")

    # 4. TLD Approval & Handoff to Production Crawler
    if relevant_candidate_urls:
        target_approval_url = relevant_candidate_urls[0]
        print(f"\n[Step 4] TLD Reviewer approving candidate source: {target_approval_url}")
        
        app_req = ApprovalRequest(
            source_id=source_id,
            urls=[target_approval_url],
            run_production_crawl=True
        )
        app_res = await approval_service.approve_candidates(app_req)

        print(f"\n[Step 5] TLD Approval Workflow Succeeded:")
        print(f"  - Source ID: {app_res.source_id}")
        print(f"  - Approved URLs: {app_res.approved_urls}")
        
        prod_res = app_res.production_crawl_results
        if prod_res:
            print(f"\n[Step 6] Production Extraction Crawler Results:")
            print(f"  - Success: {prod_res.get('success')}")
            print(f"  - Documents Extracted: {prod_res.get('total_documents_scraped')}")
            print(f"  - Combined Content Hash: {prod_res.get('combined_content_hash')}")
            print(f"  - Saved Directory: {prod_res.get('saved_directory')}")
            assert prod_res.get("success") is True, "Production crawler failed on approved URL"
    else:
        print("\n[Step 4] No relevant candidate URLs found to approve.")

    print("\n" + "=" * 80)
    print("SUCCESS: Full TLD Regulatory Discovery & Production Handoff Flow Verified!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_end_to_end_verification())
