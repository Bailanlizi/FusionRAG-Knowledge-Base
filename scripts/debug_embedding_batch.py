#!/usr/bin/env python3
"""Local debug: test embedding batch sizes on a sample document (not run in CI)."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingestion.chunker import SemanticChunker, count_tokens
from src.ingestion.parser import DocumentParser
from src.utils.api_clients import get_embedding_client
from src.utils.config import get_settings

DEFAULT_PATH = (
    PROJECT_ROOT
    / "data/documents/dsid_5ae656c5449149fa8029551d47d843c3__adr-027-terraform-module-boundaries-and-interface.txt"
)


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PATH
    if not path.exists():
        print(f"File not found: {path}")
        print("Usage: python scripts/debug_embedding_batch.py [path/to/document.txt]")
        sys.exit(1)

    chunks = SemanticChunker().chunk(DocumentParser().parse(path))
    texts = [c.content for c in chunks]

    print("chunk 数量:", len(chunks))
    print("配置 batch_size:", get_settings().ingest.batch_size)
    print("最长 chunk tokens:", max(count_tokens(t) for t in texts) if texts else 0)

    client = get_embedding_client()

    try:
        client.embed(texts[:16])
        print("前 16 条: 成功")
    except Exception as e:
        print("前 16 条: 失败", e)
        if e.__cause__:
            print("  cause:", e.__cause__)

    try:
        client.embed(texts[:10])
        print("前 10 条: 成功")
    except Exception as e:
        print("前 10 条: 失败", e)
        if e.__cause__:
            print("  cause:", e.__cause__)


if __name__ == "__main__":
    main()
