#!/usr/bin/env python3
"""Ingest documents from data/documents into the knowledge base."""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingestion.indexer import DocumentIndexer
from src.utils.config import get_settings
from src.utils.db import MilvusStore, PostgresClient
from src.utils.logger import logger


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest documents into FusionRAG")
    parser.add_argument(
        "--path",
        type=str,
        default=str(get_settings().project_root / "data" / "documents"),
        help="Directory containing documents",
    )
    parser.add_argument("--recursive", action="store_true", default=True)
    parser.add_argument("--force", action="store_true", help="Re-index even if unchanged")
    parser.add_argument("--init-db", action="store_true", help="Initialize DB before ingest")
    args = parser.parse_args()

    if args.init_db:
        pg = PostgresClient()
        pg.init_tables()
        milvus = MilvusStore()
        milvus.create_collection()

    indexer = DocumentIndexer()
    total = indexer.index_directory(args.path, recursive=args.recursive)
    logger.info("Ingestion complete. Total new chunks: %d", total)


if __name__ == "__main__":
    main()
