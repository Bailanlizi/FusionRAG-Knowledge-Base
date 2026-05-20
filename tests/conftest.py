"""Pytest hooks: mock Milvus in CI/local when USE_MOCK=true (no Milvus server required)."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

if os.environ.get("USE_MOCK", "").lower() == "true":

    def _make_milvus_store() -> MagicMock:
        store = MagicMock()
        store.collection_exists.return_value = False
        store.dense_search.return_value = []
        store.sparse_search.return_value = []
        return store

    import src.utils.db  # noqa: F401 — ensure patch target exists

    patch("src.utils.db.MilvusStore", side_effect=_make_milvus_store).start()
