import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Set, Tuple, Optional
from pathlib import Path

from app.config import settings
from app.services.config_loader import get_source_by_id
from app.services.content_cleaner import classify_links, is_pdf_url, is_binary_download, is_allowed_domain
from app.services.agent_reach_reader import AgentReachReader
from app.services.relevance_evaluator import RelevanceEvaluator
from app.services.grok_relevance_evaluator import GrokRelevanceEvaluator
from app.schemas.discovery import (
    CandidateURLRecord,
    EvaluatedCandidateRecord,
    RelevanceClassificationEnum,
    CandidateStatusEnum,
    DiscoveryRunRequest,
    DiscoveryRunResponse,
    GrokEvaluationResponse
)
from app.utils.logger import logger
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode


# Deterministic pre-filter signal keywords
POSITIVE_SIGNALS = [
    "medical", "medical-record", "medical-records", "patient", "patient-record",
    "health-information", "health-information-privacy", "health-information-security",
    "protected-health-information", "confidentiality", "medical-privacy", "health-privacy",
    "record-disclosure", "patient-information", "hipaa", "privacy-rights"
]

NEGATIVE_SIGNALS = [
    "restaurant", "vehicle", "tourism", "tax", "building", "employment",
    "procurement", "road", "transportation", "parking", "environmental-permits"
]


def deterministic_prefilter(url: str, title: Optional[str] = None) -> Optional[GrokEvaluationResponse]:
    """
    Lightweight deterministic pre-filtering optimization.
    Returns GrokEvaluationResponse if candidate is clearly irrelevant based on domain signals,
    or None if candidate should be evaluated by Agent Reach + Grok.
    """
    text_to_check = f"{url.lower()} {(title or '').lower()}"

    has_positive = any(sig in text_to_check for sig in POSITIVE_SIGNALS)
    has_negative = any(sig in text_to_check for sig in NEGATIVE_SIGNALS)

    if has_negative and not has_positive:
        return GrokEvaluationResponse(
            classification=RelevanceClassificationEnum.NOT_RELEVANT,
            confidence=0.95,
            reason="Pre-filtered: candidate URL/title contains clear negative topic indicator.",
            matched_topics=[]
        )
    return None


