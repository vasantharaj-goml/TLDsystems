import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
from app.config import settings
from app.utils.logger import logger


def sanitize_filename(name: str, max_length: int = 60) -> str:
    """Clean string for safe disk path generation."""
    cleaned = re.sub(r'[\\/*?:"<>|]', "_", name)
    cleaned = re.sub(r'\s+', "_", cleaned)
    return cleaned.strip("._")[:max_length] or "document"


def save_crawl_results(crawl_result: Dict[str, Any], source_id: str) -> str:
    """
    Saves extracted Markdown documents and metadata JSON into disk storage 
    under storage/extracted_content/<source_id>/<timestamp>/.
    """
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    target_dir = settings.STORAGE_DIR / sanitize_filename(source_id) / timestamp_str
    target_dir.mkdir(parents=True, exist_ok=True)

    # 1. Save summary metadata JSON
    summary_path = target_dir / "crawl_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "source_id": source_id,
            "seed_url": crawl_result.get("seed_url"),
            "total_documents_scraped": crawl_result.get("total_documents_scraped"),
            "total_html_pages": crawl_result.get("total_html_pages"),
            "total_pdfs_parsed": crawl_result.get("total_pdfs_parsed"),
            "combined_content_hash": crawl_result.get("combined_content_hash"),
            "metadata": crawl_result.get("metadata")
        }, f, indent=2)

    # 2. Save individual Markdown files
    for idx, doc in enumerate(crawl_result.get("documents", []), start=1):
        doc_type = doc.get("type", "doc")
        url_part = sanitize_filename(doc.get("url", "").split("//")[-1].replace("/", "_"))
        filename = f"{idx:03d}_{doc_type}_{url_part}.md"
        doc_path = target_dir / filename

        with open(doc_path, "w", encoding="utf-8") as f:
            f.write(doc.get("content") or "# No content extracted.")

    logger.info(f"Successfully saved crawl results for {source_id} to {target_dir}")
    return str(target_dir)