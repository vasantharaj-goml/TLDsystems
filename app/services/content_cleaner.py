import re
import hashlib
from typing import Optional, Set, Tuple, List
from urllib.parse import urljoin, urlparse
from app.schemas.discovery import PageClassificationEnum, CrawlPriorityEnum


REGULATORY_URL_PATTERNS = [
    "/administrative-code/", "/administrative_code/", "/admin-code/", "/admincode/",
    "/statutes/", "/statute/", "/laws/", "/law/", "/rules/", "/rule/", "/regulations/",
    "/regulation/", "/regulatory/", "/code/", "/codes/", "/chapter/", "/chapters/",
    "/section/", "/sections/", "/title/", "/part/", "/subpart/", "/rulemaking/",
    "/rule-making/", "/proposed-rule/", "/proposed-rules/", "/proposed-regulation/",
    "/emergency-rule/", "/emergency-rules/", "/filing/", "/filings/", "/register/",
    "/legal/", "/legislation/", "/acts/", "/public-law/", "/api/"
]

UNRELATED_NAV_PATTERNS = [
    "/about", "/about-us", "/careers", "/employment", "/contact", "/contact-us",
    "/locations", "/login", "/administration", "/staff", "/leadership",
    "/facebook", "/twitter", "/instagram", "/youtube", "/linkedin",
    "/accessibility", "/faq", "/general-faq", "/news", "/press-releases",
    "/events", "/privacy-policy", "/terms-of-use", "/disclaimer"
]

HEALTH_KEYWORDS = [
    "health", "healthcare", "medical", "medicine", "clinical", "patient", "provider",
    "physician", "doctor", "hospital", "clinic", "medical facility", "public health",
    "medical records", "patient records", "health records", "electronic health records",
    "ehr", "emr", "phi", "protected health information", "patient data", "medical data"
]

TLD_PRIVACY_SECURITY_KEYWORDS = [
    "privacy", "data privacy", "health privacy", "medical privacy", "patient privacy",
    "confidentiality", "confidential", "security", "data security", "information security",
    "cybersecurity", "safeguards", "access control", "data protection", "breach",
    "data breach", "breach notification", "unauthorized access", "unauthorized disclosure",
    "use and disclosure", "release of information", "patient access", "records retention",
    "disposal of records", "destruction of records"
]


def calculate_sha256(text: str) -> Optional[str]:
    """Compute SHA-256 hash of cleaned text for change detection."""
    if not text:
        return None
    h = hashlib.sha256()
    h.update(text.encode("utf-8"))
    return h.hexdigest()


def normalize_url(url: str) -> str:
    """
    Normalizes a URL for strict deduplication across common variations.
    - Strips fragment identifiers (#section).
    - Lowercases scheme, hostname, and path.
    - Strips trailing slashes from path (except root '/').
    - Example: 'HTTPS://Example.Gov/About/#sec' -> 'https://example.gov/about'
    """
    if not url:
        return ""
    try:
        url_without_frag = url.strip().split("#")[0]
        parsed = urlparse(url_without_frag)
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        path = parsed.path.lower()
        if len(path) > 1 and path.endswith("/"):
            path = path[:-1]
        query = f"?{parsed.query}" if parsed.query else ""
        return f"{scheme}://{netloc}{path}{query}"
    except Exception:
        return url.strip().split("#")[0]


def is_unrelated_nav_link(url: str, text: str = "") -> bool:
    """
    Identifies obvious website navigation (About, Careers, Login, Social Media, etc.)
    which should be filtered unless there is an explicit regulatory path pattern.
    """
    try:
        parsed = urlparse(url.lower())
        path = parsed.path
        combined = f"{path} {text.lower()}".strip()

        # Explicit regulatory URL patterns override navigation exclusions
        if any(pat in path for pat in REGULATORY_URL_PATTERNS):
            return False

        for nav_pat in UNRELATED_NAV_PATTERNS:
            if nav_pat in path or f" {nav_pat.strip('/')} " in f" {combined} ":
                return True
        return False
    except Exception:
        return False


