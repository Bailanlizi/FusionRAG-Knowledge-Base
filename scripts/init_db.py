#!/usr/bin/env python3
"""Initialize PostgreSQL tables and Milvus collection."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.config import get_settings
from src.utils.db import MilvusStore, PostgresClient
from src.utils.logger import logger


def main() -> None:
    settings = get_settings()
    logger.info("Initializing databases...")
    logger.info("PostgreSQL: %s", settings.env.postgres_url.split("@")[-1])
    logger.info("Milvus: %s:%s", settings.env.milvus_host, settings.env.milvus_port)

    pg = PostgresClient()
    pg.init_tables()
    logger.info("PostgreSQL OK")

    milvus = MilvusStore()
    milvus.create_collection(drop_existing=False)
    count = milvus.count()
    logger.info("Milvus OK — collection '%s' has %d entities", milvus.collection_name, count)
    logger.info("Database initialization complete.")


if __name__ == "__main__":
    main()
