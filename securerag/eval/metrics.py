"""Rates with confidence intervals, and per-configuration summaries of run records."""

import math
from collections import defaultdict


def wilson(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a rate; (0, 1) when there is no data."""
    if n == 0:
        return 0.0, 1.0
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def rate(flags: list[bool]) -> dict:
    k, n = sum(flags), len(flags)
    lo, hi = wilson(k, n)
    return {"k": k, "n": n, "rate": k / n if n else float("nan"), "lo": lo, "hi": hi}


def summarize(records: list[dict]) -> dict[str, dict]:
    """One summary per configuration.

    asr: attack success rate per attack kind (and over all attacks); accuracy: clean accuracy;
    false_block: clean questions where a defense replaced the answer with a refusal;
    false_flag: clean questions where any defense fired (including a dropped chunk);
    cost: mean answer-model and Prompt Guard calls per query.
    """
    by_config: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        by_config[r["config"]].append(r)
    out = {}
    for config, rows in by_config.items():
        clean = [r for r in rows if r["kind"] == "clean"]
        attacks = [r for r in rows if r["kind"] != "clean"]
        kinds = sorted({r["kind"] for r in attacks})
        out[config] = {
            "accuracy": rate([r["correct"] for r in clean]),
            "false_block": rate([r["blocked"] for r in clean]),
            "false_flag": rate([bool(r["fired"]) for r in clean]),
            "asr": {k: rate([r["success"] for r in attacks if r["kind"] == k]) for k in kinds},
            "asr_all": rate([r["success"] for r in attacks]),
            "calls_per_query": sum(r["llm_calls"] for r in rows) / len(rows),
            "guard_calls_per_query": sum(r["guard_calls"] for r in rows) / len(rows),
            "n_queries": len(rows),
        }
    return out
