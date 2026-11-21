from types import SimpleNamespace

from fastapi.testclient import TestClient

from jobmatch import llm, monitoring
from jobmatch.api.main import app
from jobmatch.match.profile import CandidateProfile

GOOD = (
    '{"target_roles": ["ML Engineer"], "skills": ["Python"],'
    ' "experiences": [{"title": "Intern", "start": "2024-03", "end": "2024-05"}],'
    ' "spoken_languages": ["English"], "education": "BSc CS", "summary": "x"}'
)


def test_every_request_gets_a_response_time_header():
    response = TestClient(app).get("/health")
    assert int(response.headers["X-Response-Time-ms"]) >= 0


def test_metrics_counts_requests_per_endpoint():
    monitoring.RECENT.clear()
    client = TestClient(app)
    for _ in range(3):
        client.get("/health")
    assert client.get("/metrics").json()["/health"]["requests"] == 3


def test_llm_tokens_are_added_to_the_current_request(monkeypatch):
    reply = SimpleNamespace(message=SimpleNamespace(content=GOOD), prompt_eval_count=120, eval_count=30)
    monkeypatch.setattr(llm.ollama, "chat", lambda **_kwargs: reply)
    stats = monitoring.start_request()
    llm.chat_json("system", "user", CandidateProfile)
    assert stats["llm_calls"] == 1
    assert (stats["llm_tokens_in"], stats["llm_tokens_out"]) == (120, 30)


def test_percentile():
    assert monitoring.percentile([10, 20, 30, 40, 50, 60, 70, 80, 90, 100], 0.95) == 100
    assert monitoring.percentile([5], 0.95) == 5
