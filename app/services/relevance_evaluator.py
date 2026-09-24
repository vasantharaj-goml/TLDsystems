from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.schemas.discovery import (
    GrokEvaluationResponse,
    RelevanceClassificationEnum,
    CandidateURLRecord,
    PageClassificationEnum
)
from app.services.content_cleaner import classify_page


class RelevanceEvaluator(ABC):
    """
    Abstract Base Class for AI Relevance Evaluator implementations.
    Allows switching between Grok, AWS Bedrock, OpenAI, or Mock Evaluator without changing crawler code.
    """

    @abstractmethod
    async def evaluate(
        self,
        candidate: CandidateURLRecord,
        page_data: Dict[str, Any]
    ) -> GrokEvaluationResponse:
        """
        Evaluates a candidate record and page content for TLD regulatory relevance.
        Must return structured GrokEvaluationResponse.
        """
        pass


class MockRelevanceEvaluator(RelevanceEvaluator):
    """
    Deterministic Mock Relevance Evaluator for testing without external API calls.
    """

    async def evaluate(
        self,
        candidate: CandidateURLRecord,
        page_data: Dict[str, Any]
    ) -> GrokEvaluationResponse:
        url_lower = candidate.url.lower()
        title_lower = (candidate.title or "").lower()
        content_lower = (page_data.get("content") or "").lower()
        combined_text = f"{url_lower} {title_lower} {content_lower}"

        page_class = classify_page(candidate.url, candidate.title or "", page_data.get("content") or "")

        # 0. Structural Discovery or Source Pages
        if page_class in (PageClassificationEnum.REGULATORY_DISCOVERY, PageClassificationEnum.REGULATORY_SOURCE):
            return GrokEvaluationResponse(
                classification=RelevanceClassificationEnum.RELEVANT,
                confidence=0.90,
                reason="Official government regulatory discovery index or administrative source portal.",
                matched_topics=["regulatory index", "administrative code portal"],
                page_classification=page_class
            )

        # 1. Unrelated Health Regulations (Section 13 of prompt)
        unrelated_health_topics = [
            "solid waste", "food safety", "tobacco control", "radiation safety",
            "emergency preparedness", "immunization requirements", "building permits",
            "restaurant licensing", "environmental health", "vehicle registration", "parking"
        ]
        matched_unrelated = [kw for kw in unrelated_health_topics if kw in combined_text]
        if matched_unrelated and not any(k in combined_text for k in ["privacy", "security", "confidentiality", "medical record", "patient record"]):
            return GrokEvaluationResponse(
                classification=RelevanceClassificationEnum.NOT_RELEVANT,
                confidence=0.95,
                reason=f"Content addresses general health/administrative topic '{matched_unrelated[0]}' outside TLD health privacy/security scope.",
                matched_topics=[],
                page_classification=page_class
            )

        # 2. TLD Relevant Keywords
        relevant_keywords = [
            "medical record", "medical records", "patient privacy", "patient information confidentiality",
            "health information privacy", "health information security", "confidentiality",
            "protected health information", "use of health information", "disclosure of medical records",
            "disclosure of medical", "patient information privacy", "records retention", "data breach",
            "breach notification", "phi", "hipaa", "records disposal", "patient access"
        ]

        matched_relevant = [kw for kw in relevant_keywords if kw in combined_text]
        if matched_relevant:
            return GrokEvaluationResponse(
                classification=RelevanceClassificationEnum.RELEVANT,
                confidence=0.95,
                reason=f"Content matches TLD health privacy/security scope topics: {', '.join(matched_relevant[:2])}",
                matched_topics=matched_relevant,
                page_classification=page_class
            )

        # 3. Explicit Irrelevant Keywords
        irrelevant_keywords = [
            "restaurant", "vehicle registration", "tourism",
            "road construction", "general taxation"
        ]
        matched_irrelevant = [kw for kw in irrelevant_keywords if kw in combined_text]
        if matched_irrelevant:
            return GrokEvaluationResponse(
                classification=RelevanceClassificationEnum.NOT_RELEVANT,
                confidence=0.95,
                reason=f"Content relates to unrelated administrative area: {', '.join(matched_irrelevant[:2])}",
                matched_topics=[],
                page_classification=page_class
            )

        # 4. Uncertain keywords
        uncertain_keywords = [
            "health insurance", "hospital construction", "healthcare professional licensing",
            "general health department information", "nurse licensing"
        ]
        matched_uncertain = [kw for kw in uncertain_keywords if kw in combined_text]
        if matched_uncertain:
            return GrokEvaluationResponse(
                classification=RelevanceClassificationEnum.UNCERTAIN,
                confidence=0.60,
                reason=f"Content mentions general healthcare topic '{matched_uncertain[0]}', requiring TLD manual review",
                matched_topics=[],
                page_classification=page_class
            )

        # Default fallback: UNCERTAIN
        return GrokEvaluationResponse(
            classification=RelevanceClassificationEnum.UNCERTAIN,
            confidence=0.50,
            reason="Insufficient specific context to determine TLD health information privacy relevance",
            matched_topics=[],
            page_classification=page_class
        )

