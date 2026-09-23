from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl


class JurisdictionSchema(BaseModel):
    country: str = Field(default="US", example="US")
    state: str = Field(..., example="Texas")
    code: str = Field(..., example="US-TX")
    level: str = Field(..., example="state")


class SourceDetailsSchema(BaseModel):
    name: str = Field(..., example="Texas Constitution and Statutes")
    type: str = Field(..., example="state_statutes")
    authority: str = Field(..., example="Texas Legislature")
    official: bool = Field(default=True)
    relevance: str = Field(..., example="Official Texas statutory source for healthcare privacy laws.")
    base_url: str = Field(..., example="https://statutes.capitol.texas.gov/")
    seed_urls: List[str] = Field(..., example=["https://statutes.capitol.texas.gov/?tab=1&code=HS&chapter=HS.181&artSec="])
    allowed_domains: List[str] = Field(..., example=["statutes.capitol.texas.gov"])


class CrawlConfigSchema(BaseModel):
    enabled: bool = Field(default=True)
    engine: str = Field(default="crawl4ai")
    max_depth: int = Field(default=1, ge=1, le=5)
    follow_links: bool = Field(default=True)
    include_pdf: bool = Field(default=True)
    allowed_content_types: List[str] = Field(default=["text/html", "application/pdf"])
    respect_robots_txt: bool = Field(default=True)
    request_timeout_seconds: int = Field(default=30)
    max_retries: int = Field(default=3)
    wait_for_selector: Optional[str] = Field(default=None, example="#ContentPlaceHolder1_lblContent")
    target_css_selector: Optional[str] = Field(default=None, example=".statute-content-container")


class MonitoringSchema(BaseModel):
    frequency: str = Field(default="monthly")
    change_detection: bool = Field(default=True)
    hash_algorithm: str = Field(default="sha256")


class StatusSchema(BaseModel):
    active: bool = Field(default=True)
    accessibility: str = Field(default="accessible")
    validation: str = Field(default="verified")


class TimestampsSchema(BaseModel):
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    last_crawled_at: Optional[str] = None
    last_success_at: Optional[str] = None


class SourceRepositoryRecord(BaseModel):
    source_id: str = Field(..., example="us-tx-health-safety-code")
    jurisdiction: JurisdictionSchema
    source: SourceDetailsSchema
    crawl: CrawlConfigSchema
    monitoring: MonitoringSchema
    status: StatusSchema
    timestamps: TimestampsSchema