import pytest
import tempfile
from pathlib import Path

from app.services.content_cleaner import normalize_url, format_to_structured_txt
from app.services.file_storage import _save_crawl_review, save_crawl_results


def test_url_normalization():
    # Verify variations resolve to the exact same normalized URL
    url1 = "https://example.gov/about"
    url2 = "https://example.gov/about/"
    url3 = "https://example.gov/about#section"
    url4 = "HTTPS://Example.Gov/about/"

    norm1 = normalize_url(url1)
    norm2 = normalize_url(url2)
    norm3 = normalize_url(url3)
    norm4 = normalize_url(url4)

    assert norm1 == "https://example.gov/about"
    assert norm1 == norm2 == norm3 == norm4


def test_structured_txt_output_format():
    txt_output = format_to_structured_txt(
        source_id="US-CA-OAG-MP",
        jurisdiction="California",
        url="https://oag.ca.gov/privacy/medical-privacy",
        page_title="Medical Privacy",
        crawled_at="2026-09-24T18:00:00Z",
        clean_text="State and federal laws give you rights regarding your medical records.",
        discovered_links=["https://oag.ca.gov/privacy/facts/patient-rights"]
    )

    assert "SOURCE ID: US-CA-OAG-MP" in txt_output
    assert "JURISDICTION: California" in txt_output
    assert "SOURCE URL: https://oag.ca.gov/privacy/medical-privacy" in txt_output
    assert "PAGE TITLE: Medical Privacy" in txt_output
    assert "CONTENT\n--------------------------------" in txt_output
    assert "DISCOVERED LINKS\n--------------------------------" in txt_output
    assert "- https://oag.ca.gov/privacy/facts/patient-rights" in txt_output


def test_single_crawl_review_file():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        review_records = [
            {
                "url": "https://example.gov/about",
                "classification": "NOT_RELEVANT",
                "reason": "General agency information unrelated to health privacy."
            },
            {
                "url": "https://example.gov/contact",
                "classification": "NOT_RELEVANT",
                "reason": "Contact information page with no regulatory text."
            },
            {
                "url": "https://example.gov/records",
                "classification": "UNCERTAIN",
                "reason": "Mentions records but health regulatory connection is unclear."
            },
            # Duplicate URL check
            {
                "url": "https://example.gov/about",
                "classification": "NOT_RELEVANT",
                "reason": "Duplicate entry should be ignored."
            }
        ]

        review_file = _save_crawl_review(tmp_path, review_records)
        assert review_file.exists()
        assert review_file.name == "crawl_review.txt"

        content = review_file.read_text(encoding="utf-8")

        assert "TLD CRAWL REVIEW" in content
        assert "NOT_RELEVANT" in content
        assert "UNCERTAIN" in content
        assert "URL: https://example.gov/about" in content
        assert "URL: https://example.gov/contact" in content
        assert "URL: https://example.gov/records" in content

        # Verify duplicate URL appears only ONCE
        assert content.count("URL: https://example.gov/about") == 1
