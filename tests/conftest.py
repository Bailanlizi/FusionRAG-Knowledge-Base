"""Pytest configuration."""

import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("USE_MOCK", "true")
os.environ.setdefault("DASHSCOPE_API_KEY", "mock-key-for-tests")


@pytest.fixture(autouse=True)
def mock_mode():
    os.environ["USE_MOCK"] = "true"
