from fastapi import APIRouter

from src.api.schemas import KbStatsResponse
from src.api.services.document_service import DocumentService

router = APIRouter(prefix="/kb", tags=["kb"])
svc = DocumentService()


@router.get("/stats", response_model=KbStatsResponse)
def kb_stats() -> KbStatsResponse:
    return svc.get_stats()
