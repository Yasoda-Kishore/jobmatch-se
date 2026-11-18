from fastapi.testclient import TestClient

from jobmatch.api.main import app
from jobmatch.search.common import best_per_ad
from jobmatch.search.engine import reciprocal_rank_fusion
from jobmatch.search.keyword import to_or_query


def test_to_or_query_joins_words_with_or():
    assert to_or_query("Python Data-Engineer!") == "python | data | engineer"


def test_to_or_query_keeps_swedish_letters_and_drops_symbols():
    assert to_or_query("Göteborg & (utvecklare)") == "göteborg | utvecklare"
    assert to_or_query("!!") is None


def test_best_per_ad_keeps_first_row_per_ad():
    rows = [("a", 0.9), ("a", 0.8), ("b", 0.7), ("c", 0.6)]
    assert best_per_ad(rows, k=2) == [("a", 0.9), ("b", 0.7)]


def test_rrf_rewards_ads_found_by_both_methods():
    vector = [("a", 0.9), ("b", 0.8), ("c", 0.7)]
    keyword = [("c", 5.0), ("d", 4.0)]
    fused = [ad_id for ad_id, _ in reciprocal_rank_fusion(vector, keyword)]
    assert fused[0] == "c"  # found by both lists, so it wins
    assert set(fused) == {"a", "b", "c", "d"}


def test_health_endpoint():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}