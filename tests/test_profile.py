from types import SimpleNamespace

import pytest

from jobmatch import llm
from jobmatch.match.profile import CandidateProfile, build_search_query

GOOD = (
    '{"target_roles": ["ML Engineer"], "skills": ["Python", "PyTorch", "Docker"],'
    ' "years_of_experience": 1.0, "languages": ["English"], "education": "BSc CS",'
    ' "summary": "A junior ML engineer."}'
)


def fake_chat(answers):
    """Replace ollama.chat with a function that returns the given answers in order."""
    replies = iter(answers)

    def chat(**_kwargs):
        return SimpleNamespace(message=SimpleNamespace(content=next(replies)))

    return chat


def test_chat_json_returns_valid_profile(monkeypatch):
    monkeypatch.setattr(llm.ollama, "chat", fake_chat([GOOD]))
    profile = llm.chat_json("system", "user", CandidateProfile)
    assert profile.skills == ["Python", "PyTorch", "Docker"]


def test_chat_json_retries_after_bad_json(monkeypatch):
    monkeypatch.setattr(llm.ollama, "chat", fake_chat(["not json", '{"skills": 5}', GOOD]))
    profile = llm.chat_json("system", "user", CandidateProfile)
    assert profile.target_roles == ["ML Engineer"]


def test_chat_json_gives_up_after_max_tries(monkeypatch):
    monkeypatch.setattr(llm.ollama, "chat", fake_chat(["bad"] * llm.MAX_TRIES))
    with pytest.raises(llm.LLMError):
        llm.chat_json("system", "user", CandidateProfile)


def test_build_search_query_uses_role_and_top_skills():
    profile = CandidateProfile.model_validate_json(GOOD)
    assert build_search_query(profile, max_skills=2) == "ML Engineer Python PyTorch"