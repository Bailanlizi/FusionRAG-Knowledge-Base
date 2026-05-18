"""Structured semantic chunking with optional LLM merge."""

from __future__ import annotations

import hashlib
import re
import uuid

import tiktoken

from src.ingestion.models import ChunkRecord, ChunkType, ParsedDocument
from src.utils.api_clients import get_llm_client, parse_json_from_llm
from src.utils.config import get_settings
from src.utils.logger import logger

_enc = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(_enc.encode(text))


def _split_by_headings(markdown: str) -> list[tuple[str, str]]:
    """Split markdown into (title_path, content) sections."""
    sections: list[tuple[str, str]] = []
    current_title = ""
    current_lines: list[str] = []

    for line in markdown.split("\n"):
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            if current_lines:
                sections.append((current_title, "\n".join(current_lines).strip()))
            level = len(heading.group(1))
            title = heading.group(2).strip()
            current_title = title if level <= 2 else f"{current_title} > {title}" if current_title else title
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_title, "\n".join(current_lines).strip()))

    if not sections:
        sections.append(("", markdown))
    return sections


def _split_paragraphs(text: str, max_tokens: int) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        candidate = f"{current}\n\n{para}".strip() if current else para
        if count_tokens(candidate) <= max_tokens:
            current = candidate
        else:
            if current:
                chunks.append(current)
            if count_tokens(para) > max_tokens:
                sentences = re.split(r"(?<=[。！？.!?])\s*", para)
                buf = ""
                for sent in sentences:
                    if count_tokens(buf + sent) <= max_tokens:
                        buf += sent
                    else:
                        if buf:
                            chunks.append(buf)
                        buf = sent
                if buf:
                    chunks.append(buf)
                current = ""
            else:
                current = para

    if current:
        chunks.append(current)
    return chunks


class SemanticChunker:
    def __init__(self) -> None:
        self.settings = get_settings()

    def chunk(self, doc: ParsedDocument) -> list[ChunkRecord]:
        records: list[ChunkRecord] = []
        target_min = self.settings.chunking.target_min
        target_max = self.settings.chunking.target_max

        for page in doc.pages:
            sections = _split_by_headings(page.markdown)
            for title_path, content in sections:
                if not content.strip():
                    continue
                parts = _split_paragraphs(content, target_max)
                for part in parts:
                    chunk_type = ChunkType.TABLE if "|" in part and part.count("|") > 4 else ChunkType.TEXT
                    chunk_id = hashlib.md5(
                        f"{doc.doc_id}:{page.page_num}:{title_path}:{part[:100]}".encode()
                    ).hexdigest()[:16]
                    records.append(
                        ChunkRecord(
                            chunk_id=chunk_id,
                            doc_id=doc.doc_id,
                            file_path=doc.source_path,
                            title_path=title_path or doc.file_name,
                            page=page.page_num,
                            chunk_type=chunk_type,
                            content=part,
                            token_count=count_tokens(part),
                        )
                    )

        if self.settings.chunking.merge_short_chunks:
            records = self._merge_short(records, target_min, target_max)

        return records

    def _merge_short(
        self, records: list[ChunkRecord], target_min: int, target_max: int
    ) -> list[ChunkRecord]:
        if not records:
            return records

        merged: list[ChunkRecord] = []
        buffer: ChunkRecord | None = None

        for rec in records:
            if buffer is None:
                buffer = rec
                continue

            combined_tokens = buffer.token_count + rec.token_count
            if buffer.token_count < self.settings.chunking.min_tokens and combined_tokens <= target_max:
                buffer = ChunkRecord(
                    chunk_id=hashlib.md5(
                        f"{buffer.chunk_id}{rec.chunk_id}".encode()
                    ).hexdigest()[:16],
                    doc_id=buffer.doc_id,
                    file_path=buffer.file_path,
                    title_path=buffer.title_path,
                    page=buffer.page,
                    chunk_type=ChunkType.MIXED,
                    content=f"{buffer.content}\n\n{rec.content}",
                    token_count=combined_tokens,
                )
            else:
                merged.append(buffer)
                buffer = rec

        if buffer:
            merged.append(buffer)

        if self.settings.chunking.merge_short_chunks and len(merged) > 1:
            merged = self._llm_merge_optional(merged)

        return merged

    def _llm_merge_optional(self, records: list[ChunkRecord]) -> list[ChunkRecord]:
        """Use LLM to decide if adjacent short chunks should merge."""
        if get_settings().env.use_mock:
            return records

        result: list[ChunkRecord] = []
        i = 0
        llm = get_llm_client()

        while i < len(records):
            if (
                i + 1 < len(records)
                and records[i].token_count < self.settings.chunking.min_tokens
                and records[i + 1].token_count < self.settings.chunking.min_tokens
            ):
                prompt = (
                    "判断以下两个文本块是否应合并为一个检索单元。仅回复 JSON: "
                    '{"merge": true/false}\n\n'
                    f"块A:\n{records[i].content[:500]}\n\n块B:\n{records[i+1].content[:500]}"
                )
                try:
                    resp = llm.chat([{"role": "user", "content": prompt}])
                    data = parse_json_from_llm(resp)
                    if data.get("merge"):
                        combined = ChunkRecord(
                            chunk_id=uuid.uuid4().hex[:16],
                            doc_id=records[i].doc_id,
                            file_path=records[i].file_path,
                            title_path=records[i].title_path,
                            page=records[i].page,
                            chunk_type=ChunkType.MIXED,
                            content=f"{records[i].content}\n\n{records[i+1].content}",
                            token_count=records[i].token_count + records[i + 1].token_count,
                        )
                        result.append(combined)
                        i += 2
                        continue
                except Exception as e:
                    logger.debug("LLM merge skipped: %s", e)

            result.append(records[i])
            i += 1

        return result
