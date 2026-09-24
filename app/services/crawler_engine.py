import sys
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Set, Tuple

# Ensure Windows support for async event loops
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from app.services.content_cleaner import (
    calculate_sha256,
    format_to_clean_markdown,
    format_to_structured_txt,
    normalize_url,
    classify_links,
    is_pdf_url,
    classify_page,
    calculate_crawl_priority
)
from app.services.pdf_processor import download_and_extract_pdf
from app.services.file_storage import save_crawl_results
from app.schemas.discovery import CandidateURLRecord, RelevanceClassificationEnum, PageClassificationEnum, CrawlPriorityEnum
from app.services.grok_relevance_evaluator import GrokRelevanceEvaluator
from app.utils.logger import logger


def _build_crawler_config(crawl_settings: Dict[str, Any]) -> CrawlerRunConfig:
    """Builds Crawl4AI CrawlerRunConfig based on source metadata and universal exclusions."""
    request_timeout = int(crawl_settings.get("request_timeout_seconds", 30))
    delay_before_return = float(crawl_settings.get("delay_before_return_html", 2.0))
    wait_until = str(crawl_settings.get("wait_until", "domcontentloaded"))
    process_iframes = bool(crawl_settings.get("process_iframes", True))

    # Universal Boilerplate Exclusion List for generic multi-website scraping
    universal_excluded_selectors = (
        # Semantic elements & ARIA landmarks
        "header, nav, footer, aside, form, "
        "[role='navigation'], [role='banner'], [role='contentinfo'], [role='search'], [role='complementary'], "
        # Common layout IDs
        "#header, #footer, #sidebar, #mainnav, #nav, #menu, #sidemenu, #breadcrumbs, #topbar, #NavTree, "
        # Common layout classes & noise
        ".header, .footer, .navbar, .nav, .sidebar, .menu, .breadcrumbs, .pagination, "
        ".social-share, .cookie-banner, .advertisement, .ad, .modal, .popup, .skip-link, "
        ".search-container, .site-information, .nodisplay, .hidden, .statuteTree, .dvControls, .leftSpace, "
        # Common UI Component Frameworks (Angular Material, Bootstrap, Tailwind, MUI, WordPress)
        "mat-toolbar, mat-sidenav, mat-nav-list, mat-form-field, mat-select, mat-option, "
        "mat-tree, mat-nested-tree-node, mat-accordion, mat-expansion-panel, mat-tab-group, mat-tab-header, "
        ".mat-drawer, .offcanvas, .drawer, .site-header, .site-footer, .nav-menu, .widget-area, "
        # Form controls & Interactive navigation
        "select, option, button, input, textarea, label, datalist, fieldset, legend"
    )

    custom_selectors = crawl_settings.get("excluded_selector")
    if custom_selectors:
        excluded_selector = f"{universal_excluded_selectors}, {custom_selectors}"
    else:
        excluded_selector = universal_excluded_selectors

    universal_excluded_tags = [
        "nav", "header", "footer", "script", "style", "aside", "form", "noscript", "svg",
        "select", "option", "button", "input", "textarea", "label", "fieldset", "legend"
    ]
    custom_tags = crawl_settings.get("excluded_tags", [])
    excluded_tags = list(dict.fromkeys(universal_excluded_tags + custom_tags))

    crawl_kwargs = {
        "cache_mode": CacheMode.BYPASS,
        "page_timeout": request_timeout * 1000,
        "wait_until": wait_until,
        "delay_before_return_html": delay_before_return,
        "process_iframes": process_iframes,
        "remove_forms": True,
        "excluded_tags": excluded_tags,
        "excluded_selector": excluded_selector
    }

    # Dynamic waiting: supports wait_for duration (e.g. "wait:3") or selector
    if crawl_settings.get("wait_for"):
        crawl_kwargs["wait_for"] = crawl_settings["wait_for"]
    elif crawl_settings.get("wait_for_selector"):
        selector = crawl_settings["wait_for_selector"]
        crawl_kwargs["wait_for"] = selector if selector.startswith(("css:", "js:", "wait:")) else f"css:{selector}"
        crawl_kwargs["wait_for_timeout"] = min(request_timeout, 10) * 1000

    if crawl_settings.get("target_css_selector"):
        crawl_kwargs["css_selector"] = crawl_settings["target_css_selector"]

    return CrawlerRunConfig(**crawl_kwargs)


