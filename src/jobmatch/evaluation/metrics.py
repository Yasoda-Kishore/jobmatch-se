"""Search quality metrics. `ranked` = ad ids in the order the search returned them."""
import math


def recall_at_k(ranked: list[str], relevant: set[str], k: int = 10) -> float:
    """Out of all the relevant ads, what share appears in the top k?"""
    if not relevant:
        return 0.0
    return len(set(ranked[:k]) & relevant) / len(relevant)


def reciprocal_rank(ranked: list[str], relevant: set[str]) -> float:
    """1 / position of the first relevant ad (1.0 if it is first, 0 if none is found)."""
    for position, ad_id in enumerate(ranked, start=1):
        if ad_id in relevant:
            return 1 / position
    return 0.0


def ndcg_at_k(ranked: list[str], relevant: set[str], k: int = 10) -> float:
    """Ranking quality from 0 to 1. A relevant ad counts more the higher it is."""
    dcg = sum(1 / math.log2(pos + 1) for pos, ad_id in enumerate(ranked[:k], start=1) if ad_id in relevant)
    ideal_hits = min(len(relevant), k)
    idcg = sum(1 / math.log2(pos + 1) for pos in range(1, ideal_hits + 1))
    return dcg / idcg if idcg else 0.0