def classify_page(url: str, title: str = "", content: str = "") -> PageClassificationEnum:
    """
    Classifies page into regulatory workflow categories based on URL, title, and content preview.
    """
    url_lower = url.lower()
    title_lower = title.lower()
    content_preview = content[:1500].lower() if content else ""
    combined = f"{url_lower} {title_lower} {content_preview}"

    if "proposed" in combined and ("rule" in combined or "regulation" in combined):
        return PageClassificationEnum.PROPOSED_RULE
    if "emergency" in combined and ("rule" in combined or "regulation" in combined):
        return PageClassificationEnum.EMERGENCY_RULE
    if re.search(r"\b\d{3}-\d+-\d+\b", combined) or re.search(r"\bchapter\s+\d+\b", combined) or re.search(r"\bsection\s+\d+\b", combined):
        return PageClassificationEnum.ACTUAL_REGULATION
    if "statute" in url_lower or "statutes" in title_lower or re.search(r"\bstatute\b", title_lower):
        return PageClassificationEnum.ACTUAL_STATUTE
    if url_lower.endswith(".pdf") or "format=pdf" in url_lower or "type=pdf" in url_lower:
        return PageClassificationEnum.REGULATORY_DOCUMENT
    if "administrative-code" in url_lower or "administrative code" in title_lower or "regulations" in url_lower or "rules" in url_lower:
        if any(term in title_lower or term in url_lower for term in ["laws and regulations", "regulations.html", "rules", "index"]):
            return PageClassificationEnum.REGULATORY_DISCOVERY
        return PageClassificationEnum.REGULATORY_SOURCE
    if any(term in combined for term in ["law", "regulation", "rule", "code", "statute"]):
        return PageClassificationEnum.REGULATORY_DISCOVERY
    if is_unrelated_nav_link(url, title):
        return PageClassificationEnum.GENERAL_INFORMATION
    return PageClassificationEnum.UNKNOWN


def calculate_crawl_priority(
    url: str,
    title: str = "",
    parent_classification: Optional[PageClassificationEnum] = None,
    allowed_domains: Optional[List[str]] = None
) -> CrawlPriorityEnum:
    """
    Assigns crawl priority based on official domain, URL patterns, keywords, and parent page classification.
    """
    if is_unrelated_nav_link(url, title):
        return CrawlPriorityEnum.SKIP

    url_lower = url.lower()
    title_lower = title.lower()

    if any(pat in url_lower for pat in REGULATORY_URL_PATTERNS) or parent_classification in (PageClassificationEnum.REGULATORY_DISCOVERY, PageClassificationEnum.REGULATORY_SOURCE):
        return CrawlPriorityEnum.HIGH

    if any(k in url_lower or k in title_lower for k in HEALTH_KEYWORDS + TLD_PRIVACY_SECURITY_KEYWORDS):
        return CrawlPriorityEnum.MEDIUM

    return CrawlPriorityEnum.LOW


def format_to_structured_txt(
    source_id: str,
    jurisdiction: str,
    url: str,
    page_title: str,
    crawled_at: str,
    clean_text: str,
    discovered_links: Optional[List[str]] = None,
    parent_url: Optional[str] = None,
    agency: Optional[str] = None,
    doc_type: Optional[str] = None,
    chapter: Optional[str] = None,
    section: Optional[str] = None,
    citation: Optional[str] = None,
    effective_date: Optional[str] = None,
    last_updated: Optional[str] = None,
    status: str = "RELEVANT"
) -> str:
    """
    Formats scraped regulatory content into structured plain text (.txt).
    """
    cleaned_body = clean_text.strip() if clean_text else "No content extracted."
    
    links_section = ""
    if discovered_links:
        links_list = "\n".join([f"- {link}" for link in discovered_links])
        links_section = f"\n\nDISCOVERED LINKS\n--------------------------------\n{links_list}"

    output = (
        f"SOURCE ID: {source_id}\n"
        f"JURISDICTION: {jurisdiction}\n"
        f"AGENCY: {agency or 'Official State Agency'}\n"
        f"DOCUMENT TYPE: {doc_type or 'Administrative Regulation'}\n"
        f"TITLE: {page_title}\n"
        f"PAGE TITLE: {page_title}\n"
        f"CHAPTER: {chapter or 'N/A'}\n"
        f"SECTION: {section or 'N/A'}\n"
        f"CITATION: {citation or 'N/A'}\n"
        f"SOURCE URL: {url}\n"
        f"PARENT/DISCOVERY URL: {parent_url or 'N/A'}\n"
        f"EFFECTIVE DATE: {effective_date or 'N/A'}\n"
        f"LAST UPDATED: {last_updated or 'N/A'}\n"
        f"STATUS: {status}\n"
        f"TLD RELEVANCE: {status}\n\n"
        f"CONTENT\n"
        f"--------------------------------\n"
        f"{cleaned_body}"
        f"{links_section}"
    )
    return output


