from fastapi import APIRouter
from app.api.v1.endpoints import crawl, sources, discovery

api_router = APIRouter()

# Register endpoint groups under v1
api_router.include_router(crawl.router, prefix="/crawl", tags=["Crawl Operations"])
api_router.include_router(sources.router, prefix="/sources", tags=["Source Registry"])
api_router.include_router(discovery.router, prefix="/discovery", tags=["Candidate Discovery & Triage"])