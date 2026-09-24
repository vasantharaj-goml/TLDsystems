# Phase 11 — Regulatory Discovery Traversal, Page Classification, and Scope Filtering

## Overview
Phase 11 enhances the TLD Systems regulatory crawler to intelligently navigate from **Official Government Discovery Pages** (e.g., ADPH Laws and Regulations index) to **Official Regulatory Systems** (e.g., Alabama Administrative Code portal) down to **Actual Regulation Text** (e.g., Chapter 420-5-19-.01 Advance Directives), eliminating premature relevance cut-offs on discovery index pages and preventing scope creep from unrelated health regulations.

---

## Key Features Implemented

### 1. Structural Page Classification
Supported page classification categories (`PageClassificationEnum`):
- `REGULATORY_DISCOVERY` (e.g., "Laws and Regulations" index pages)
- `REGULATORY_SOURCE` (e.g., "Administrative Code" portals)
- `ACTUAL_REGULATION` (e.g., "420-5-19-.01")
- `ACTUAL_STATUTE`
- `REGULATORY_DOCUMENT` (e.g., Official PDFs)
- `PROPOSED_RULE`
- `EMERGENCY_RULE`
- `OFFICIAL_SUPPORTING`
- `GENERAL_INFORMATION`
- `UNKNOWN`

### 2. Regulatory Discovery Traversal Rule
- Structural discovery pages (`REGULATORY_DISCOVERY` and `REGULATORY_SOURCE`) are treated as navigation portals. They are **never stopped as `NOT_RELEVANT`** at the index level.
- Child links pointing to allowed official regulatory domains are aggressively queued and followed down to actual regulation text pages before final TLD relevance evaluation occurs.

### 3. Priority-Guided Crawl Queue
Discovered links are evaluated and scored before queueing (`CrawlPriorityEnum`):
- `HIGH`: Official regulatory domain + path pattern (`/administrative-code/`, `/statutes/`, `/rules/`, `/regulations/`, `/chapter/`, `/section/`, `.pdf`) or child of discovery portal.
- `MEDIUM`: Official health agency page with health/privacy/security terms.
- `LOW`: General info page.
- `SKIP`: Obvious website navigation (`about`, `careers`, `contact`, `locations`, `login`, `staff`, `social media`, `faq`, `press releases`).

### 4. TLD Health Privacy/Security Scope Boundaries
- **TLD Scope**: Health information privacy & security, medical record confidentiality, PHI, patient record access, records retention/disposal related to medical records, and security safeguards/breach notifications.
- **Unrelated Health Regulations**: Food safety, solid waste, tobacco control, radiation safety, emergency preparedness, and general facility licensing are classified as `NOT_RELEVANT` unless their text specifically addresses health-information privacy/security scope.

### 5. Enhanced Regulatory Metadata Output Format
Structured `.txt` records include rich regulatory metadata headers:
- `SOURCE ID`
- `JURISDICTION`
- `AGENCY`
- `DOCUMENT TYPE`
- `TITLE`
- `PAGE TITLE`
- `CHAPTER`
- `SECTION`
- `CITATION`
- `SOURCE URL`
- `PARENT/DISCOVERY URL`
- `EFFECTIVE DATE`
- `LAST UPDATED`
- `STATUS`
- `TLD RELEVANCE`

---

## Verification
- Unit & integration tests: `tests/test_enhanced_crawler.py` (15 total tests passing).
- End-to-end verification script: `scripts/verify_flow.py` (Exit code 0).
