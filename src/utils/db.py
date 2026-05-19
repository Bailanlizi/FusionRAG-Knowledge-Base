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
    desc,
    func,
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
    source_type = Column(String(32), default="upload", index=True)
    page_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ConversationRow(Base):
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True)
    title = Column(String(512), default="新对话")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class MessageRow(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True)
    conversation_id = Column(String(36), nullable=False, index=True)
    role = Column(String(16), nullable=False)
    content = Column(Text, nullable=False, default="")
    sources_json = Column(Text, default="[]")
    trace_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


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
        self._ensure_source_type_column()
        self.backfill_source_types()
        logger.info("PostgreSQL tables initialized")

    def _ensure_source_type_column(self) -> None:
        from sqlalchemy import inspect, text

        insp = inspect(self.engine)
        if "documents" not in insp.get_table_names():
            return
        cols = {c["name"] for c in insp.get_columns("documents")}
        if "source_type" not in cols:
            with self.engine.begin() as conn:
                conn.execute(
                    text("ALTER TABLE documents ADD COLUMN source_type VARCHAR(32) DEFAULT 'upload'")
                )
            logger.info("Added documents.source_type column")

    def backfill_source_types(self) -> None:
        from src.utils.source_type import infer_source_type

        with self.session() as s:
            rows = s.execute(select(DocumentRow)).scalars().all()
            changed = False
            for row in rows:
                inferred = infer_source_type(row.file_path, row.doc_id)
                if row.source_type != inferred:
                    row.source_type = inferred
                    changed = True
            if changed:
                s.commit()

    def session(self) -> Session:
        return self.SessionLocal()

    def upsert_document(
        self,
        doc_id: str,
        file_path: str,
        file_name: str,
        content_hash: str,
        page_count: int = 0,
        source_type: str | None = None,
    ) -> None:
        from src.utils.source_type import infer_source_type

        st = source_type or infer_source_type(file_path, doc_id)
        with self.session() as s:
            row = s.get(DocumentRow, doc_id)
            now = datetime.now(timezone.utc)
            if row:
                row.content_hash = content_hash
                row.page_count = page_count
                row.source_type = st
                row.updated_at = now
            else:
                s.add(
                    DocumentRow(
                        doc_id=doc_id,
                        file_path=file_path,
                        file_name=file_name,
                        content_hash=content_hash,
                        source_type=st,
                        page_count=page_count,
                        created_at=now,
                        updated_at=now,
                    )
                )
            s.commit()

    def get_document(self, doc_id: str) -> DocumentRow | None:
        with self.session() as s:
            return s.get(DocumentRow, doc_id)

    def delete_document(self, doc_id: str) -> bool:
        with self.session() as s:
            row = s.get(DocumentRow, doc_id)
            if not row:
                return False
            s.delete(row)
            s.commit()
            return True

    def count_documents(self) -> int:
        with self.session() as s:
            return s.execute(select(func.count()).select_from(DocumentRow)).scalar_one()

    def count_chunks(self) -> int:
        with self.session() as s:
            return s.execute(select(func.count()).select_from(ChunkRow)).scalar_one()

    def get_last_document_update(self) -> datetime | None:
        with self.session() as s:
            return s.execute(select(func.max(DocumentRow.updated_at))).scalar_one()

    def count_chunks_by_doc(self, doc_id: str) -> int:
        with self.session() as s:
            return s.execute(
                select(func.count()).select_from(ChunkRow).where(ChunkRow.doc_id == doc_id)
            ).scalar_one()

    def list_documents(
        self,
        q: str | None = None,
        source_type: str | None = None,
        sort: str = "updated_at",
        order: str = "desc",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[DocumentRow], int]:
        with self.session() as s:
            filters = []
            if q:
                filters.append(DocumentRow.file_name.ilike(f"%{q}%"))
            if source_type:
                filters.append(DocumentRow.source_type == source_type)
            count_stmt = select(func.count()).select_from(DocumentRow)
            list_stmt = select(DocumentRow)
            for f in filters:
                count_stmt = count_stmt.where(f)
                list_stmt = list_stmt.where(f)
            total = s.execute(count_stmt).scalar_one()
            sort_col = getattr(DocumentRow, sort, DocumentRow.updated_at)
            list_stmt = list_stmt.order_by(desc(sort_col) if order == "desc" else sort_col)
            list_stmt = list_stmt.offset((page - 1) * page_size).limit(page_size)
            rows = list(s.execute(list_stmt).scalars().all())
            return rows, total

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
                s.execute(
                    select(ChunkRow)
                    .where(ChunkRow.doc_id == doc_id)
                    .order_by(ChunkRow.page, ChunkRow.chunk_id)
                ).scalars().all()
            )

    def create_conversation(self, conv_id: str, title: str) -> ConversationRow:
        now = datetime.now(timezone.utc)
        row = ConversationRow(id=conv_id, title=title, created_at=now, updated_at=now)
        with self.session() as s:
            s.add(row)
            s.commit()
            s.refresh(row)
            return row

    def list_conversations(self) -> list[ConversationRow]:
        with self.session() as s:
            return list(
                s.execute(select(ConversationRow).order_by(desc(ConversationRow.updated_at))).scalars().all()
            )

    def get_conversation(self, conv_id: str) -> ConversationRow | None:
        with self.session() as s:
            return s.get(ConversationRow, conv_id)

    def delete_conversation(self, conv_id: str) -> bool:
        with self.session() as s:
            conv = s.get(ConversationRow, conv_id)
            if not conv:
                return False
            msgs = s.execute(
                select(MessageRow).where(MessageRow.conversation_id == conv_id)
            ).scalars().all()
            for m in msgs:
                s.delete(m)
            s.delete(conv)
            s.commit()
            return True

    def touch_conversation(self, conv_id: str, title: str | None = None) -> None:
        with self.session() as s:
            conv = s.get(ConversationRow, conv_id)
            if not conv:
                return
            conv.updated_at = datetime.now(timezone.utc)
            if title:
                conv.title = title
            s.commit()

    def add_message(
        self,
        msg_id: str,
        conversation_id: str,
        role: str,
        content: str,
        sources_json: str = "[]",
        trace_json: str = "{}",
    ) -> MessageRow:
        now = datetime.now(timezone.utc)
        row = MessageRow(
            id=msg_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
            sources_json=sources_json,
            trace_json=trace_json,
            created_at=now,
        )
        with self.session() as s:
            s.add(row)
            s.commit()
            s.refresh(row)
            return row

    def list_messages(self, conversation_id: str) -> list[MessageRow]:
        with self.session() as s:
            return list(
                s.execute(
                    select(MessageRow)
                    .where(MessageRow.conversation_id == conversation_id)
                    .order_by(MessageRow.created_at)
                ).scalars().all()
            )

    def get_message(self, msg_id: str) -> MessageRow | None:
        with self.session() as s:
            return s.get(MessageRow, msg_id)

    def delete_message(self, msg_id: str) -> bool:
        with self.session() as s:
            row = s.get(MessageRow, msg_id)
            if not row:
                return False
            s.delete(row)
            s.commit()
            return True

    def delete_messages_after(self, conversation_id: str, after_created_at: datetime) -> None:
        with self.session() as s:
            rows = s.execute(
                select(MessageRow).where(
                    MessageRow.conversation_id == conversation_id,
                    MessageRow.created_at > after_created_at,
                )
            ).scalars().all()
            for row in rows:
                s.delete(row)
            s.commit()


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