def format_to_clean_markdown(title: str, url: str, raw_markdown: str) -> str:
    """Standardizes markdown headers and strips extraneous whitespace and navigation artifacts."""
    if not raw_markdown:
        return ""

    cleaned = raw_markdown.strip()

    # Remove UI artifacts such as skip links and standalone material icon labels
    cleaned = re.sub(r"\[\s*Skip To Main Content\s*\]\([^)]+\)", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"(?m)^\s*(chevron_right|info|search|menu|expand_more)\s*$", "", cleaned)
    cleaned = re.sub(r"(?m)^\s*Courier New\s*\(Serif\)\s*$", "", cleaned, flags=re.IGNORECASE)

    # Remove codeblock fences generated by Crawl4AI for HTML <pre> containers in legal texts
    cleaned = re.sub(r"(?m)^```[a-zA-Z0-9_-]*\s*$", "", cleaned)

    # Clean whitespace-only lines
    cleaned = re.sub(r"(?m)^[ \t]+$", "", cleaned)

    # Normalize excessive newlines
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned.strip())

    # Build standardized document header
    header = f"# {title}\n\n"
    header += f"- **Official Source URL**: {url}\n"
    header += "---\n\n"

    return header + cleaned


def is_allowed_domain(url: str, allowed_domains: List[str]) -> bool:
    """Verifies if the URL matches configured allowed domains."""
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower().split(":")[0]
        if not netloc:
            return False
        return any(netloc == d.lower() or netloc.endswith("." + d.lower()) for d in allowed_domains)
    except Exception:
        return False


def is_binary_download(url: str) -> bool:
    """Prevents crawler crashes from non-HTML/PDF binary file downloads."""
    try:
        parsed = urlparse(url)
        path_lower = parsed.path.lower()
        binary_extensions = (".doc", ".docx", ".zip", ".tar", ".gz", ".exe", ".xlsx", ".xls", ".csv", ".mp3", ".mp4")
        if path_lower.endswith(binary_extensions):
            return True
        query_lower = parsed.query.lower()
        return any(f".{ext}" in query_lower for ext in ["doc", "docx", "zip", "xlsx", "csv", "exe"])
    except Exception:
        return False


def is_pdf_url(url: str) -> bool:
    """Detects whether a URL represents a PDF document via file extension or query parameter."""
    try:
        parsed = urlparse(url)
        path_lower = parsed.path.lower()
        if path_lower.endswith(".pdf"):
            return True
        query_lower = parsed.query.lower()
        pdf_indicators = ["pdf=true", "pdf=1", "format=pdf", "type=pdf", "export=pdf", "output=pdf", "download=pdf", ".pdf"]
        return any(indicator in query_lower for indicator in pdf_indicators)
    except Exception:
        return False


def classify_links(
    links: List[str], 
    base_url: str, 
    allowed_domains: List[str]
) -> Tuple[Set[str], Set[str]]:
    """
    Categorizes raw Crawl4AI extracted links into HTML sub-pages and PDF downloads.
    Filters obvious site navigation and normalizes all discovered URLs to prevent duplicates.
    """
    discovered_html: Set[str] = set()
    discovered_pdf: Set[str] = set()
    normalized_base = normalize_url(base_url)

    for link in links:
        if not link:
            continue
            
        abs_url = urljoin(base_url, link.strip())
        norm_url = normalize_url(abs_url)

        if not norm_url.startswith(("http://", "https://")):
            continue
        if allowed_domains and not is_allowed_domain(norm_url, allowed_domains):
            continue
        if is_binary_download(norm_url):
            continue
        if is_unrelated_nav_link(norm_url):
            continue

        if is_pdf_url(norm_url):
            discovered_pdf.add(norm_url)
        elif norm_url != normalized_base:
            discovered_html.add(norm_url)

    return discovered_html, discovered_pdf
