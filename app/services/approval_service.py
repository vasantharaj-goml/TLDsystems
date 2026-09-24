import json
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from app.config import settings
from app.services.config_loader import get_source_by_id
from app.services.crawler_engine import execute_source_crawl
from app.schemas.discovery import ApprovalRequest, ApprovalResponse, CandidateStatusEnum
from app.utils.logger import logger


class ApprovalService:
    """
    Manages TLD Source Approval Boundary & Handoff to Production Crawler.
    
    Strict Enforcement:
    - Grok/LLM evaluates candidate relevance ONLY.
    - Candidate URLs can NEVER be auto-approved by AI.
    - TLD Approval is a separate human/administrative action.
    - Only APPROVED URLs are submitted to the production crawler.
    """

    async def approve_candidates(self, request: ApprovalRequest) -> ApprovalResponse:
        source_id = request.source_id
        target_urls = set(request.urls)

        # 1. Locate candidate records from latest discovery run
        candidates_dir = settings.DISCOVERY_STORAGE_DIR / source_id
        if not candidates_dir.exists():
            raise ValueError(f"No discovery runs found for source_id '{source_id}'")

        # Find latest timestamp run folder
        run_dirs = sorted([d for d in candidates_dir.iterdir() if d.is_dir()], reverse=True)
        if not run_dirs:
            raise ValueError(f"No valid discovery run directories found under {candidates_dir}")

        latest_run_dir = run_dirs[0]
        candidates_file = latest_run_dir / "candidates.json"

        if not candidates_file.exists():
            raise ValueError(f"Candidates file missing at {candidates_file}")

        with open(candidates_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        raw_candidates = data.get("candidates", [])

        approved_urls: List[str] = []
        rejected_urls: List[str] = []
        approved_records: List[Dict[str, Any]] = []

        for cand in raw_candidates:
            cand_url = cand.get("url")
            if cand_url in target_urls:
                cand["status"] = CandidateStatusEnum.APPROVED.value
                approved_urls.append(cand_url)
                approved_records.append(cand)
            else:
                rejected_urls.append(cand_url)

        if not approved_urls:
            logger.warning(f"None of the requested URLs matched discovered candidates for source {source_id}")

        # 2. Persist approved sources into storage/approved_sources/<source_id>/approved.json
        self._save_approved_sources(source_id, approved_records)

        production_results: Optional[Dict[str, Any]] = None

        # 3. Optional Production Crawler Handoff
        if request.run_production_crawl and approved_urls:
            logger.info(f"Handing off {len(approved_urls)} approved URLs to existing production crawler for {source_id}")
            
            # Load original source config and override seed_urls with approved URLs
            source_config = get_source_by_id(source_id)
            prod_config = dict(source_config)
            prod_config["source"] = dict(prod_config.get("source", {}))
            prod_config["source"]["seed_urls"] = approved_urls
            
            # Restrict depth to 1 for precise target extraction on approved pages
            prod_config["crawl"] = dict(prod_config.get("crawl", {}))
            prod_config["crawl"]["max_depth"] = 1

            production_results = await execute_source_crawl(prod_config)

        return ApprovalResponse(
            source_id=source_id,
            approved_urls=approved_urls,
            rejected_urls=rejected_urls,
            production_crawl_results=production_results
        )

    def _save_approved_sources(self, source_id: str, approved_records: List[Dict[str, Any]]) -> Path:
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        target_dir = settings.APPROVED_STORAGE_DIR / source_id / timestamp_str
        target_dir.mkdir(parents=True, exist_ok=True)

        output_path = target_dir / "approved.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({
                "source_id": source_id,
                "approved_at": timestamp_str,
                "total_approved": len(approved_records),
                "approved_candidates": approved_records
            }, f, indent=2)

        logger.info(f"Saved {len(approved_records)} approved sources to {output_path}")
        return output_path
