"""Tests for multi-turn query rewriting."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("USE_MOCK", "true")
os.environ.setdefault("DASHSCOPE_API_KEY", "mock-key")

from src.retrieval.query_rewriter import QueryRewriter, format_history, trim_history
from src.retrieval.schemas import ChatTurn


def test_trim_history_limits_turns_and_truncates_assistant():
    turns = [
        ChatTurn(role="user", content="q1"),
        ChatTurn(role="assistant", content="a" * 500),
        ChatTurn(role="user", content="q2"),
    ]
    trimmed = trim_history(turns, max_turns=2, max_assistant_chars=100)
    assert len(trimmed) == 2
    assert trimmed[0].role == "assistant"
    assert trimmed[0].content.endswith("…")
    assert len(trimmed[0].content) == 101
    assert trimmed[1].content == "q2"


def test_rewrite_without_history_returns_original():
    rewriter = QueryRewriter()
    result = rewriter.rewrite("Milvus 怎么部署？", [])
    assert result.standalone_query == "Milvus 怎么部署？"
    assert result.is_follow_up is False


def test_rewrite_with_history_uses_mock():
    rewriter = QueryRewriter()
    history = [
        ChatTurn(role="user", content="Milvus 怎么部署？"),
        ChatTurn(role="assistant", content="使用 docker compose..."),
    ]
    result = rewriter.rewrite("第二步具体命令是什么？", history)
    assert result.standalone_query
    assert result.is_follow_up is True


def test_format_history():
    text = format_history([ChatTurn(role="user", content="hello")])
    assert "用户：hello" in text
