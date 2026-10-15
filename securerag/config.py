"""Central settings: defense switches, retrieval parameters and secrets from the environment."""

import os
from dataclasses import dataclass, field, replace

DEFENSES = ("d1_source_filter", "d2_anomaly", "d3_consistency", "d4_output_filter")


@dataclass(frozen=True)
class Config:
    chunk_tokens: int = 300
    top_k: int = 5
    temperature: float = 0.3
    seed: int = 42
    embedding_model: str = "all-MiniLM-L6-v2"
    # Model IDs are chosen and verified in week 1 (see PLAN.md); recorded in results/run_meta.json.
    groq_model: str = ""
    gemini_model: str = ""
    defenses: frozenset[str] = field(default_factory=frozenset)

    def with_defenses(self, *names: str) -> "Config":
        unknown = set(names) - set(DEFENSES)
        if unknown:
            raise ValueError(f"unknown defenses: {sorted(unknown)}")
        return replace(self, defenses=frozenset(names))

    def enabled(self, name: str) -> bool:
        return name in self.defenses


# The 6 evaluated configurations from PLAN.md: none, each defense alone, all four.
CONFIGS: dict[str, tuple[str, ...]] = {
    "none": (),
    "d1": ("d1_source_filter",),
    "d2": ("d2_anomaly",),
    "d3": ("d3_consistency",),
    "d4": ("d4_output_filter",),
    "combined": DEFENSES,
}


def groq_api_key() -> str | None:
    return os.environ.get("SECURERAG_GROQ_API_KEY") or None


def gemini_api_key() -> str | None:
    return os.environ.get("SECURERAG_GEMINI_API_KEY") or None
