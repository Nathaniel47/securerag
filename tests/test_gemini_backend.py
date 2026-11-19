import sys
import types

import pytest

from securerag.llm.gemini import gemini_backend


def fake_google(monkeypatch, record):
    """A stand-in for the google-genai package, so no key or network is needed."""

    class Models:
        def generate_content(self, model, contents, config):
            record["call"] = (model, contents, config)
            usage = types.SimpleNamespace(total_token_count=42)
            return types.SimpleNamespace(text="an answer", usage_metadata=usage)

    class Client:
        def __init__(self, api_key):
            record["api_key"] = api_key
            self.models = Models()

    class Config:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    genai = types.ModuleType("google.genai")
    genai.Client = Client
    genai.types = types.SimpleNamespace(GenerateContentConfig=Config)
    google = types.ModuleType("google")
    google.genai = genai
    monkeypatch.setitem(sys.modules, "google", google)
    monkeypatch.setitem(sys.modules, "google.genai", genai)
    monkeypatch.setitem(sys.modules, "google.genai.types", genai.types)


def test_backend_sends_system_and_user_text_and_returns_text_and_tokens(monkeypatch):
    record = {}
    fake_google(monkeypatch, record)
    monkeypatch.setenv("SECURERAG_GEMINI_API_KEY", "test-key")
    messages = [{"role": "system", "content": "be brief"}, {"role": "user", "content": "hi"}]
    text, tokens = gemini_backend("gemini-x", messages, 0.0, 7, {"max_completion_tokens": 50})
    assert (text, tokens) == ("an answer", 42)
    model, contents, config = record["call"]
    assert (model, contents) == ("gemini-x", "hi")
    assert config.system_instruction == "be brief" and config.seed == 7
    assert record["api_key"] == "test-key"


def test_backend_refuses_to_run_without_a_key(monkeypatch):
    fake_google(monkeypatch, {})
    monkeypatch.delenv("SECURERAG_GEMINI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="SECURERAG_GEMINI_API_KEY"):
        gemini_backend("gemini-x", [{"role": "user", "content": "hi"}], 0.0, 1, {})
