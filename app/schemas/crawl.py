from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class CrawlRequest(BaseModel):
    source_id: str = Field(
        ..., 
        description="Unique source identifier from source_repository.json", 
        example="us-tx-health-safety-code"
    )
    override_max_depth: Optional[int] = Field(
        None, 
        ge=1, 
        le=5, 
        description="Optional override for crawl depth"
    )


class ScrapedDocumentRecord(BaseModel):
    url: str
    depth: int
    type: str  # 'html' or 'pdf'
    content: str
    content_hash: str
    page_count: Optional[int] = None


class CrawlResponse(BaseModel):
    success: bool
    source_id: str
    seed_url: str
    total_documents_scraped: int
    total_html_pages: int
    total_pdfs_parsed: int
    combined_content_hash: Optional[str] = None
    saved_directory: str
    error: Optional[str] = None
    metadata: Dict[str, Any]