async def _run_in_proactor_if_needed(coro_fn, *args, **kwargs):
    """
    On Windows, Playwright requires a ProactorEventLoop to manage browser subprocesses.
    When running under Uvicorn with reload/workers on Windows, Uvicorn initializes a SelectorEventLoop,
    which raises NotImplementedError during subprocess transport creation.
    This helper dispatches the crawler execution to a thread running a ProactorEventLoop if needed.
    """
    if sys.platform == "win32":
        loop = asyncio.get_running_loop()
        if not isinstance(loop, getattr(asyncio, "ProactorEventLoop", ())):
            def _worker():
                proactor_loop = asyncio.ProactorEventLoop()
                asyncio.set_event_loop(proactor_loop)
                try:
                    return proactor_loop.run_until_complete(coro_fn(*args, **kwargs))
                finally:
                    try:
                        proactor_loop.close()
                    except Exception:
                        pass
            return await asyncio.to_thread(_worker)
    return await coro_fn(*args, **kwargs)


async def _crawl_html_pages(
    target_url: str,
    max_depth: int,
    follow_links: bool,
    allowed_domains: List[str],
    source_name: str,
    source_id: str,
    jurisdiction_str: str,
    crawled_at: str,
    crawl_config: CrawlerRunConfig,
    crawl_settings: Dict[str, Any] = None
) -> Tuple[List[Dict[str, Any]], Set[str], List[Dict[str, Any]], bool, str]:
    """
    Executes Priority-guided Breadth-First Search for HTML pages up to max_depth.
    Traverses REGULATORY_DISCOVERY and REGULATORY_SOURCE index pages to reach ACTUAL_REGULATION text.
    Only expands child links for RELEVANT pages or REGULATORY_DISCOVERY/SOURCE index pages.
    Deduplicates URLs using normalize_url().
    Returns: (scraped_documents, discovered_pdf_urls, review_records, success, error_message)
    """
    crawl_settings = crawl_settings or {}
    scraped_documents: List[Dict[str, Any]] = []
    visited_urls: Set[str] = set()
    discovered_pdf_urls: Set[str] = set()
    review_records: List[Dict[str, Any]] = []

    norm_target = normalize_url(target_url)
    # Queue item tuple: (url, depth, parent_url, priority_name)
    queue: List[Tuple[str, int, Optional[str], str]] = [(norm_target, 1, None, "HIGH")]

    evaluator = GrokRelevanceEvaluator()

    async with AsyncWebCrawler() as crawler:
        while queue:
            # Sort queue by priority (HIGH -> MEDIUM -> LOW) then pop head
            priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "SKIP": 3}
            queue.sort(key=lambda item: (item[1], priority_order.get(item[3], 2)))

            raw_url, current_depth, parent_url, priority = queue.pop(0)
            current_url = normalize_url(raw_url)

            if current_url in visited_urls:
                continue

            visited_urls.add(current_url)

            if is_pdf_url(current_url):
                discovered_pdf_urls.add(current_url)
                continue

            try:
                result = await crawler.arun(url=current_url, config=crawl_config)
                
                # If a strict selector wait timed out, retry immediately with relaxed config without wait_for
                if not result.success and crawl_settings.get("wait_for_selector"):
                    err = result.error_message or ""
                    if "Wait condition failed" in err or "Timeout" in err:
                        logger.warning(f"Wait condition failed for {current_url}. Retrying without wait_for selector...")
                        relaxed_settings = dict(crawl_settings)
                        relaxed_settings.pop("wait_for_selector", None)
                        relaxed_settings.pop("target_css_selector", None)
                        result = await crawler.arun(url=current_url, config=_build_crawler_config(relaxed_settings))

                if not result.success:
                    err = result.error_message or ""
                    if "Download is starting" in err or "download" in err.lower():
                        logger.info(f"URL {current_url} triggered a download instead of HTML navigation. Diverting to PDF processor.")
                        discovered_pdf_urls.add(current_url)
                        continue

                    logger.warning(f"Failed to crawl URL: {current_url}. Error: {result.error_message}")
                    if current_url == norm_target:
                        return [], set(), [], False, f"Failed to fetch seed URL: {result.error_message}"
                    continue

                raw_md = result.markdown or ""
                clean_body = format_to_clean_markdown(title=source_name, url=current_url, raw_markdown=raw_md)

                # Classify page structure
                page_class = classify_page(current_url, source_name, clean_body)

                # Relevance evaluation check
                cand_record = CandidateURLRecord(
                    url=current_url,
                    source_id=source_id,
                    depth=current_depth,
                    parent_url=parent_url,
                    title=source_name,
                    page_classification=page_class
                )
                page_data = {"content": clean_body, "title": source_name, "content_preview": clean_body[:500]}
                eval_res = await evaluator.evaluate(cand_record, page_data)

                # Extract discovered links (internal + external allowed domains)
                raw_links = (result.links.get("internal", []) + result.links.get("external", [])) if result.links else []
                extracted_links = [link.get("href") for link in raw_links]
                html_links, pdf_links = classify_links(extracted_links, current_url, allowed_domains)
                discovered_pdf_urls.update(pdf_links)

                # Handle Discovery or Source index pages (traversal index)
                if page_class in (PageClassificationEnum.REGULATORY_DISCOVERY, PageClassificationEnum.REGULATORY_SOURCE) or current_url == norm_target:
                    logger.info(f"Page {current_url} is a structural {page_class.value}. Expanding regulatory child links (count={len(html_links)}).")
                    if follow_links and (current_depth < max_depth):
                        for sub_url in html_links:
                            norm_sub = normalize_url(sub_url)
                            if norm_sub not in visited_urls:
                                sub_prio = calculate_crawl_priority(norm_sub, "", page_class, allowed_domains)
                                if sub_prio != CrawlPriorityEnum.SKIP:
                                    queue.append((norm_sub, current_depth + 1, current_url, sub_prio.value))
                    continue

                # Process according to relevance verdict for non-index text pages
                if eval_res.classification == RelevanceClassificationEnum.RELEVANT:
                    # Build structured .txt representation
                    structured_txt = format_to_structured_txt(
                        source_id=source_id,
                        jurisdiction=jurisdiction_str,
                        url=current_url,
                        page_title=source_name,
                        crawled_at=crawled_at,
                        clean_text=clean_body,
                        discovered_links=sorted(list(html_links | pdf_links)),
                        parent_url=parent_url,
                        status="RELEVANT"
                    )

                    scraped_documents.append({
                        "url": current_url,
                        "depth": current_depth,
                        "type": "html",
                        "content": structured_txt,
                        "content_hash": calculate_sha256(structured_txt)
                    })

                    # Expand links for RELEVANT pages
                    if follow_links and (current_depth < max_depth):
                        for sub_url in html_links:
                            norm_sub = normalize_url(sub_url)
                            if norm_sub not in visited_urls:
                                sub_prio = calculate_crawl_priority(norm_sub, "", page_class, allowed_domains)
                                if sub_prio != CrawlPriorityEnum.SKIP:
                                    queue.append((norm_sub, current_depth + 1, current_url, sub_prio.value))

                elif eval_res.classification in (RelevanceClassificationEnum.NOT_RELEVANT, RelevanceClassificationEnum.UNCERTAIN):
                    # NOT_RELEVANT or UNCERTAIN: STOP expanding child links for this branch!
                    logger.info(f"Page {current_url} classified as {eval_res.classification.value}. Stopping link expansion for this branch.")
                    review_records.append({
                        "url": current_url,
                        "classification": eval_res.classification.value,
                        "reason": eval_res.reason
                    })
                else:
                    # EVALUATION_ERROR: Do NOT treat as NOT_RELEVANT or UNCERTAIN
                    logger.warning(f"Grok API Evaluation error for {current_url}: {eval_res.reason}. Stopping branch expansion without marking as NOT_RELEVANT or UNCERTAIN.")
                    review_records.append({
                        "url": current_url,
                        "classification": "EVALUATION_ERROR",
                        "reason": eval_res.reason
                    })

            except Exception as e:
                logger.error(f"Error crawling {current_url}: {str(e)}")
                if current_url == norm_target:
                    return [], set(), [], False, str(e)
                continue

    return scraped_documents, discovered_pdf_urls, review_records, True, ""


