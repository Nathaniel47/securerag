import json

import pytest

from securerag.attacks.base import Attack
from securerag.config import Config
from securerag.eval.metrics import summarize, wilson
from securerag.eval.run_eval import load_records, run, select_items
from securerag.eval.scoring import is_correct
from securerag.llm.budget import DailyBudgetExhausted
from securerag.llm.cache import ResponseCache
from securerag.llm.client import LLMClient
from securerag.rag.embed import HashEmbedder
from securerag.rag.store import VectorStore


def test_is_correct_matches_content_words_in_any_order():
    q = {"answer": "8,877 (0.08%)"}
    assert is_correct("He received 8,877 votes (0.08%).", q)
    assert not is_correct("He received 9,000 votes.", q)
    assert is_correct("Prayer camps", {"answer": "Prayer camps"})
    assert not is_correct("I don't know.", {"answer": "the Land Act"})
    alias = {"answer": "80%", "aliases": ["Eighty percent"]}
    assert is_correct("Eighty percent of land.", alias) and is_correct("About 80%.", alias)


def test_wilson_interval_behaviour():
    lo, hi = wilson(0, 25)
    assert lo == 0.0 and 0.1 < hi < 0.2
    lo, hi = wilson(25, 25)
    assert hi == 1.0 and 0.8 < lo < 1.0
    assert wilson(0, 0) == (0.0, 1.0)
    lo, hi = wilson(50, 100)
    assert lo < 0.5 < hi


def rec(config, kind, ok, blocked=False, fired=(), calls=1):
    base = {
        "config": config,
        "kind": kind,
        "blocked": blocked,
        "fired": list(fired),
        "llm_calls": calls,
        "guard_calls": 0,
    }
    return {**base, "correct" if kind == "clean" else "success": ok}


def test_summarize_rates_and_costs():
    rows = [
        rec("none", "clean", True),
        rec("none", "clean", False),
        rec("none", "poisoning", True),
        rec("none", "leakage", False),
        rec("d3", "clean", True, blocked=True, fired=["d3_consistency"], calls=2),
        rec("d3", "clean", True, fired=["d3_consistency"], calls=2),
        rec("d3", "leakage", False, calls=2),
    ]
    s = summarize(rows)
    assert s["none"]["accuracy"]["rate"] == 0.5 and s["none"]["asr_all"]["rate"] == 0.5
    assert s["none"]["asr"]["poisoning"]["k"] == 1
    assert s["d3"]["false_block"]["k"] == 1 and s["d3"]["false_flag"]["k"] == 2
    assert s["d3"]["calls_per_query"] == 2.0


def _qs(n):
    return [{"id": f"q{i:03d}", "question": f"Q{i}?", "answer": f"A{i}"} for i in range(n)]


def _attacks():
    return [Attack(f"{k}-{i}", k, "q", ("X",)) for k in ("poisoning", "leakage") for i in range(12)]


def test_select_items_modes_are_fixed_by_seed():
    qs, atk = _qs(60), _attacks()
    c, a = select_items(qs, atk, "full", 42)
    assert (len(c), len(a)) == (60, 24)
    c1, a1 = select_items(qs, atk, "repeat", 42)
    c2, a2 = select_items(qs, atk, "confirm", 42)
    assert (len(c1), len(a1)) == (30, 20) and c1 == c2 and a1 == a2
    c3, a3 = select_items(qs, atk, "full", 42, limit=2)
    assert (len(c3), len(a3)) == (2, 4)


def _runner(tmp_path, reply):
    store = VectorStore(HashEmbedder())
    store.add(
        [
            {
                "chunk_id": "a#0",
                "doc_id": "a",
                "source": "s",
                "title": "T",
                "text": "A0 is the answer to Q0",
                "trust": "official",
                "role": "public",
            }
        ]
    )

    def backend(model, messages, temperature, seed, settings):
        return reply(), 10

    return store, LLMClient(backend, "fake", 0.3, 42, cache=ResponseCache(tmp_path / "cache"))


def test_run_writes_records_and_resumes_without_repeating_work(tmp_path):
    store, llm = _runner(tmp_path, lambda: "A0")
    out = tmp_path / "runs" / "full.jsonl"
    qs, atk = _qs(3), [Attack("poisoning-0", "poisoning", "Q0?", ("A9",))]
    n = run(store, llm, None, qs, atk, ["none", "d1"], out, log=lambda *_: None)
    assert n == 8
    recs = load_records(out)
    assert len(recs) == 8 and {r["config"] for r in recs} == {"none", "d1"}
    assert sum(r["correct"] for r in recs if r["kind"] == "clean" and r["config"] == "none") == 1
    assert run(store, llm, None, qs, atk, ["none", "d1"], out, log=lambda *_: None) == 0
    assert json.loads(out.read_text().splitlines()[0])["answer"] == "A0"


def test_run_pauses_on_budget_and_keeps_progress(tmp_path):
    store, llm = _runner(tmp_path, lambda: "A0")
    calls = {"n": 0}
    real = llm.backend

    def limited(*args):
        calls["n"] += 1
        if calls["n"] > 2:
            raise DailyBudgetExhausted("out of tokens")
        return real(*args)

    llm.backend = limited
    out = tmp_path / "full.jsonl"
    with pytest.raises(DailyBudgetExhausted):
        run(store, llm, None, _qs(5), [], ["none"], out, log=lambda *_: None)
    assert len(load_records(out)) == 2  # what was answered before the pause is kept
    llm.backend = real
    assert run(store, llm, None, _qs(5), [], ["none"], out, log=lambda *_: None) == 3


def test_run_skips_failing_items_and_aborts_after_repeated_errors(tmp_path):
    store, llm = _runner(tmp_path, lambda: "A0")

    def boom(*args):
        raise ConnectionError("network down")

    llm.backend = boom
    out = tmp_path / "full.jsonl"
    with pytest.raises(RuntimeError, match="errors in a row"):
        run(store, llm, None, _qs(10), [], ["none"], out, log=lambda *_: None)
    assert not load_records(out)


def test_default_config_is_used_for_records(tmp_path):
    store, llm = _runner(tmp_path, lambda: "A0")
    out = tmp_path / "f.jsonl"
    run(store, llm, None, _qs(1), [], ["d4"], out, base_cfg=Config(), log=lambda *_: None)
    assert load_records(out)[0]["config"] == "d4"


def test_validation_sample_is_seeded_and_blank_for_the_human():
    from securerag.eval.validate_scorer import sample_rows

    qs = _qs(40)
    recs = [
        {"config": "none", "kind": "clean", "item_id": q["id"], "answer": "A", "correct": True}
        for q in qs
    ]
    rows = sample_rows(recs, qs, 42)
    assert len(rows) == 30 and rows == sample_rows(recs, qs, 42)
    assert {r["human_verdict"] for r in rows} == {""}
