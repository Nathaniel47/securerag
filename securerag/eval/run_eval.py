"""Evaluation runner: every configuration over the clean questions and the attack attempts.

Resume command (safe to run every day; finished work is skipped, and answered calls are cached):
    python -m securerag.eval.run_eval --mode full

It stops cleanly when the day's token budget is used up (exit code 75) and carries on after
00:00 UTC. Results are appended to results/runs/<mode>[_r<repeat>].jsonl, one line per query.
"""

import argparse
import json
import random
import sys
from pathlib import Path

from securerag.attacks.base import Attack
from securerag.attacks.build import load_attacks, load_jsonl
from securerag.attacks.run import run_attack
from securerag.config import CONFIGS, Config
from securerag.defenses import build_defenses
from securerag.eval.scoring import is_correct
from securerag.llm.budget import DailyBudgetExhausted
from securerag.llm.client import LLMClient
from securerag.llm.meta import update_run_meta
from securerag.rag.embed import SentenceTransformerEmbedder
from securerag.rag.kb import build_store
from securerag.rag.pipeline import Pipeline, Trace
from securerag.rag.store import VectorStore

RUNS_DIR = Path("results/runs")
EXIT_BUDGET = 75
MAX_CONSECUTIVE_ERRORS = 5
SUBSET_CLEAN, SUBSET_PER_ATTACK = 30, 10  # the repeat and confirmation runs (70 queries)


def select_items(
    questions: list[dict], attacks: list[Attack], mode: str, seed: int, limit: int | None = None
) -> tuple[list[dict], list[Attack]]:
    """`full` uses everything; `repeat` and `confirm` use the fixed 70-query subset."""
    if mode == "full":
        clean, atk = list(questions), list(attacks)
    else:
        rng = random.Random(seed)
        clean = rng.sample(sorted(questions, key=lambda q: q["id"]), SUBSET_CLEAN)
        atk = [
            a
            for kind in sorted({a.kind for a in attacks})
            for a in rng.sample([x for x in attacks if x.kind == kind], SUBSET_PER_ATTACK)
        ]
    if limit:
        kinds = sorted({a.kind for a in atk})
        clean = clean[:limit]
        atk = [a for k in kinds for a in [x for x in atk if x.kind == k][:limit]]
    return clean, atk


def record_from(
    config: str, item_id: str, kind: str, channel: str, repeat: int, trace: Trace, outcome: bool
) -> dict:
    base = {
        "config": config, "item_id": item_id, "kind": kind, "channel": channel, "repeat": repeat,
        "answer": trace.answer, "blocked": trace.blocked, "fired": sorted(trace.fired),
        "llm_calls": trace.llm_calls, "guard_calls": trace.guard_calls,
        "latency_s": round(trace.latency_s, 3),
    }  # fmt: skip
    return {**base, "correct" if kind == "clean" else "success": outcome}


def load_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def _item_id(what: str, item) -> str:
    return item["id"] if what == "clean" else item.id


def _one(pipe: Pipeline, name: str, what: str, item, repeat: int) -> dict:
    if what == "clean":
        trace = pipe.ask(item["question"], repeat=repeat)
        return record_from(
            name, item["id"], "clean", "", repeat, trace, is_correct(trace.answer, item)
        )
    trace, ok = run_attack(pipe, item, repeat=repeat)
    return record_from(name, item.id, item.kind, item.channel, repeat, trace, ok)


def run(
    store: VectorStore,
    llm: LLMClient,
    guard: LLMClient | None,
    questions: list[dict],
    attacks: list[Attack],
    configs: list[str],
    out_path: Path,
    repeat: int = 0,
    base_cfg: Config | None = None,
    log=print,
) -> int:
    """Returns the number of new records written. Raises DailyBudgetExhausted when paused."""
    base_cfg = base_cfg or Config()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = {(r["config"], r["item_id"]) for r in load_records(out_path)}
    written = errors = 0
    with out_path.open("a", encoding="utf-8") as f:
        for name in configs:
            cfg = base_cfg.with_defenses(*CONFIGS[name])
            pipe = Pipeline(store, llm, cfg, build_defenses(cfg, guard))
            todo = [("clean", q) for q in questions if (name, q["id"]) not in done]
            todo += [("attack", a) for a in attacks if (name, a.id) not in done]
            log(f"[{name}] {len(todo)} to do")
            for what, item in todo:
                try:
                    rec = _one(pipe, name, what, item, repeat)
                except DailyBudgetExhausted:
                    raise
                except Exception as e:  # a network or parsing hiccup: skip now, retry on resume
                    errors += 1
                    log(f"  error on {name}/{_item_id(what, item)}: {e!r}")
                    if errors >= MAX_CONSECUTIVE_ERRORS:
                        raise RuntimeError(f"{errors} errors in a row; last: {e!r}") from e
                    continue
                errors = 0
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                f.flush()
                written += 1
    return written


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", choices=["full", "repeat", "confirm"], default="full")
    ap.add_argument("--repeat", type=int, default=0, help="repeat index (repeat mode: 1, 2, 3)")
    ap.add_argument("--configs", nargs="*", default=list(CONFIGS), choices=list(CONFIGS))
    ap.add_argument("--limit", type=int, help="items per kind, for a quick trial")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args(argv)

    from securerag.config import load_env
    from securerag.llm.gemini import gemini_client
    from securerag.llm.groq import groq_client, guard_client

    load_env()

    cfg = Config()
    data = Path("data")
    questions = load_jsonl(data / "questions.jsonl")
    attacks = load_attacks(data / "attacks.jsonl")
    clean, atk = select_items(questions, attacks, args.mode, cfg.seed, args.limit)
    suffix = f"_r{args.repeat}" if args.mode == "repeat" else ""
    answer_llm = gemini_client(cfg) if args.mode == "confirm" else groq_client(cfg)
    out = args.out or RUNS_DIR / f"{args.mode}{suffix}.jsonl"

    store = build_store(
        SentenceTransformerEmbedder(cfg.embedding_model), data, data / "embeddings.npz"
    )
    update_run_meta(
        **{
            f"eval_{args.mode}": {
                "model": cfg.gemini_model if args.mode == "confirm" else cfg.groq_model,
                "reasoning_effort": cfg.reasoning_effort,
                "temperature": cfg.temperature, "seed": cfg.seed, "top_k": cfg.top_k,
                "guard_model": cfg.prompt_guard_model, "embedding_model": cfg.embedding_model,
                "configs": args.configs, "repeat": args.repeat,
                "queries": {"clean": len(clean), "attacks": len(atk)},
            }
        }
    )  # fmt: skip
    try:
        n = run(store, answer_llm, guard_client(cfg), clean, atk, args.configs, out,
                args.repeat, cfg)  # fmt: skip
    except DailyBudgetExhausted as e:
        print(f"Paused: {e}. Run the same command again after 00:00 UTC.")
        return EXIT_BUDGET
    print(f"Finished: {n} new records in {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
