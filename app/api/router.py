from fastapi import APIRouter
from app.api.v1.endpoints import crawl, sources

api_router = APIRouter()

# Register endpoint groups under v1
api_router.include_router(crawl.router, prefix="/crawl", tags=["Crawl Operations"])
api_router.include_router(sources.router, prefix="/sources", tags=["Source Registry"])