class CandidateDiscoveryEngine:
    """
    Orchestrates Candidate URL Discovery using Crawl4AI,
    Agent Reach content fetching, and Grok relevance classification.
    """

    def __init__(
        self,
        reader: Optional[AgentReachReader] = None,
        evaluator: Optional[RelevanceEvaluator] = None
    ):
        self.reader = reader or AgentReachReader()
        self.evaluator = evaluator or GrokRelevanceEvaluator()

    async def run_discovery(self, request: DiscoveryRunRequest) -> DiscoveryRunResponse:
        source_id = request.source_id
        source_config = get_source_by_id(source_id)
        
        source_info = source_config.get("source", {})
        crawl_settings = source_config.get("crawl", {})
        allowed_domains = source_info.get("allowed_domains", [])
        jurisdiction = source_config.get("jurisdiction", {})

        max_depth = request.override_max_depth or int(crawl_settings.get("max_depth", 2))
        seed_urls = source_info.get("seed_urls", [])
        target_url = seed_urls[0] if seed_urls else source_info.get("base_url")

        if not target_url:
            raise ValueError(f"No valid seed or base URL found for source '{source_id}'")

        logger.info(f"Starting candidate discovery for '{source_id}' at {target_url} (max_depth={max_depth})")

        # Step 1: Discover URLs using Crawl4AI
        discovered_candidates = await self._discover_candidates_with_crawl4ai(
            target_url=target_url,
            max_depth=max_depth,
            allowed_domains=allowed_domains,
            source_id=source_id,
            jurisdiction=jurisdiction
        )

        evaluated_records: List[EvaluatedCandidateRecord] = []
        failures: List[Dict[str, Any]] = []

        relevant_count = 0
        not_relevant_count = 0
        uncertain_count = 0

        # Step 2: Process candidate list with Agent Reach & Grok
        for cand in discovered_candidates:
            try:
                # 2a. Pre-filtering check
                prefilter_res = None if request.bypass_prefilter else deterministic_prefilter(cand.url, cand.title)

                if prefilter_res:
                    eval_res = prefilter_res
                    page_data = {"content": "", "title": cand.title, "content_preview": ""}
                else:
                    # 2b. Agent Reach reads content
                    page_data = await self.reader.read_candidate_content(cand.url, cand.content_type)
                    if not page_data.get("success"):
                        logger.warning(f"Failed to read content for candidate {cand.url}: {page_data.get('error')}")
                        failures.append({"url": cand.url, "error": page_data.get("error")})

                    # Update title if read succeeded
                    if page_data.get("title") and not cand.title:
                        cand.title = page_data["title"]

                    # 2c. Grok evaluates relevance
                    eval_res = await self.evaluator.evaluate(cand, page_data)

                # Determine status
                if eval_res.classification == RelevanceClassificationEnum.RELEVANT:
                    status = CandidateStatusEnum.RELEVANT_CANDIDATE
                    relevant_count += 1
                elif eval_res.classification == RelevanceClassificationEnum.NOT_RELEVANT:
                    status = CandidateStatusEnum.NOT_RELEVANT
                    not_relevant_count += 1
                elif eval_res.classification == RelevanceClassificationEnum.UNCERTAIN:
                    status = CandidateStatusEnum.UNCERTAIN
                    uncertain_count += 1
                else:
                    status = CandidateStatusEnum.EVALUATION_ERROR
                    failures.append({"url": cand.url, "error": eval_res.reason})


                evaluated_record = EvaluatedCandidateRecord(
                    url=cand.url,
                    source_id=cand.source_id,
                    jurisdiction=cand.jurisdiction,
                    depth=cand.depth,
                    parent_url=cand.parent_url,
                    title=cand.title or page_data.get("title") or cand.url,
                    content_type=cand.content_type,
                    content_preview=page_data.get("content_preview") or (page_data.get("content", "")[:300]),
                    discovery_method=cand.discovery_method,
                    status=status,
                    classification=eval_res.classification,
                    confidence=eval_res.confidence,
                    reason=eval_res.reason,
                    matched_topics=eval_res.matched_topics
                )
                evaluated_records.append(evaluated_record)

            except Exception as e:
                logger.error(f"Error evaluating candidate candidate {cand.url}: {str(e)}")
                failures.append({"url": cand.url, "error": str(e)})

        # Step 3: Save results to disk
        self._save_discovery_summary(source_id, evaluated_records, failures)

        return DiscoveryRunResponse(
            source_id=source_id,
            status="completed",
            discovered_count=len(evaluated_records),
            relevant_count=relevant_count,
            not_relevant_count=not_relevant_count,
            uncertain_count=uncertain_count,
            candidates=evaluated_records,
            failures=failures
        )

    async def _discover_candidates_with_crawl4ai(
        self,
        target_url: str,
        max_depth: int,
        allowed_domains: List[str],
        source_id: str,
        jurisdiction: Any
    ) -> List[CandidateURLRecord]:
        """
        Uses Crawl4AI link extraction to gather candidate URLs up to max_depth.
        """
        candidates: List[CandidateURLRecord] = []
        visited_urls: Set[str] = set()
        queue: List[Tuple[str, int, Optional[str]]] = [(target_url, 1, None)]

        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            page_timeout=30000,
            wait_until="domcontentloaded"
        )

        async with AsyncWebCrawler() as crawler:
            while queue:
                curr_url, depth, parent_url = queue.pop(0)

                if curr_url in visited_urls:
                    continue
                visited_urls.add(curr_url)

                content_type = "pdf" if is_pdf_url(curr_url) else "html"

                cand_record = CandidateURLRecord(
                    url=curr_url,
                    source_id=source_id,
                    jurisdiction=jurisdiction,
                    depth=depth,
                    parent_url=parent_url,
                    content_type=content_type,
                    discovery_method="seed_url" if depth == 1 else "internal_link"
                )
                candidates.append(cand_record)

                if content_type == "pdf" or depth >= max_depth:
                    continue

                try:
                    result = await crawler.arun(url=curr_url, config=run_config)
                    if result.success and result.links:
                        raw_links = result.links.get("internal", []) + result.links.get("external", [])
                        extracted_links = [link.get("href") for link in raw_links]
                        html_links, pdf_links = classify_links(extracted_links, curr_url, allowed_domains)



                        for sub_url in html_links:
                            if sub_url not in visited_urls:
                                queue.append((sub_url, depth + 1, curr_url))

                        for pdf_url in pdf_links:
                            if pdf_url not in visited_urls:
                                visited_urls.add(pdf_url)
                                candidates.append(CandidateURLRecord(
                                    url=pdf_url,
                                    source_id=source_id,
                                    jurisdiction=jurisdiction,
                                    depth=depth + 1,
                                    parent_url=curr_url,
                                    content_type="pdf",
                                    discovery_method="internal_link"
                                ))
                except Exception as e:
                    logger.warning(f"Discovery crawl failed for sub-link {curr_url}: {str(e)}")

        return candidates

    def _save_discovery_summary(
        self,
        source_id: str,
        candidates: List[EvaluatedCandidateRecord],
        failures: List[Dict[str, Any]]
    ) -> Path:
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        target_dir = settings.DISCOVERY_STORAGE_DIR / source_id / timestamp_str
        target_dir.mkdir(parents=True, exist_ok=True)

        file_path = target_dir / "candidates.json"
        data = {
            "source_id": source_id,
            "timestamp": timestamp_str,
            "total_discovered": len(candidates),
            "candidates": [c.model_dump() for c in candidates],
            "failures": failures
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved candidate discovery results for {source_id} to {file_path}")
        return file_path
