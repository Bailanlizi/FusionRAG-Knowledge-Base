from fastapi import APIRouter, File, Query, UploadFile

from src.api.schemas import (
    ChunkItem,
    DocumentItem,
    DocumentListResponse,
    UploadResponse,
)
from src.api.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])
svc = DocumentService()


@router.get("", response_model=DocumentListResponse)
def list_documents(
    q: str | None = None,
    source_type: str | None = None,
    sort: str = Query("updated_at"),
    order: str = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> DocumentListResponse:
    return svc.list_documents(q, source_type, sort, order, page, page_size)


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)) -> UploadResponse:
    return await svc.upload(file)


@router.get("/{doc_id}", response_model=DocumentItem)
def get_document(doc_id: str) -> DocumentItem:
    return svc.get_document(doc_id)


@router.get("/{doc_id}/chunks", response_model=list[ChunkItem])
def list_chunks(doc_id: str) -> list[ChunkItem]:
    return svc.list_chunks(doc_id)


@router.delete("/{doc_id}", status_code=204)
def delete_document(doc_id: str) -> None:
    svc.delete_document(doc_id)
