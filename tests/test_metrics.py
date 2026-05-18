"""Tests for evaluation metrics."""

import pytest

from src.evaluation.metrics import hit_at_k, ndcg_at_k, recall_at_k, mrr


def test_recall_at_k():
    retrieved = ["a", "b", "c", "d"]
    relevant = {"a", "c", "e"}
    assert recall_at_k(retrieved, relevant, 3) == 2 / 3
    assert recall_at_k(retrieved, relevant, 1) == 1 / 3


def test_hit_at_k():
    retrieved = ["x", "y", "a"]
    relevant = {"a"}
    assert hit_at_k(retrieved, relevant, 1) == 0.0
    assert hit_at_k(retrieved, relevant, 5) == 1.0


def test_mrr():
    lists = [["a", "b"], ["x", "y", "a"]]
    relevant = [{"a"}, {"a"}]
    assert mrr(lists, relevant) == pytest.approx((1.0 + 1 / 3) / 2)


def test_ndcg_perfect():
    retrieved = ["a", "b", "c"]
    relevant = {"a", "b"}
    score = ndcg_at_k(retrieved, relevant, 3)
    assert score == 1.0


def test_ndcg_zero_relevant():
    assert ndcg_at_k(["a"], set(), 5) == 0.0
