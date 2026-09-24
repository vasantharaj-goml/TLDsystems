from fastapi import APIRouter, HTTPException, status
from app.schemas.discovery import (
    DiscoveryRunRequest,
    DiscoveryRunResponse,
    ApprovalRequest,
    ApprovalResponse
)
from app.services.discovery_engine import CandidateDiscoveryEngine
from app.services.approval_service import ApprovalService
from app.utils.logger import logger

router = APIRouter()
discovery_engine = CandidateDiscoveryEngine()
approval_service = ApprovalService()


@router.post(
    "/run",
    response_model=DiscoveryRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute Candidate Discovery & Grok Relevance Triage",
    description="Traverses government website links with Crawl4AI, fetches content with Agent Reach capability, evaluates relevance with Grok, and outputs categorized candidate sources."
)
async def run_discovery(request: DiscoveryRunRequest):
    try:
        logger.info(f"Received discovery request for source_id: {request.source_id}")
        return await discovery_engine.run_discovery(request)
    except ValueError as e:
        logger.error(f"Discovery lookup error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Discovery execution error for {request.source_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Candidate discovery failed: {str(e)}"
        )


@router.post(
    "/approve",
    response_model=ApprovalResponse,
    status_code=status.HTTP_200_OK,
    summary="TLD Approve Candidate URLs & Handoff to Production Crawler",
    description="Manually validates relevant candidate URLs and transitions state to APPROVED. Optionally triggers existing production crawler."
)
async def approve_candidates(request: ApprovalRequest):
    try:
        logger.info(f"Received TLD approval request for source_id: {request.source_id}")
        return await approval_service.approve_candidates(request)
    except ValueError as e:
        logger.error(f"Approval lookup error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Approval workflow error for {request.source_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"TLD approval failed: {str(e)}"
        )
