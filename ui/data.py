"""Turn run records into the tables the dashboard shows."""

from pathlib import Path

import pandas as pd

from securerag.config import CONFIGS
from securerag.eval.metrics import summarize
from securerag.eval.run_eval import load_records

RUNS = Path("results/runs/full.jsonl")


def fmt(r: dict) -> str:
    return f"{r['rate']:.0%} ({r['k']}/{r['n']})" if r["n"] else "n/a"


def summary_tables(records: list[dict]) -> dict[str, pd.DataFrame]:
    s = summarize(records)
    order = [c for c in CONFIGS if c in s]
    kinds = sorted({k for c in s.values() for k in c["asr"]})
    asr = pd.DataFrame(
        {k: [fmt(s[c]["asr"][k]) if k in s[c]["asr"] else "n/a" for c in order] for k in kinds},
        index=order,
    )
    asr["all attacks"] = [fmt(s[c]["asr_all"]) for c in order]
    quality = pd.DataFrame(
        {
            "clean accuracy": [fmt(s[c]["accuracy"]) for c in order],
            "false blocks": [fmt(s[c]["false_block"]) for c in order],
            "false flags": [fmt(s[c]["false_flag"]) for c in order],
            "LLM calls/query": [round(s[c]["calls_per_query"], 2) for c in order],
        },
        index=order,
    )
    rates = pd.DataFrame(
        {
            "attack success": [s[c]["asr_all"]["rate"] for c in order],
            "clean accuracy": [s[c]["accuracy"]["rate"] for c in order],
        },
        index=order,
    )
    return {"asr": asr, "quality": quality, "rates": rates}


def load_results(path: Path = RUNS) -> list[dict]:
    return load_records(path)


def replay_rows(records: list[dict], item_id: str) -> list[dict]:
    """One row per configuration for a recorded query (first repeat only), in CONFIGS order."""
    by_cfg = {r["config"]: r for r in records if r["item_id"] == item_id and r["repeat"] == 0}
    rows = []
    for cfg in CONFIGS:
        r = by_cfg.get(cfg)
        if r is None:
            continue
        outcome = r.get("success") if "success" in r else r.get("correct")
        rows.append(
            {
                "config": cfg,
                "blocked": r["blocked"],
                "defenses fired": "; ".join(r["fired"]) or "-",
                "outcome": outcome,
                "answer": r["answer"],
            }
        )
    return rows
