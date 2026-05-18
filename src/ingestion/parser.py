"""Document parser: Docling + optional PaddleOCR enhancement."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from src.ingestion.models import ChunkType, ContentBlock, ParsedDocument, ParsedPage
from src.utils.config import get_settings
from src.utils.logger import logger

SUPPORTED_EXTENSIONS = {".pdf", ".md", ".markdown", ".txt"}


def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _table_to_markdown(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    header = rows[0]
    sep = ["---"] * len(header)
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(sep) + " |",
    ]
    for row in rows[1:]:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


def _assess_complexity(
    text: str,
    has_images: bool,
    table_rows: int,
    table_cols: int,
    ocr_confidence: float,
) -> tuple[float, bool]:
    """Heuristic complexity score and whether OCR enhance is needed."""
    score = 0.0
    if has_images:
        score += 0.3
    if table_rows > 5 and table_cols > 4:
        score += 0.3
    if ocr_confidence < 0.7:
        score += 0.4
    if len(text.strip()) < 50:
        score += 0.2
    needs_ocr = score >= get_settings().ocr.complexity_threshold
    return min(score, 1.0), needs_ocr


class DocumentParser:
    """Parse PDF/Markdown into standardized ParsedDocument."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def parse(self, file_path: str | Path) -> ParsedDocument:
        path = Path(file_path).resolve()
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {path.suffix}")

        doc_id = hashlib.md5(str(path).encode()).hexdigest()[:16]
        content_hash = _file_hash(path)

        if path.suffix.lower() in {".md", ".markdown", ".txt"}:
            return self._parse_markdown(path, doc_id, content_hash)

        return self._parse_pdf(path, doc_id, content_hash)

    def _parse_markdown(self, path: Path, doc_id: str, content_hash: str) -> ParsedDocument:
        text = path.read_text(encoding="utf-8")
        page = ParsedPage(
            page_num=1,
            markdown=text,
            blocks=[ContentBlock(block_type=ChunkType.TEXT, text=text)],
        )
        return ParsedDocument(
            doc_id=doc_id,
            source_path=str(path),
            file_name=path.name,
            pages=[page],
            full_markdown=text,
            complexity_score=0.0,
            content_hash=content_hash,
        )

    def _parse_pdf(self, path: Path, doc_id: str, content_hash: str) -> ParsedDocument:
        try:
            from docling.document_converter import DocumentConverter
        except ImportError as e:
            raise ImportError("docling is required for PDF parsing. pip install docling") from e

        converter = DocumentConverter()
        result = converter.convert(str(path))
        doc = result.document

        pages: list[ParsedPage] = []
        max_complexity = 0.0

        try:
            md_content = doc.export_to_markdown()
        except Exception:
            md_content = ""

        page_texts = re.split(r"\n---+\n", md_content) if md_content else [md_content or ""]

        for i, page_text in enumerate(page_texts, start=1):
            has_images = "![" in page_text or "<!-- image" in page_text.lower()
            table_rows, table_cols = 0, 0
            table_blocks: list[ContentBlock] = []

            for table_match in re.finditer(r"\|(.+)\|", page_text):
                row = [c.strip() for c in table_match.group(1).split("|")]
                table_rows += 1
                table_cols = max(table_cols, len(row))

            ocr_confidence = 0.95 if len(page_text.strip()) > 100 else 0.5
            complexity, needs_ocr = _assess_complexity(
                page_text, has_images, table_rows, table_cols, ocr_confidence
            )
            max_complexity = max(max_complexity, complexity)

            if needs_ocr and self.settings.ocr.enabled:
                enhanced = self._paddle_ocr_enhance(path, i)
                if enhanced:
                    page_text = enhanced
                    logger.info("PaddleOCR enhanced page %d of %s", i, path.name)

            blocks = [ContentBlock(block_type=ChunkType.TEXT, text=page_text)]
            if table_rows > 2:
                blocks.append(
                    ContentBlock(
                        block_type=ChunkType.TABLE,
                        text=page_text,
                        metadata={"rows": table_rows, "cols": table_cols},
                    )
                )

            pages.append(
                ParsedPage(
                    page_num=i,
                    markdown=page_text,
                    blocks=blocks,
                    has_images=has_images,
                    has_complex_table=table_rows > 5 and table_cols > 4,
                    ocr_confidence=ocr_confidence,
                    needs_ocr_enhance=needs_ocr,
                )
            )

        if not pages:
            pages.append(
                ParsedPage(
                    page_num=1,
                    markdown=md_content or "",
                    blocks=[ContentBlock(text=md_content or "")],
                )
            )

        return ParsedDocument(
            doc_id=doc_id,
            source_path=str(path),
            file_name=path.name,
            pages=pages,
            full_markdown="\n\n".join(p.markdown for p in pages),
            complexity_score=max_complexity,
            content_hash=content_hash,
        )

    def _paddle_ocr_enhance(self, path: Path, page_num: int) -> str | None:
        """Optional PaddleOCR enhancement for complex pages (CPU, with timeout)."""
        import signal
        from contextlib import contextmanager

        @contextmanager
        def timeout(seconds: int):
            def handler(signum, frame):
                raise TimeoutError("PaddleOCR timeout")

            if hasattr(signal, "SIGALRM"):
                old = signal.signal(signal.SIGALRM, handler)
                signal.alarm(seconds)
                try:
                    yield
                finally:
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, old)
            else:
                yield

        try:
            from paddleocr import PaddleOCR

            ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
            with timeout(self.settings.ocr.timeout_seconds):
                result = ocr.ocr(str(path), cls=True)
            if not result:
                return None
            lines = []
            for page_result in result:
                if page_result:
                    for line in page_result:
                        if line and len(line) >= 2:
                            lines.append(line[1][0])
            return "\n".join(lines) if lines else None
        except Exception as e:
            logger.warning("PaddleOCR failed for %s page %d: %s", path.name, page_num, e)
            return None
