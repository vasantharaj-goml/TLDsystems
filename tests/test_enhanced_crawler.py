import pytest
import pytest_asyncio
from app.schemas.discovery import (
    CandidateURLRecord,
    GrokEvaluationResponse,
    RelevanceClassificationEnum,
    CandidateStatusEnum,
    PageClassificationEnum,
    CrawlPriorityEnum
)
from app.services.content_cleaner import (
    normalize_url,
    classify_page,
    calculate_crawl_priority,
    is_unrelated_nav_link,
    classify_links,
    format_to_structured_txt
)
from app.services.relevance_evaluator import MockRelevanceEvaluator


@pytest.mark.asyncio
async def test_url_normalization_and_trailing_slash_duplicate():
    url1 = "HTTPS://AdminCode.Legislature.State.Al.US/Administrative-Code/420-5-19/"
    url2 = "https://admincode.legislature.state.al.us/administrative-code/420-5-19#section1"
    norm1 = normalize_url(url1)
    norm2 = normalize_url(url2)
    assert norm1 == norm2
    assert norm1 == "https://admincode.legislature.state.al.us/administrative-code/420-5-19"


@pytest.mark.asyncio
async def test_page_classification_detection():
    # Discovery page
    class1 = classify_page("https://www.alabamapublichealth.gov/about/regulations.html", "ADPH Laws and Regulations")
    assert class1 == PageClassificationEnum.REGULATORY_DISCOVERY

    # Source page / Administrative code
    class2 = classify_page("https://admincode.legislature.state.al.us/administrative-code/420-5-19", "Alabama Administrative Code 420-5-19")
    assert class2 in (PageClassificationEnum.REGULATORY_SOURCE, PageClassificationEnum.REGULATORY_DISCOVERY, PageClassificationEnum.ACTUAL_REGULATION)

    # Actual Regulation section
    class3 = classify_page("https://admincode.legislature.state.al.us/administrative-code/420-5-19-.01", "Chapter 420-5-19-.01 Advance Directives")
    assert class3 == PageClassificationEnum.ACTUAL_REGULATION

    # Document
    class4 = classify_page("https://www.alabamapublichealth.gov/privacy/notice.pdf", "Notice of Privacy Practices PDF")
    assert class4 == PageClassificationEnum.REGULATORY_DOCUMENT


@pytest.mark.asyncio
async def test_crawl_priority_calculation():
    allowed_domains = ["alabamapublichealth.gov", "legislature.state.al.us"]

    # High priority: administrative code pattern
    prio_high = calculate_crawl_priority(
        "https://admincode.legislature.state.al.us/administrative-code/420-5-19",
        "Administrative Code",
        PageClassificationEnum.REGULATORY_DISCOVERY,
        allowed_domains
    )
    assert prio_high == CrawlPriorityEnum.HIGH

    # Skip: site nav / careers
    prio_skip = calculate_crawl_priority(
        "https://www.alabamapublichealth.gov/careers/employment.html",
        "Employment Opportunities",
        PageClassificationEnum.GENERAL_INFORMATION,
        allowed_domains
    )
    assert prio_skip == CrawlPriorityEnum.SKIP


@pytest.mark.asyncio
async def test_unrelated_health_regulation_filtering():
    evaluator = MockRelevanceEvaluator()

    # Medical Privacy Regulation -> RELEVANT
    cand_privacy = CandidateURLRecord(
        url="https://admincode.legislature.state.al.us/administrative-code/420-5-19-.01",
        source_id="US-AL-ADPH",
        title="420-5-19-.01 Confidentiality of Patient Medical Records"
    )
    page_privacy = {"content": "All patient medical records and protected health information shall remain confidential and protected against unauthorized disclosure."}
    res_privacy = await evaluator.evaluate(cand_privacy, page_privacy)
    assert res_privacy.classification == RelevanceClassificationEnum.RELEVANT

    # Food Safety Health Regulation -> NOT_RELEVANT
    cand_food = CandidateURLRecord(
        url="https://admincode.legislature.state.al.us/administrative-code/420-3-1-.01",
        source_id="US-AL-ADPH",
        title="420-3-1 Food Service Establishment Sanitation and Food Handling"
    )
    page_food = {"content": "Food service establishments must maintain proper refrigeration temperatures for raw food safety and solid waste disposal."}
    res_food = await evaluator.evaluate(cand_food, page_food)
    assert res_food.classification == RelevanceClassificationEnum.NOT_RELEVANT
    assert "general health/administrative topic" in res_food.reason.lower() or "outside tld" in res_food.reason.lower()


@pytest.mark.asyncio
async def test_regulatory_child_link_classification():
    links = [
        "https://admincode.legislature.state.al.us/administrative-code/420-5-19",
        "https://www.alabamapublichealth.gov/about/careers.html",
        "https://www.alabamapublichealth.gov/privacy/guidance.pdf"
    ]
    allowed_domains = ["alabamapublichealth.gov", "legislature.state.al.us"]
    html_links, pdf_links = classify_links(links, "https://www.alabamapublichealth.gov/about/regulations.html", allowed_domains)

    assert "https://admincode.legislature.state.al.us/administrative-code/420-5-19" in html_links
    assert "https://www.alabamapublichealth.gov/privacy/guidance.pdf" in pdf_links
    # Obvious nav link should be filtered
    assert "https://www.alabamapublichealth.gov/about/careers.html" not in html_links
