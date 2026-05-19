"""API tests with USE_MOCK."""

from __future__ import annotations

import os

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

os.environ.setdefault("USE_MOCK", "true")
os.environ.setdefault("DASHSCOPE_API_KEY", "mock-key")

from src.api.main import app
from src.utils.db import PostgresClient


@pytest.fixture(scope="module")
def client():
    pg = PostgresClient()
    pg.init_tables()
    return TestClient(app)


def test_health(client: TestClient):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_kb_stats(client: TestClient):
    r = client.get("/api/kb/stats")
    assert r.status_code == 200
    data = r.json()
    assert "document_count" in data
    assert "chunk_count" in data


def test_conversation_flow(client: TestClient):
    r = client.post("/api/conversations", json={"title": "test"})
    assert r.status_code == 201
    conv_id = r.json()["id"]

    r2 = client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": "What is FusionRAG?"},
    )
    assert r2.status_code == 200
    body = r2.json()
    assert body["role"] == "assistant"
    assert body["content"]
    assert "trace" in body

    r3 = client.get(f"/api/conversations/{conv_id}")
    assert r3.status_code == 200
    assert len(r3.json()["messages"]) >= 2

    client.delete(f"/api/conversations/{conv_id}")


def test_list_documents(client: TestClient):
    r = client.get("/api/documents")
    assert r.status_code == 200
    assert "items" in r.json()
