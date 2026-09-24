from fastapi import APIRouter, HTTPException, status
from app.schemas.crawl import CrawlRequest, CrawlResponse
from app.services.config_loader import get_source_by_id
from app.services.crawler_engine import execute_source_crawl
from app.utils.logger import logger

router = APIRouter()


@router.post(
    "/run", 
    response_model=CrawlResponse, 
    status_code=status.HTTP_200_OK,
    summary="Execute Synchronous Crawl",
    description="Crawls an official regulatory source synchronously across Scenarios 1, 2, or 3."
)
async def run_crawl(request: CrawlRequest):
    try:
        source_config = get_source_by_id(request.source_id)
    except ValueError as e:
        logger.error(f"Source lookup failed for source_id: {request.source_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    # Apply override parameters if provided in request body
    if request.override_max_depth:
        source_config["crawl"]["max_depth"] = request.override_max_depth

    logger.info(f"Received API crawl request for source_id: {request.source_id}")
    result = await execute_source_crawl(source_config)

    if not result.get("success"):
        logger.error(f"Crawl execution failed for {request.source_id}: {result.get('error')}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=result.get("error", "Crawl execution failed")
        )

    return result