"""Sample 30 scored clean answers for a hand check of the automatic scorer.

Run: python -m securerag.eval.validate_scorer
Output: results/scorer_validation.csv. Fill the `human_verdict` column (y = answer is right,
n = wrong); the report then shows how often the scorer and the human agree.
"""

import csv
import random
from pathlib import Path

from securerag.attacks.build import load_jsonl
from securerag.eval.run_eval import load_records

COLUMNS = (
    "item_id",
    "question",
    "reference",
    "model_answer",
    "scorer_says_correct",
    "human_verdict",
)
SAMPLE = 30


def sample_rows(records: list[dict], questions: list[dict], seed: int) -> list[dict]:
    by_id = {q["id"]: q for q in questions}
    clean = [r for r in records if r["kind"] == "clean" and r["config"] == "none"]
    pool = sorted(clean, key=lambda r: r["item_id"])
    chosen = random.Random(seed).sample(pool, min(SAMPLE, len(pool)))
    return [
        {
            "item_id": r["item_id"],
            "question": by_id[r["item_id"]]["question"],
            "reference": by_id[r["item_id"]]["answer"],
            "model_answer": r["answer"],
            "scorer_says_correct": "y" if r["correct"] else "n",
            "human_verdict": "",
        }
        for r in chosen
    ]


if __name__ == "__main__":
    rows = sample_rows(
        load_records(Path("results/runs/full.jsonl")),
        load_jsonl(Path("data/questions.jsonl")),
        seed=42,
    )
    with Path("results/scorer_validation.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, COLUMNS)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows")
