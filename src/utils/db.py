"""PostgreSQL and Milvus connection management."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pymilvus import (
    DataType,
    Function,
    FunctionType,
    MilvusClient,
)
from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Text,
    create_engine,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.utils.config import get_settings
from src.utils.logger import logger


class Base(DeclarativeBase):
    pass


class DocumentRow(Base):
    __tablename__ = "documents"

    doc_id = Column(String(64), primary_key=True)
    file_path = Column(String(1024), nullable=False, unique=True)
    file_name = Column(String(512), nullable=False)
    content_hash = Column(String(64), nullable=False)
    page_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ChunkRow(Base):
    __tablename__ = "chunks"

    chunk_id = Column(String(64), primary_key=True)
    doc_id = Column(String(64), nullable=False, index=True)
    file_path = Column(String(1024), nullable=False)
    title_path = Column(String(512), default="")
    page = Column(Integer, default=0)
    chunk_type = Column(String(32), default="text")
    content = Column(Text, nullable=False)
    token_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class PostgresClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.engine = create_engine(settings.env.postgres_url, pool_pre_ping=True)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def init_tables(self) -> None:
        Base.metadata.create_all(self.engine)
        logger.info("PostgreSQL tables initialized")

    def session(self) -> Session:
        return self.SessionLocal()

    def upsert_document(
        self,
        doc_id: str,
        file_path: str,
        file_name: str,
        content_hash: str,
        page_count: int = 0,
    ) -> None:
        with self.session() as s:
            row = s.get(DocumentRow, doc_id)
            now = datetime.now(timezone.utc)
            if row:
                row.content_hash = content_hash
                row.page_count = page_count
                row.updated_at = now
            else:
                s.add(
                    DocumentRow(
                        doc_id=doc_id,
                        file_path=file_path,
                        file_name=file_name,
                        content_hash=content_hash,
                        page_count=page_count,
                        created_at=now,
                        updated_at=now,
                    )
                )
            s.commit()

    def get_document_by_path(self, file_path: str) -> DocumentRow | None:
        with self.session() as s:
            return s.execute(
                select(DocumentRow).where(DocumentRow.file_path == file_path)
            ).scalar_one_or_none()

    def insert_chunks(self, chunks: list[dict[str, Any]]) -> None:
        with self.session() as s:
            for c in chunks:
                s.merge(ChunkRow(**c))
            s.commit()

    def delete_chunks_by_doc(self, doc_id: str) -> None:
        with self.session() as s:
            rows = s.execute(select(ChunkRow).where(ChunkRow.doc_id == doc_id)).scalars().all()
            for row in rows:
                s.delete(row)
            s.commit()

    def get_chunk(self, chunk_id: str) -> ChunkRow | None:
        with self.session() as s:
            return s.get(ChunkRow, chunk_id)

    def list_chunks_by_doc(self, doc_id: str) -> list[ChunkRow]:
        with self.session() as s:
            return list(
                s.execute(select(ChunkRow).where(ChunkRow.doc_id == doc_id)).scalars().all()
            )


class MilvusStore:
    """Milvus collection with dense + BM25 sparse hybrid search."""

    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.collection_name = settings.env.milvus_collection or settings.milvus.collection_name
        self.dim = settings.models.embedding_dim
        uri = f"http://{settings.env.milvus_host}:{settings.env.milvus_port}"
        self.client = MilvusClient(uri=uri)

    def collection_exists(self) -> bool:
        return self.client.has_collection(self.collection_name)

    def create_collection(self, drop_existing: bool = False) -> None:
        if drop_existing and self.collection_exists():
            self.client.drop_collection(self.collection_name)

        if self.collection_exists():
            logger.info("Milvus collection '%s' already exists", self.collection_name)
            return

        schema = self.client.create_schema(auto_id=False, enable_dynamic_field=False)
        schema.add_field("chunk_id", DataType.VARCHAR, is_primary=True, max_length=64)
        schema.add_field("doc_id", DataType.VARCHAR, max_length=64)
        schema.add_field("file_path", DataType.VARCHAR, max_length=1024)
        schema.add_field("title_path", DataType.VARCHAR, max_length=512)
        schema.add_field("page", DataType.INT64)
        schema.add_field("chunk_type", DataType.VARCHAR, max_length=32)
        schema.add_field(
            "text",
            DataType.VARCHAR,
            max_length=65535,
            enable_analyzer=True,
            enable_match=True,
        )
        schema.add_field("dense_vector", DataType.FLOAT_VECTOR, dim=self.dim)
        schema.add_field("sparse_vector", DataType.SPARSE_FLOAT_VECTOR)

        bm25_fn = Function(
            name="bm25",
            function_type=FunctionType.BM25,
            input_field_names=["text"],
            output_field_names=["sparse_vector"],
        )
        schema.add_function(bm25_fn)

        index_params = self.client.prepare_index_params()
        index_params.add_index("dense_vector", index_type="AUTOINDEX", metric_type="COSINE")
        index_params.add_index(
            "sparse_vector",
            index_type="SPARSE_INVERTED_INDEX",
            metric_type="BM25",
        )

        self.client.create_collection(
            collection_name=self.collection_name,
            schema=schema,
            index_params=index_params,
        )
        logger.info("Milvus collection '%s' created", self.collection_name)

    def insert(self, records: list[dict[str, Any]]) -> None:
        if not records:
            return
        self.client.insert(collection_name=self.collection_name, data=records)

    def delete_by_doc(self, doc_id: str) -> None:
        if not self.collection_exists():
            return
        self.client.delete(
            collection_name=self.collection_name,
            filter=f'doc_id == "{doc_id}"',
        )

    def dense_search(
        self, query_vector: list[float], top_k: int, doc_ids: list[str] | None = None
    ) -> list[dict[str, Any]]:
        filter_expr = None
        if doc_ids:
            ids_str = ", ".join(f'"{d}"' for d in doc_ids)
            filter_expr = f"doc_id in [{ids_str}]"

        results = self.client.search(
            collection_name=self.collection_name,
            data=[query_vector],
            anns_field="dense_vector",
            limit=top_k,
            output_fields=["chunk_id", "doc_id", "file_path", "title_path", "page", "chunk_type", "text"],
            filter=filter_expr,
        )
        return self._parse_results(results)

    def sparse_search(
        self, query_text: str, top_k: int, doc_ids: list[str] | None = None
    ) -> list[dict[str, Any]]:
        filter_expr = None
        if doc_ids:
            ids_str = ", ".join(f'"{d}"' for d in doc_ids)
            filter_expr = f"doc_id in [{ids_str}]"

        results = self.client.search(
            collection_name=self.collection_name,
            data=[query_text],
            anns_field="sparse_vector",
            limit=top_k,
            output_fields=["chunk_id", "doc_id", "file_path", "title_path", "page", "chunk_type", "text"],
            filter=filter_expr,
            search_params={"metric_type": "BM25"},
        )
        return self._parse_results(results)

    def hybrid_search(
        self,
        query_vector: list[float],
        query_text: str,
        top_k: int,
    ) -> list[dict[str, Any]]:
        """Run dense + sparse and merge via simple union (RRF done upstream)."""
        dense = self.dense_search(query_vector, top_k)
        sparse = self.sparse_search(query_text, top_k)
        return dense + sparse

    def count(self) -> int:
        if not self.collection_exists():
            return 0
        stats = self.client.get_collection_stats(self.collection_name)
        return int(stats.get("row_count", 0))

    @staticmethod
    def _parse_results(results: list) -> list[dict[str, Any]]:
        parsed = []
        for hits in results:
            for hit in hits:
                entity = hit.get("entity", hit)
                parsed.append(
                    {
                        "chunk_id": entity.get("chunk_id", hit.get("id")),
                        "doc_id": entity.get("doc_id", ""),
                        "file_path": entity.get("file_path", ""),
                        "title_path": entity.get("title_path", ""),
                        "page": entity.get("page", 0),
                        "chunk_type": entity.get("chunk_type", "text"),
                        "text": entity.get("text", ""),
                        "score": hit.get("distance", hit.get("score", 0.0)),
                    }
                )
        return parsed
