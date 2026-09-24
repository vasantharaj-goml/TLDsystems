import json
import httpx
from typing import Dict, Any, Optional
from app.config import settings
from app.schemas.discovery import (
    GrokEvaluationResponse,
    RelevanceClassificationEnum,
    CandidateURLRecord
)
from app.services.relevance_evaluator import RelevanceEvaluator, MockRelevanceEvaluator
from app.utils.logger import logger

GROK_SYSTEM_PROMPT = """You are a technical relevance classifier for the TLD Systems regulatory-source discovery pipeline.

Your task is to determine whether a government webpage or document is relevant to TLD Systems Phase 1 regulatory monitoring.

TLD Scope includes:
1. Health information privacy & security
2. Medical record confidentiality
3. Patient information privacy
4. Use or disclosure of health/medical records
5. Patient access rights to medical records
6. Records retention and destruction/disposal for medical records
7. Security safeguards and data breach notification requirements involving health information

IMPORTANT CLASSIFICATION RULES:
- Distinguish REGULATORY_DISCOVERY or REGULATORY_SOURCE index pages from ACTUAL_REGULATION text pages.
- Structural discovery pages (lists of laws, rules, chapters, administrative codes) are useful regulatory portals and should be classified as RELEVANT with page_classification set to REGULATORY_DISCOVERY or REGULATORY_SOURCE.
- General health regulations (food safety, solid waste, tobacco control, radiation safety, emergency preparedness, general licensing) that DO NOT address health-information privacy/security scope must be classified as NOT_RELEVANT.

DO NOT:
- Interpret laws or legal meaning
- Give legal advice or compliance recommendations
- Generate legal conclusions

Return ONLY JSON matching this structure:
{
  "classification": "RELEVANT | NOT_RELEVANT | UNCERTAIN",
  "confidence": 0.0,
  "reason": "Short factual explanation based only on supplied content",
  "matched_topics": ["medical records", "health information privacy"],
  "page_classification": "REGULATORY_SOURCE | REGULATORY_DISCOVERY | ACTUAL_REGULATION | ACTUAL_STATUTE | REGULATORY_DOCUMENT | GENERAL_INFORMATION"
}
"""


class GrokRelevanceEvaluator(RelevanceEvaluator):
    """
    Implementation of RelevanceEvaluator using Grok (xAI API).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        api_base: Optional[str] = None,
        timeout: Optional[int] = None
    ):

        raw_key = api_key or settings.GROK_API_KEY
        self.api_key = raw_key.strip().strip('"').strip("'") if raw_key else ""
        self.model = model or settings.GROK_MODEL
        self.api_base = (api_base or settings.GROK_API_BASE).rstrip("/")
        self.timeout = timeout or settings.GROK_REQUEST_TIMEOUT
        self._fallback_mock = MockRelevanceEvaluator()

        # Safe diagnostic logging (Never log full key!)
        key_loaded = bool(self.api_key)
        prefix = self.api_key[:4] if self.api_key else "None"
        length = len(self.api_key) if self.api_key else 0

        if key_loaded and self.api_key.startswith("gsk_"):
            # Automatically support Groq 100% Free Tier API keys (gsk_...)
            self.api_base = "https://api.groq.com/openai/v1"
            if "grok" in self.model.lower():
                self.model = "llama-3.3-70b-versatile"
            logger.info(f"Groq Free Tier key detected (Prefix: '{prefix}...'). Auto-configured endpoint: {self.api_base} | Model: {self.model}")
        else:
            logger.info(f"Grok Evaluator initialized | API Key Loaded: {key_loaded} | Prefix: '{prefix}...' | Length: {length} | Base URL: {self.api_base} | Model: {self.model}")


    async def evaluate(
        self,
        candidate: CandidateURLRecord,
        page_data: Dict[str, Any]
    ) -> GrokEvaluationResponse:
        """
        Evaluates candidate relevance via Grok LLM API.
        If no key is configured, falls back to MockRelevanceEvaluator for testing.
        If API call fails, returns EVALUATION_ERROR without misclassifying as NOT_RELEVANT or UNCERTAIN.
        """
        if not self.api_key:
            logger.info("GROK_API_KEY is not configured. Falling back to MockRelevanceEvaluator.")
            return await self._fallback_mock.evaluate(candidate, page_data)

        user_prompt = self._build_user_prompt(candidate, page_data)
        endpoint = f"{self.api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": GROK_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"}
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(endpoint, headers=headers, json=payload)
                if resp.status_code != 200:
                    err_msg = f"Grok API HTTP error {resp.status_code}: {resp.text}"
                    logger.error(err_msg)
                    return GrokEvaluationResponse(
                        classification=RelevanceClassificationEnum.EVALUATION_ERROR,
                        confidence=0.0,
                        reason=err_msg,
                        matched_topics=[]
                    )

                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                return self._parse_grok_response(content)

        except Exception as e:
            err_msg = f"Error calling Grok Relevance API: {str(e)}"
            logger.error(err_msg)
            return GrokEvaluationResponse(
                classification=RelevanceClassificationEnum.EVALUATION_ERROR,
                confidence=0.0,
                reason=err_msg,
                matched_topics=[]
            )


    def _build_user_prompt(self, candidate: CandidateURLRecord, page_data: Dict[str, Any]) -> str:
        headings = page_data.get("headings", [])
        headings_str = "\n".join([f"- {h}" for h in headings[:10]]) if headings else "None"
        content_snippet = (page_data.get("content") or page_data.get("content_preview") or "")[:2500]

        return f"""Evaluate candidate webpage relevance for TLD Systems:

Candidate URL: {candidate.url}
Source ID: {candidate.source_id}
Parent URL: {candidate.parent_url or 'N/A'}
Crawl Depth: {candidate.depth}
Content Type: {candidate.content_type}
Page Title: {page_data.get('title') or candidate.title or 'N/A'}

Page Headings:
{headings_str}

Page Content Snippet:
{content_snippet}
"""

    def _parse_grok_response(self, raw_json: str) -> GrokEvaluationResponse:
        try:
            parsed = json.loads(raw_json)
            classification_str = str(parsed.get("classification", "")).upper()
            
            if classification_str not in [e.value for e in RelevanceClassificationEnum]:
                classification_str = RelevanceClassificationEnum.UNCERTAIN.value

            classification = RelevanceClassificationEnum(classification_str)
            confidence = float(parsed.get("confidence", 0.5))
            confidence = max(0.0, min(1.0, confidence))
            reason = str(parsed.get("reason", "No reason provided by model.")).strip()
            matched_topics = list(parsed.get("matched_topics", []))

            # Sanitize reason to enforce legal boundary (strip legal advice phrasing if present)
            forbidden_prefixes = [
                "This law requires", "Healthcare providers must", "This law means",
                "The regulation mandates", "Compliant", "Non-compliant"
            ]
            for prefix in forbidden_prefixes:
                if prefix.lower() in reason.lower():
                    reason = "Content discusses topics related to health information privacy/security matching TLD criteria."
                    break

            return GrokEvaluationResponse(
                classification=classification,
                confidence=confidence,
                reason=reason,
                matched_topics=matched_topics
            )
        except Exception as e:
            logger.error(f"Failed to parse Grok JSON response: {str(e)}. Raw: {raw_json}")
            return GrokEvaluationResponse(
                classification=RelevanceClassificationEnum.UNCERTAIN,
                confidence=0.5,
                reason="Grok response parsing failure; defaulted to UNCERTAIN for TLD review.",
                matched_topics=[]
            )
