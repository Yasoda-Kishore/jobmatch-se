import math

from jobmatch.evaluation.metrics import ndcg_at_k, recall_at_k, reciprocal_rank

RELEVANT = {"a", "b"}


def test_recall_counts_found_relevant_ads():
    assert recall_at_k(["a", "x", "y"], RELEVANT) == 0.5
    assert recall_at_k(["x", "b", "a"], RELEVANT) == 1.0
    assert recall_at_k(["x", "y"], RELEVANT) == 0.0


def test_reciprocal_rank_uses_first_relevant_position():
    assert reciprocal_rank(["a", "x"], RELEVANT) == 1.0
    assert reciprocal_rank(["x", "y", "b"], RELEVANT) == 1 / 3
    assert reciprocal_rank(["x"], RELEVANT) == 0.0


def test_ndcg_is_one_for_a_perfect_ranking():
    assert ndcg_at_k(["a", "b", "x"], RELEVANT) == 1.0


def test_ndcg_is_lower_when_relevant_ads_are_lower():
    perfect = ndcg_at_k(["a", "b", "x"], RELEVANT)
    worse = ndcg_at_k(["x", "a", "b"], RELEVANT)
    assert worse < perfect
    # worked example: hits at positions 2 and 3, ideal hits at positions 1 and 2
    expected = (1 / math.log2(3) + 1 / math.log2(4)) / (1 + 1 / math.log2(3))
    assert math.isclose(worse, expected)