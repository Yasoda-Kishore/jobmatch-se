"""Settings for every test: tests never call a real LLM, whatever is set in the terminal."""
import pytest

from jobmatch import llm


def _no_real_llm():
    raise RuntimeError("Tests must not call a real LLM. Use monkeypatch to fake it.")


@pytest.fixture(autouse=True)
def offline_llm(monkeypatch):
    monkeypatch.setattr(llm, "LLM_PROVIDER", "ollama")
    monkeypatch.setattr(llm, "LLM_JSON_MODE", "schema")
    monkeypatch.setattr(llm, "LLM_REASONING_EFFORT", "")
    monkeypatch.setattr(llm, "_openai_client", _no_real_llm)