from types import SimpleNamespace

from jobmatch import llm, monitoring
from jobmatch.match import service
from jobmatch.match.cache import text_hash
from jobmatch.match.fit import AdRequirements

REQ = AdRequirements(
    required_skills=["Python"], nice_to_have_skills=[], min_years=None,
    seniority="junior", requires_swedish=False, key_quotes=[],
)


def test_cloud_provider_uses_json_mode_and_counts_tokens(monkeypatch):
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=REQ.model_dump_json()))],
            usage=SimpleNamespace(prompt_tokens=200, completion_tokens=40),
        )

    fake = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(llm, "LLM_PROVIDER", "openai")
    monkeypatch.setattr(llm, "LLM_JSON_MODE", "object")
    monkeypatch.setattr(llm, "_openai_client", lambda: fake)
    stats = monitoring.start_request()
    result = llm.chat_json("Read the ad.", "ad text", AdRequirements)
    assert result.required_skills == ["Python"]
    assert calls[0]["response_format"] == {"type": "json_object"}
    assert "JSON schema" in calls[0]["messages"][0]["content"]
    assert (stats["llm_tokens_in"], stats["llm_tokens_out"]) == (200, 40)


def test_read_many_runs_in_parallel_skips_failures_and_records_usage(monkeypatch):
    def fake_read(title, _text):
        llm.record_llm_call(10, 5, 1.0)
        if title == "broken":
            raise llm.LLMError("bad")
        return REQ

    monkeypatch.setattr(service, "read_requirements", fake_read)
    monkeypatch.setattr(service, "LLM_PARALLEL", 3)
    ads = [{"id": str(i), "title": "broken" if i == 2 else "ok"} for i in range(4)]
    stats = monitoring.start_request()
    result = service.read_many(ads, {ad["id"]: "text" for ad in ads})
    assert sorted(result) == ["0", "1", "3"]  # ad 2 failed and was skipped
    assert stats["llm_calls"] == 4  # usage from all threads was counted


def test_text_hash_changes_when_the_ad_changes():
    assert text_hash("We need Python") == text_hash("We need Python")
    assert text_hash("We need Python") != text_hash("We need Python and SQL")


def test_strict_schema_follows_the_strict_mode_rules():
    from jobmatch.llm import strict_schema
    from jobmatch.match.profile import CandidateProfile

    schema = strict_schema(CandidateProfile.model_json_schema())
    experience = schema["properties"]["experiences"]["items"]
    assert "$defs" not in schema and "$ref" not in str(schema)  # nested model copied in place
    assert experience["required"] == ["title", "start", "end"]  # a field called "title" is kept
    assert experience["additionalProperties"] is False
    assert "pattern" not in str(schema)
    assert set(schema["required"]) == set(schema["properties"])


def test_provider_error_counts_as_a_failed_try_and_is_retried(monkeypatch):
    import httpx
    from openai import BadRequestError

    answers = iter(["error", REQ.model_dump_json()])

    def create(**kwargs):
        answer = next(answers)
        if answer == "error":
            response = httpx.Response(400, request=httpx.Request("POST", "https://api.example.com"))
            raise BadRequestError("Failed to validate JSON", response=response, body=None)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=answer))],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1),
        )

    fake = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(llm, "LLM_PROVIDER", "openai")
    monkeypatch.setattr(llm, "_openai_client", lambda: fake)
    assert llm.chat_json("Read the ad.", "ad text", AdRequirements).required_skills == ["Python"]
