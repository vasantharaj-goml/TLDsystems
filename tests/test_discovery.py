import pytest
import asyncio
from typing import Dict, Any

from app.schemas.discovery import (
    DiscoveryRunRequest,
    ApprovalRequest,
    CandidateStatusEnum,
    RelevanceClassificationEnum
)
from app.services.discovery_engine import CandidateDiscoveryEngine, deterministic_prefilter
from app.services.relevance_evaluator import MockRelevanceEvaluator
from app.services.agent_reach_reader import AgentReachReader
from app.services.approval_service import ApprovalService


class MockAgentReachReader(AgentReachReader):
    async def read_candidate_content(self, url: str, content_type: str = "html") -> Dict[str, Any]:
        url_lower = url.lower()
        if "failing-page" in url_lower:
            return {"url": url, "success": False, "error": "Connection reset by peer"}
        
        if "medical-records" in url_lower:
            title = "Medical Records Confidentiality"
            content = "Detailed state regulations regarding patient medical records privacy and disclosure."
        elif "restaurant" in url_lower:
            title = "Restaurant Licensing Rules"
            content = "Health department guidelines for commercial food service establishments."
        elif "insurance" in url_lower:
            title = "Health Insurance Regulations"
            content = "General information regarding health insurance policy filing."
        else:
            title = "Government Information Page"
            content = "General public notice."

        return {
            "url": url,
            "success": True,
            "error": None,
            "title": title,
            "headings": [title],
            "content": content,
            "content_preview": content[:200],
            "content_type": content_type
        }


def test_deterministic_prefilter():
    # Negative signal pre-filtered out
    res1 = deterministic_prefilter("https://example.gov/restaurant-licensing", "Restaurant Licensing")
    assert res1 is not None
    assert res1.classification == RelevanceClassificationEnum.NOT_RELEVANT

    # Positive signal passed through to Grok
    res2 = deterministic_prefilter("https://example.gov/medical-records-privacy", "Medical Privacy")
    assert res2 is None


@pytest.mark.asyncio
async def test_discovery_engine_flow():
    mock_reader = MockAgentReachReader()
    mock_evaluator = MockRelevanceEvaluator()

    engine = CandidateDiscoveryEngine(reader=mock_reader, evaluator=mock_evaluator)
    
    # Run candidate discovery on US-CA-OAG-MP
    req = DiscoveryRunRequest(source_id="US-CA-OAG-MP", override_max_depth=1)
    res = await engine.run_discovery(req)

    assert res.source_id == "US-CA-OAG-MP"
    assert res.status == "completed"
    assert res.discovered_count >= 1
    assert len(res.candidates) == res.discovered_count

    # Check candidate statuses
    for cand in res.candidates:
        assert cand.status in [
            CandidateStatusEnum.RELEVANT_CANDIDATE,
            CandidateStatusEnum.NOT_RELEVANT,
            CandidateStatusEnum.UNCERTAIN
        ]
        # Crucial check: Grok must NEVER return APPROVED!
        assert cand.status != CandidateStatusEnum.APPROVED


@pytest.mark.asyncio
async def test_tld_approval_workflow():
    mock_reader = MockAgentReachReader()
    mock_evaluator = MockRelevanceEvaluator()

    engine = CandidateDiscoveryEngine(reader=mock_reader, evaluator=mock_evaluator)
    await engine.run_discovery(DiscoveryRunRequest(source_id="US-CA-OAG-MP", override_max_depth=1))

    approval_service = ApprovalService()
    target_url = "https://oag.ca.gov/privacy/medical-privacy"

    # Approve candidate URL without production crawl
    app_res = await approval_service.approve_candidates(
        ApprovalRequest(source_id="US-CA-OAG-MP", urls=[target_url], run_production_crawl=False)
    )

    assert app_res.source_id == "US-CA-OAG-MP"
    assert target_url in app_res.approved_urls
