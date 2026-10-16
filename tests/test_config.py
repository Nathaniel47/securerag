import pytest

from securerag.config import CONFIGS, CORE_DEFENSES, Config, groq_api_key


def test_seven_configurations():
    assert len(CONFIGS) == 7
    assert CONFIGS["combined"] == CORE_DEFENSES


def test_with_defenses_toggles():
    cfg = Config().with_defenses("d1_source_filter")
    assert cfg.enabled("d1_source_filter")
    assert not cfg.enabled("d4_output_filter")


def test_unknown_defense_rejected():
    with pytest.raises(ValueError):
        Config().with_defenses("nope")


def test_missing_key_is_none(monkeypatch):
    monkeypatch.delenv("SECURERAG_GROQ_API_KEY", raising=False)
    assert groq_api_key() is None
