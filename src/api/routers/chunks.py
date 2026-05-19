from fastapi import APIRouter

from src.api.schemas import ChunkDetailResponse
from src.api.services.document_service import DocumentService

router = APIRouter(prefix="/chunks", tags=["chunks"])
svc = DocumentService()


@router.get("/{chunk_id}", response_model=ChunkDetailResponse)
def get_chunk(chunk_id: str) -> ChunkDetailResponse:
    return svc.get_chunk(chunk_id)
