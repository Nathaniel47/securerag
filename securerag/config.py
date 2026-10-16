"""Central settings: defense switches, retrieval parameters and secrets from the environment."""

import os
from dataclasses import dataclass, field, replace

CORE_DEFENSES = ("d1_source_filter", "d2_anomaly", "d3_consistency", "d4_output_filter")
# D5 was added after the plan froze the four core defenses; it is evaluated alone and is not
# part of the "combined" configuration, so combined stays comparable with PLAN.md.
DEFENSES = (*CORE_DEFENSES, "d5_prompt_guard")

GROQ_MAIN_MODEL = "openai/gpt-oss-20b"
GROQ_GUARD_MODEL = "meta-llama/llama-prompt-guard-2-86m"

# Free-tier limits reported by the account owner on 2026-10-16 (per organisation).
# rpm/rpd = requests per minute/day, tpm/tpd = tokens per minute/day. TPD resets at 00:00 UTC.
RATE_LIMITS: dict[str, dict[str, int]] = {
    "openai/gpt-oss-20b": {"rpm": 30, "rpd": 1000, "tpm": 8000, "tpd": 200_000},
    "openai/gpt-oss-120b": {"rpm": 30, "rpd": 1000, "tpm": 8000, "tpd": 200_000},
    "qwen/qwen3.8-27b": {"rpm": 30, "rpd": 1000, "tpm": 8000, "tpd": 200_000},
    "meta-llama/llama-prompt-guard-2-86m": {
        "rpm": 30,
        "rpd": 14_400,
        "tpm": 15_000,
        "tpd": 500_000,
    },
}


@dataclass(frozen=True)
class Config:
    chunk_tokens: int = 300
    # Token budget: about 700 tokens per answer call = 3 chunks trimmed to 600 chars (~150 tokens
    # each) + ~100 tokens of rules and question + a short answer (see rag/prompt.py).
    top_k: int = 3
    chunk_trim_chars: int = 600
    target_tokens_per_call: int = 700
    expected_completion_tokens: int = 120
    max_completion_tokens: int = 400  # reasoning tokens count as output, so leave headroom
    temperature: float = 0.3
    seed: int = 42
    embedding_model: str = "all-MiniLM-L6-v2"
    # Chosen 2026-10-16: llama-3.1-8b-instant is not available on the owner's account.
    groq_model: str = GROQ_MAIN_MODEL
    reasoning_effort: str = "low"
    prompt_guard_model: str = GROQ_GUARD_MODEL
    prompt_guard_threshold: float = 0.5
    gemini_model: str = "gemini-3.5-flash-lite"
    defenses: frozenset[str] = field(default_factory=frozenset)

    def with_defenses(self, *names: str) -> "Config":
        unknown = set(names) - set(DEFENSES)
        if unknown:
            raise ValueError(f"unknown defenses: {sorted(unknown)}")
        return replace(self, defenses=frozenset(names))

    def enabled(self, name: str) -> bool:
        return name in self.defenses


# The 7 evaluated configurations: none, each defense alone (5), and the four core combined.
CONFIGS: dict[str, tuple[str, ...]] = {
    "none": (),
    "d1": ("d1_source_filter",),
    "d2": ("d2_anomaly",),
    "d3": ("d3_consistency",),
    "d4": ("d4_output_filter",),
    "combined": CORE_DEFENSES,
    "d5": ("d5_prompt_guard",),
}


def groq_api_key() -> str | None:
    return os.environ.get("SECURERAG_GROQ_API_KEY") or None


def gemini_api_key() -> str | None:
    return os.environ.get("SECURERAG_GEMINI_API_KEY") or None
