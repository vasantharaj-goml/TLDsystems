import pytest
import asyncio
from app.schemas.discovery import (
    CandidateURLRecord,
    RelevanceClassificationEnum,
    CandidateStatusEnum,
    GrokEvaluationResponse
)
from app.services.relevance_evaluator import MockRelevanceEvaluator
from app.services.grok_relevance_evaluator import GrokRelevanceEvaluator


@pytest.mark.asyncio
async def test_relevant_content_classification():
    evaluator = MockRelevanceEvaluator()
    
    test_cases = [
        ("https://example.gov/privacy/medical-records", "Medical Records Privacy"),
        ("https://example.gov/confidentiality", "Patient Information Confidentiality"),
        ("https://example.gov/health-security", "Health Information Security"),
        ("https://example.gov/records-disclosure", "Disclosure of Medical Records")
    ]

    for url, title in test_cases:
        candidate = CandidateURLRecord(
            url=url,
            source_id="test_source",
            title=title
        )
        page_data = {"content": f"Official rules regarding {title} and disclosure."}
        
        result = await evaluator.evaluate(candidate, page_data)
        assert result.classification == RelevanceClassificationEnum.RELEVANT
        assert result.confidence > 0.8
        assert len(result.reason) > 0


@pytest.mark.asyncio
async def test_not_relevant_content_classification():
    evaluator = MockRelevanceEvaluator()

    test_cases = [
        ("https://example.gov/restaurant-licensing", "Restaurant Licensing"),
        ("https://example.gov/vehicle-registration", "Vehicle Registration"),
        ("https://example.gov/tourism", "Tourism Guide"),
        ("https://example.gov/road-construction", "Road Construction Projects")
    ]

    for url, title in test_cases:
        candidate = CandidateURLRecord(
            url=url,
            source_id="test_source",
            title=title
        )
        page_data = {"content": f"Information about {title}."}
        
        result = await evaluator.evaluate(candidate, page_data)
        assert result.classification == RelevanceClassificationEnum.NOT_RELEVANT
        assert result.confidence > 0.8


@pytest.mark.asyncio
async def test_uncertain_content_classification():
    evaluator = MockRelevanceEvaluator()

    test_cases = [
        ("https://example.gov/health-insurance", "Health Insurance Licensing"),
        ("https://example.gov/hospital-construction", "Hospital Construction"),
        ("https://example.gov/professional-licensing", "Healthcare Professional Licensing"),
        ("https://example.gov/general-info", "General Health Department Information")
    ]

    for url, title in test_cases:
        candidate = CandidateURLRecord(
            url=url,
            source_id="test_source",
            title=title
        )
        page_data = {"content": f"Overview of {title}."}
        
        result = await evaluator.evaluate(candidate, page_data)
        assert result.classification == RelevanceClassificationEnum.UNCERTAIN


def test_grok_legal_boundary_sanitizer():
    evaluator = GrokRelevanceEvaluator(api_key="mock")
    
    # Raw JSON with forbidden legal compliance statement
    raw_response = """{
      "classification": "RELEVANT",
      "confidence": 0.9,
      "reason": "This law requires healthcare providers to submit records immediately.",
      "matched_topics": ["medical records"]
    }"""

    parsed = evaluator._parse_grok_response(raw_response)
    assert parsed.classification == RelevanceClassificationEnum.RELEVANT
    # Verify legal interpretation advice was stripped
    assert "This law requires healthcare providers" not in parsed.reason
    assert "health information privacy" in parsed.reason or "TLD criteria" in parsed.reason
