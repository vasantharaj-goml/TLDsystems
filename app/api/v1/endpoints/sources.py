from fastapi import APIRouter, HTTPException, status
from typing import List, Dict, Any
from app.services.config_loader import load_all_sources, get_source_by_id

router = APIRouter()


@router.get(
    "/", 
    response_model=List[Dict[str, Any]], 
    summary="List All Registered Sources",
    description="Retrieves a list of all configured official government regulatory sources."
)
async def list_sources():
    return load_all_sources()


@router.get(
    "/{source_id}", 
    response_model=Dict[str, Any], 
    summary="Get Specific Source Metadata",
    description="Fetches source configuration JSON for a specific source ID."
)
async def get_source(source_id: str):
    try:
        return get_source_by_id(source_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=str(e)
        )