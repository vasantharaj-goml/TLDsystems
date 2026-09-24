from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class RelevanceClassificationEnum(str, Enum):
    RELEVANT = "RELEVANT"
    NOT_RELEVANT = "NOT_RELEVANT"
    UNCERTAIN = "UNCERTAIN"
    EVALUATION_ERROR = "EVALUATION_ERROR"


class CandidateStatusEnum(str, Enum):
    DISCOVERED = "DISCOVERED"
    RELEVANT_CANDIDATE = "RELEVANT_CANDIDATE"
    NOT_RELEVANT = "NOT_RELEVANT"
    UNCERTAIN = "UNCERTAIN"
    EVALUATION_ERROR = "EVALUATION_ERROR"
    APPROVED = "APPROVED"


class PageClassificationEnum(str, Enum):
    REGULATORY_SOURCE = "REGULATORY_SOURCE"
    REGULATORY_DISCOVERY = "REGULATORY_DISCOVERY"
    OFFICIAL_SUPPORTING = "OFFICIAL_SUPPORTING"
    GENERAL_INFORMATION = "GENERAL_INFORMATION"
    ACTUAL_REGULATION = "ACTUAL_REGULATION"
    ACTUAL_STATUTE = "ACTUAL_STATUTE"
    REGULATORY_DOCUMENT = "REGULATORY_DOCUMENT"
    PROPOSED_RULE = "PROPOSED_RULE"
    EMERGENCY_RULE = "EMERGENCY_RULE"
    UNKNOWN = "UNKNOWN"


class CrawlPriorityEnum(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    SKIP = "SKIP"


class CandidateURLRecord(BaseModel):
    url: str = Field(..., description="Target candidate URL")
    source_id: str = Field(..., description="Origin source repository ID")
    jurisdiction: Optional[Any] = Field(None, description="Jurisdiction details")
    depth: int = Field(1, ge=1, description="Crawl depth at which URL was discovered")
    parent_url: Optional[str] = Field(None, description="URL of referring parent page")
    title: Optional[str] = Field(None, description="Page title if available")
    content_type: str = Field("html", description="Document type: html, pdf, etc.")
    content_preview: Optional[str] = Field(None, description="Snippet or preview of candidate content")
    discovery_method: str = Field("internal_link", description="How candidate link was discovered")
    status: CandidateStatusEnum = Field(CandidateStatusEnum.DISCOVERED, description="Current workflow state")
    page_classification: PageClassificationEnum = Field(PageClassificationEnum.UNKNOWN, description="Category of target page")
    crawl_priority: CrawlPriorityEnum = Field(CrawlPriorityEnum.MEDIUM, description="Calculated crawl queue priority")


class GrokEvaluationResponse(BaseModel):
    classification: RelevanceClassificationEnum = Field(..., description="Semantic relevance verdict")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model confidence score")
    reason: str = Field(..., description="Short factual rationale without legal interpretation")
    matched_topics: List[str] = Field(default_factory=list, description="Specific TLD topics matched")
    page_classification: Optional[PageClassificationEnum] = Field(PageClassificationEnum.UNKNOWN, description="Classified page category")


class EvaluatedCandidateRecord(CandidateURLRecord):
    classification: RelevanceClassificationEnum
    confidence: float
    reason: str
    matched_topics: List[str] = Field(default_factory=list)



class DiscoveryRunRequest(BaseModel):
    source_id: str = Field(..., description="Source ID from config/source_repository.json")
    override_max_depth: Optional[int] = Field(None, ge=1, le=5, description="Optional discovery depth override")
    bypass_prefilter: bool = Field(False, description="Whether to bypass deterministic keyword pre-filtering")


class DiscoveryRunResponse(BaseModel):
    source_id: str
    status: str
    discovered_count: int
    relevant_count: int
    not_relevant_count: int
    uncertain_count: int
    candidates: List[EvaluatedCandidateRecord]
    failures: List[Dict[str, Any]] = Field(default_factory=list)


class ApprovalRequest(BaseModel):
    source_id: str = Field(..., description="Source ID of candidate URLs")
    urls: List[str] = Field(..., description="List of candidate URLs to approve")
    run_production_crawl: bool = Field(False, description="Whether to immediately launch production crawler on approved URLs")


class ApprovalResponse(BaseModel):
    source_id: str
    approved_urls: List[str]
    rejected_urls: List[str] = Field(default_factory=list)
    production_crawl_results: Optional[Dict[str, Any]] = None
