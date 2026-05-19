"""Document management for the Web API."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from src.api.schemas import (
    ChunkDetailResponse,
    ChunkItem,
    DocumentItem,
    DocumentListResponse,
    KbStatsResponse,
    UploadResponse,
)
from src.ingestion.indexer import DocumentIndexer
from src.utils.config import PROJECT_ROOT
from src.utils.db import MilvusStore, PostgresClient
from src.utils.source_type import infer_source_type

UPLOAD_DIR = PROJECT_ROOT / "data" / "documents" / "uploads"
ALLOWED_SUFFIXES = {".pdf", ".md", ".markdown", ".txt"}


class DocumentService:
    def __init__(self) -> None:
        self.pg = PostgresClient()
        self.milvus = MilvusStore()
        self.indexer = DocumentIndexer()

    def get_stats(self) -> KbStatsResponse:
        last = self.pg.get_last_document_update()
        return KbStatsResponse(
            document_count=self.pg.count_documents(),
            chunk_count=self.pg.count_chunks(),
            last_updated_at=last,
        )

    def list_documents(
        self,
        q: str | None = None,
        source_type: str | None = None,
        sort: str = "updated_at",
        order: str = "desc",
        page: int = 1,
        page_size: int = 20,
    ) -> DocumentListResponse:
        rows, total = self.pg.list_documents(q, source_type, sort, order, page, page_size)
        items = [
            DocumentItem(
                doc_id=r.doc_id,
                file_name=r.file_name,
                file_path=r.file_path,
                source_type=r.source_type or "upload",
                chunk_count=self.pg.count_chunks_by_doc(r.doc_id),
                page_count=r.page_count or 0,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in rows
        ]
        return DocumentListResponse(items=items, total=total, page=page, page_size=page_size)

    def get_document(self, doc_id: str) -> DocumentItem:
        row = self.pg.get_document(doc_id)
        if not row:
            raise HTTPException(status_code=404, detail="Document not found")
        return DocumentItem(
            doc_id=row.doc_id,
            file_name=row.file_name,
            file_path=row.file_path,
            source_type=row.source_type or "upload",
            chunk_count=self.pg.count_chunks_by_doc(row.doc_id),
            page_count=row.page_count or 0,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def list_chunks(self, doc_id: str) -> list[ChunkItem]:
        if not self.pg.get_document(doc_id):
            raise HTTPException(status_code=404, detail="Document not found")
        return [
            ChunkItem(
                chunk_id=c.chunk_id,
                doc_id=c.doc_id,
                title_path=c.title_path or "",
                page=c.page or 0,
                chunk_type=c.chunk_type or "text",
                content=c.content,
                token_count=c.token_count or 0,
            )
            for c in self.pg.list_chunks_by_doc(doc_id)
        ]

    def get_chunk(self, chunk_id: str) -> ChunkDetailResponse:
        chunk = self.pg.get_chunk(chunk_id)
        if not chunk:
            raise HTTPException(status_code=404, detail="Chunk not found")
        doc = self.pg.get_document(chunk.doc_id)
        return ChunkDetailResponse(
            chunk_id=chunk.chunk_id,
            doc_id=chunk.doc_id,
            file_name=doc.file_name if doc else Path(chunk.file_path).name,
            file_path=chunk.file_path,
            title_path=chunk.title_path or "",
            page=chunk.page or 0,
            chunk_type=chunk.chunk_type or "text",
            content=chunk.content,
        )

    async def upload(self, file: UploadFile) -> UploadResponse:
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in ALLOWED_SUFFIXES:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")

        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        safe_name = Path(file.filename or "upload").name
        dest = UPLOAD_DIR / f"{uuid.uuid4().hex}__{safe_name}"
        content = await file.read()
        dest.write_bytes(content)

        chunk_count = self.indexer.index_file(dest, force=True)
        parsed_doc = self.pg.get_document_by_path(str(dest.resolve()))
        doc_id = parsed_doc.doc_id if parsed_doc else ""

        return UploadResponse(
            doc_id=doc_id,
            file_name=safe_name,
            chunk_count=chunk_count,
            message="Indexed successfully" if chunk_count else "File unchanged or empty",
        )

    def delete_document(self, doc_id: str) -> None:
        row = self.pg.get_document(doc_id)
        if not row:
            raise HTTPException(status_code=404, detail="Document not found")

        self.pg.delete_chunks_by_doc(doc_id)
        self.milvus.delete_by_doc(doc_id)
        self.pg.delete_document(doc_id)

        path = Path(row.file_path)
        if path.exists() and "uploads" in path.as_posix():
            try:
                path.unlink()
            except OSError:
                pass
