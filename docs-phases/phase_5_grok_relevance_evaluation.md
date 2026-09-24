# Phase 5: Grok Relevance Evaluation

## Overview
Phase 5 implemented the semantic technical relevance classification engine powered by Grok (xAI API).

## Implementation Details

* **Files Added**:
  * [`app/services/relevance_evaluator.py`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/app/services/relevance_evaluator.py): Abstract base class `RelevanceEvaluator` and `MockRelevanceEvaluator`.
  * [`app/services/grok_relevance_evaluator.py`](file:///d:/GoML/TLDSystem/v3/web-crawler-and-scrapper/app/services/grok_relevance_evaluator.py): `GrokRelevanceEvaluator` implementation.

### Grok Prompt Specification
Uses a dedicated system prompt defining TLD Phase 1 scope:
1. Health information privacy
2. Health information security
3. Medical record confidentiality
4. Patient information privacy
5. Use or disclosure of health information
6. Medical records
7. Healthcare privacy/security requirements
8. Government regulations/rules concerning the above

### Output Format
Forces structured JSON output:
```json
{
  "classification": "RELEVANT | NOT_RELEVANT | UNCERTAIN",
  "confidence": 0.95,
  "reason": "Short factual explanation based only on the supplied content",
  "matched_topics": ["medical records", "health information privacy"]
}
```

### Legal Guardrails
Sanitizes model output to ensure Grok does **not**:
* Interpret legal meaning
* Provide legal advice
* Determine compliance or non-compliance
* State legal mandates or obligations