async def _process_discovered_pdfs(
    pdf_urls: Set[str], 
    request_timeout: int,
    source_id: str,
    jurisdiction_str: str,
    crawled_at: str
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Batch processes discovered PDF URLs, evaluates text relevance using Grok/Evaluator,
    and returns (relevant_pdf_documents, pdf_review_records).
    """
    if not pdf_urls:
        return [], []

    logger.info(f"Extracting & evaluating {len(pdf_urls)} discovered PDFs")
    pdf_tasks = [download_and_extract_pdf(url, timeout=request_timeout) for url in list(pdf_urls)[:10]]
    pdf_results = await asyncio.gather(*pdf_tasks)

    evaluator = GrokRelevanceEvaluator()
    pdf_documents = []
    pdf_review_records = []

    for pdf_res in pdf_results:
        if pdf_res["success"] and pdf_res["text"]:
            pdf_url = normalize_url(pdf_res["url"])
            title = f"PDF Document: {pdf_url}"

            cand_record = CandidateURLRecord(
                url=pdf_url,
                source_id=source_id,
                depth=1,
                title=title,
                content_type="pdf"
            )
            page_data = {"content": pdf_res["text"], "title": title, "content_preview": pdf_res["text"][:500]}
            eval_res = await evaluator.evaluate(cand_record, page_data)

            if eval_res.classification == RelevanceClassificationEnum.RELEVANT:
                structured_txt = format_to_structured_txt(
                    source_id=source_id,
                    jurisdiction=jurisdiction_str,
                    url=pdf_url,
                    page_title=title,
                    crawled_at=crawled_at,
                    clean_text=pdf_res["text"]
                )
                pdf_documents.append({
                    "url": pdf_url,
                    "depth": 1,
                    "type": "pdf",
                    "page_count": pdf_res["page_count"],
                    "content": structured_txt,
                    "content_hash": calculate_sha256(structured_txt)
                })
            elif eval_res.classification in (RelevanceClassificationEnum.NOT_RELEVANT, RelevanceClassificationEnum.UNCERTAIN):
                logger.info(f"PDF {pdf_url} classified as {eval_res.classification.value}. Adding to review records.")
                pdf_review_records.append({
                    "url": pdf_url,
                    "classification": eval_res.classification.value,
                    "reason": eval_res.reason
                })

    return pdf_documents, pdf_review_records


def _build_response_payload(
    source_id: str,
    target_url: str,
    scraped_documents: List[Dict[str, Any]],
    review_records: List[Dict[str, Any]],
    source_config: Dict[str, Any],
    crawled_at: str
) -> Dict[str, Any]:
    """Constructs final payload, calculates combined hash, and persists to disk."""
    all_content_str = "\n\n".join([doc.get("content", "") for doc in scraped_documents if doc.get("content")])
    combined_hash = calculate_sha256(all_content_str)

    output_payload = {
        "success": True,
        "source_id": source_id,
        "seed_url": target_url,
        "total_documents_scraped": len(scraped_documents),
        "total_html_pages": sum(1 for d in scraped_documents if d["type"] == "html"),
        "total_pdfs_parsed": sum(1 for d in scraped_documents if d["type"] == "pdf"),
        "combined_content_hash": combined_hash,
        "documents": scraped_documents,
        "review_records": review_records,
        "metadata": {
            "source_id": source_id,
            "jurisdiction": source_config.get("jurisdiction"),
            "source": source_config.get("source", {}),
            "status": source_config.get("status")
        },
        "timestamps": {
            "last_crawled_at": crawled_at,
            "last_success_at": crawled_at
        }
    }

    # Save to storage/extracted_content/<source_id>/<timestamp>/
    saved_folder = save_crawl_results(output_payload, source_id)
    output_payload["saved_directory"] = saved_folder

    return output_payload


# MAIN ORCHESTRATOR
async def execute_source_crawl(source_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Top-level Orchestrator for executing source crawls.
    Delegates to modular functions for easy debugging and testing.
    """
    source_id = source_config.get("source_id", "unknown_source")
    source_info = source_config.get("source", {})
    crawl_settings = source_config.get("crawl", {})
    allowed_domains = source_info.get("allowed_domains", [])

    jurisdiction_data = source_config.get("jurisdiction", {})
    jurisdiction_str = jurisdiction_data.get("state") if isinstance(jurisdiction_data, dict) else str(jurisdiction_data)

    max_depth = int(crawl_settings.get("max_depth", 1))
    follow_links = bool(crawl_settings.get("follow_links", True))
    include_pdf = bool(crawl_settings.get("include_pdf", True))
    request_timeout = int(crawl_settings.get("request_timeout_seconds", 30))

    seed_urls: List[str] = source_info.get("seed_urls", [])
    raw_target_url = seed_urls[0] if seed_urls else source_info.get("base_url")

    if not raw_target_url:
        logger.error(f"No valid seed or base URL found for source '{source_id}'")
        raise ValueError(f"No valid seed or base URL found for source '{source_id}'")

    target_url = normalize_url(raw_target_url)
    crawled_at = datetime.now(timezone.utc).isoformat()
    logger.info(f"Starting crawl for {source_id} at {target_url} (Max Depth: {max_depth})")

    # Step 1: Build Crawl Config
    crawl_config = _build_crawler_config(crawl_settings)

    # Step 2: Crawl HTML pages (expanding only RELEVANT branches)
    html_docs, pdf_urls, review_records, success, error_msg = await _run_in_proactor_if_needed(
        _crawl_html_pages,
        target_url=target_url,
        max_depth=max_depth,
        follow_links=follow_links,
        allowed_domains=allowed_domains,
        source_name=source_info.get("name", "Regulatory Document"),
        source_id=source_id,
        jurisdiction_str=jurisdiction_str,
        crawled_at=crawled_at,
        crawl_config=crawl_config,
        crawl_settings=crawl_settings
    )

    if not success:
        return {
            "success": False,
            "error": error_msg,
            "source_id": source_id,
            "seed_url": target_url,
            "total_documents_scraped": 0,
            "total_html_pages": 0,
            "total_pdfs_parsed": 0,
            "review_records": [],
            "saved_directory": "",
            "timestamps": {"last_crawled_at": crawled_at}
        }

    # Step 3: Process & evaluate relevance of discovered PDFs
    pdf_docs = []
    if include_pdf and pdf_urls:
        pdf_docs, pdf_review_records = await _process_discovered_pdfs(
            pdf_urls=pdf_urls,
            request_timeout=request_timeout,
            source_id=source_id,
            jurisdiction_str=jurisdiction_str,
            crawled_at=crawled_at
        )
        review_records.extend(pdf_review_records)

    # Step 4: Combine all documents & build final output
    all_documents = html_docs + pdf_docs
    return _build_response_payload(
        source_id=source_id,
        target_url=target_url,
        scraped_documents=all_documents,
        review_records=review_records,
        source_config=source_config,
        crawled_at=crawled_at
    )
