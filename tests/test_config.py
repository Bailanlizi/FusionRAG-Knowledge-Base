"""Tests for configuration loading."""

import os

from src.utils.config import get_settings


def test_settings_load():
    os.environ["USE_MOCK"] = "true"
    settings = get_settings()
    assert settings.models.embedding_dim == 1024
    assert settings.retrieval.rrf_k == 60
