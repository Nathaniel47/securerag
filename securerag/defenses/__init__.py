"""Build the defense objects for a configuration."""

from securerag.config import Config
from securerag.defenses.anomaly import AnomalyScore
from securerag.defenses.base import Defense
from securerag.defenses.consistency import AnswerConsistency
from securerag.defenses.output_filter import OutputFilter
from securerag.defenses.prompt_guard import PromptGuard
from securerag.defenses.source_filter import SourceFilter
from securerag.llm.client import LLMClient


def build_defenses(cfg: Config, guard: LLMClient | None = None) -> list[Defense]:
    """Defenses enabled in `cfg`, in pipeline order. D5 needs a Prompt Guard client."""
    made: list[Defense] = []
    if cfg.enabled("d1_source_filter"):
        made.append(SourceFilter())
    if cfg.enabled("d2_anomaly"):
        made.append(AnomalyScore())
    if cfg.enabled("d3_consistency"):
        made.append(AnswerConsistency())
    if cfg.enabled("d4_output_filter"):
        made.append(OutputFilter())
    if cfg.enabled("d5_prompt_guard"):
        if guard is None:
            raise ValueError("d5_prompt_guard needs a Prompt Guard client")
        made.append(PromptGuard(guard, cfg.prompt_guard_threshold))
    return made
