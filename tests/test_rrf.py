"""Tests for Reciprocal Rank Fusion."""

from src.retrieval.rrf import reciprocal_rank_fusion


def test_rrf_single_list():
    ranked = [["a", "b", "c"]]
    result = reciprocal_rank_fusion(ranked, k=60, top_n=3)
    assert result[0][0] == "a"
    assert len(result) == 3


def test_rrf_merge_two_lists():
    list1 = ["a", "b", "c"]
    list2 = ["b", "a", "d"]
    result = reciprocal_rank_fusion([list1, list2], k=60, top_n=4)
    ids = [r[0] for r in result]
    assert "a" in ids
    assert "b" in ids
    assert result[0][1] >= result[-1][1]


def test_rrf_empty():
    result = reciprocal_rank_fusion([], k=60, top_n=5)
    assert result == []
