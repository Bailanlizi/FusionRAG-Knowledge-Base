"""Index chunks into Milvus and PostgreSQL."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from src.ingestion.chunker import SemanticChunker
from src.ingestion.models import ChunkRecord, ParsedDocument
from src.ingestion.parser import DocumentParser
from src.utils.api_clients import get_embedding_client
from src.utils.config import get_settings
from src.utils.db import MilvusStore, PostgresClient
from src.utils.logger import logger


class DocumentIndexer:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.parser = DocumentParser()
        self.chunker = SemanticChunker()
        self.embedder = get_embedding_client()
        self.pg = PostgresClient()
        self.milvus = MilvusStore()

    def index_file(self, file_path: str | Path, force: bool = False) -> int:
        path = Path(file_path).resolve()
        parsed = self.parser.parse(path)

        existing = self.pg.get_document_by_path(str(path))
        if existing and existing.content_hash == parsed.content_hash and not force:
            logger.info("Skipping unchanged file: %s", path.name)
            return 0

        if existing and force:
            self.pg.delete_chunks_by_doc(parsed.doc_id)
            self.milvus.delete_by_doc(parsed.doc_id)

        chunks = self.chunker.chunk(parsed)
        if not chunks:
            logger.warning("No chunks produced for %s", path.name)
            return 0

        count = self._index_chunks(parsed, chunks)
        self.pg.upsert_document(
            doc_id=parsed.doc_id,
            file_path=str(path),
            file_name=path.name,
            content_hash=parsed.content_hash,
            page_count=len(parsed.pages),
        )
        logger.info("Indexed %s: %d chunks", path.name, count)
        return count

    def index_directory(self, directory: str | Path, recursive: bool = True) -> int:
        path = Path(directory)
        pattern = "**/*" if recursive else "*"
        total = 0
        extensions = {".pdf", ".md", ".markdown", ".txt"}

        for fp in path.glob(pattern):
            if fp.is_file() and fp.suffix.lower() in extensions:
                try:
                    total += self.index_file(fp)
                except Exception as e:
                    logger.error("Failed to index %s: %s", fp, e)
        return total

    def _index_chunks(self, doc: ParsedDocument, chunks: list[ChunkRecord]) -> int:
        texts = [c.content for c in chunks]
        vectors = self.embedder.embed(texts)

        pg_rows = []
        milvus_rows = []

        for chunk, vector in zip(chunks, vectors):
            pg_rows.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "doc_id": chunk.doc_id,
                    "file_path": chunk.file_path,
                    "title_path": chunk.title_path,
                    "page": chunk.page,
                    "chunk_type": chunk.chunk_type.value,
                    "content": chunk.content,
                    "token_count": chunk.token_count,
                    "created_at": datetime.now(timezone.utc),
                }
            )
            milvus_rows.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "doc_id": chunk.doc_id,
                    "file_path": chunk.file_path,
                    "title_path": chunk.title_path,
                    "page": chunk.page,
                    "chunk_type": chunk.chunk_type.value,
                    "text": chunk.content,
                    "dense_vector": vector,
                }
            )

        self.pg.insert_chunks(pg_rows)
        self.milvus.insert(milvus_rows)
        return len(chunks)
