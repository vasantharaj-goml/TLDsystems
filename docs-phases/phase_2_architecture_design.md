# Phase 2: Target Architecture & Module Design

## Overview
Phase 2 designed the system architecture, establishing strict separation of concerns, data models, AI provider abstraction, and legal guardrails.

## Architecture Diagram

```text
Government Website (config/source_repository.json)
        ↓
    Crawl4AI (Link & Document Discovery)
        ↓
 Candidate URL Queue
        ↓
 Deterministic Pre-Filter (Keyword Optimization)
        ↓
 ┌────────────────────────────────────────┐
 │   Agent Reach Access Capability Layer  │
 │   (Reads & extracts webpage/PDF content)│
 └───────────────────┬────────────────────┘
                     ↓
 ┌────────────────────────────────────────┐
 │      Grok Relevance Evaluator          │
 │ (Semantic technical classification only)│
 └───────────────────┬────────────────────┘
                     ↓
 ┌───────────────────┴────────────────────┐
 │  RELEVANT / NOT_RELEVANT / UNCERTAIN   │
 └───────────────────┬────────────────────┘
                     ↓
                TLD Review
                     ↓
            TLD State: APPROVED
                     ↓
   Existing Production Extraction Crawler
```

## Key Architectural Principles

1. **Responsibility Separation**:
   * **Crawl4AI**: Link discovery & web traversal.
   * **Agent Reach**: Page access and content reading.
   * **Grok**: Semantic technical relevance classification.
   * **TLD Review**: Human/system approval authority.
   * **Production Crawler**: Deep structured content extraction.

2. **AI Provider Abstraction**:
   * Abstract interface `RelevanceEvaluator` allows plugging in `GrokRelevanceEvaluator`, `MockRelevanceEvaluator`, or future LLM backends without changing crawler code.

3. **Legal Boundary Enforcement**:
   * Grok classifies content relevance **only** (`RELEVANT`, `NOT_RELEVANT`, `UNCERTAIN`).
   * Grok is explicitly forbidden from giving legal advice, interpreting laws, determining compliance, or generating legal conclusions.
