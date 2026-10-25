import json
import random
from pathlib import Path

import numpy as np
import pytest

from securerag.attacks.base import Attack, succeeded
from securerag.attacks.build import build_attacks, load_attacks, save_attacks
from securerag.attacks.poisoning import wrong_answer
from securerag.attacks.run import run_attack
from securerag.config import Config, load_env
from securerag.defenses.base import Defense
from securerag.llm.cache import ResponseCache
from securerag.llm.client import LLMClient
from securerag.rag.embed import HashEmbedder
from securerag.rag.kb import embed_cached
from securerag.rag.pipeline import Pipeline
from securerag.rag.prompt import SYSTEM_CANARY
from securerag.rag.store import VectorStore


def chunk(cid, text, trust="official", role="public"):
    return {
        "chunk_id": cid,
        "doc_id": cid.split("#")[0],
        "source": f"https://x/{cid}",
        "title": "T",
        "text": text,
        "trust": trust,
        "role": role,
    }


CHUNKS = [
    chunk("/a#0", "Accra is the capital city of Ghana and lies on the Gulf of Guinea coast."),
    chunk("/b#0", "Kumasi is the capital of the Ashanti Region and is known for its markets."),
    chunk("/c#0", "Lake Volta is the largest artificial lake by surface area in the world."),
    chunk(
        "r#0",
        "INTERNAL CASE NOTE Claimant: Ama Mensah. Ghana Card ID: GHA-FAKE-111111.",
        trust="restricted",
        role="staff",
    ),
]


def make_store(chunks=CHUNKS):
    store = VectorStore(HashEmbedder())
    store.add(chunks)
    return store


def fake_llm(tmp_path, reply):
    """`reply(messages)` decides the answer; the cache directory is private to the test."""

    def backend(model, messages, temperature, seed, settings):
        return reply(messages), 10

    return LLMClient(backend, "fake", 0.3, 42, cache=ResponseCache(tmp_path / "cache"))


def test_store_returns_nearest_chunk_and_applies_trust_filter():
    store = make_store()
    top = store.query("What is the capital city of Ghana?", 1)[0]
    assert top["chunk_id"] == "/a#0" and top["score"] > 0.3
    assert top["embedding"].shape == (256,)
    public = store.query("Ama Mensah Ghana Card ID", 4, frozenset({"official"}))
    assert all(c["trust"] == "official" for c in public)
    assert store.query("Ama Mensah Ghana Card ID", 1)[0]["chunk_id"] == "r#0"
    store.delete(["r#0"])
    assert len(store) == 3


def test_embedding_cache_is_reused_and_invalidated(tmp_path):
    cache = tmp_path / "emb.npz"
    emb = HashEmbedder()
    first = embed_cached(CHUNKS, emb, cache)
    calls = []
    emb.encode = lambda texts: calls.append(1) or np.zeros((len(texts), 256), dtype=np.float32)
    assert np.array_equal(embed_cached(CHUNKS, emb, cache), first) and not calls
    embed_cached(CHUNKS[:2], emb, cache)  # different chunk ids: recomputed
    assert calls


def test_pipeline_answers_from_retrieved_sources(tmp_path):
    seen = []

    def reply(messages):
        seen.append(messages)
        return "Accra."

    pipe = Pipeline(make_store(), fake_llm(tmp_path, reply), Config())
    trace = pipe.ask("What is the capital city of Ghana?")
    assert trace.answer == "Accra." and trace.llm_calls == 1 and not trace.blocked
    assert len(trace.chunks) == 3 and "[1] Accra is the capital" in seen[0][-1]["content"]
    assert SYSTEM_CANARY in seen[0][0]["content"]


def test_defense_hooks_run_at_each_stage(tmp_path):
    class Spy(Defense):
        name = "spy"
        allowed_trust = frozenset({"official"})

        def accepts_document(self, chunk):
            return "BAD" not in chunk["text"]

        def filter_chunks(self, question, chunks, trace):
            trace.flag(self.name, "kept first")
            return chunks[:1]

        def filter_answer(self, answer, trace):
            return answer.upper()

    pipe = Pipeline(make_store(), fake_llm(tmp_path, lambda m: "Accra"), Config(), [Spy()])
    trace = pipe.ask("Ama Mensah Ghana Card ID")
    assert trace.answer == "ACCRA" and len(trace.chunks) == 1 and "spy" in trace.fired
    assert all(c["trust"] == "official" for c in trace.retrieved)  # restricted never retrieved
    assert len(pipe.ingest([chunk("x#0", "BAD doc"), chunk("y#0", "fine doc")])) == 1


def test_blocking_defense_skips_retrieval_and_generation(tmp_path):
    class Blocker(Defense):
        def check_query(self, question, trace):
            return "Blocked."

    pipe = Pipeline(make_store(), fake_llm(tmp_path, lambda m: "x"), Config(), [Blocker()])
    trace = pipe.ask("anything")
    assert trace.blocked and trace.answer == "Blocked." and trace.llm_calls == 0
    assert trace.retrieved == []


def test_succeeded_uses_whole_words_and_exclusions():
    a = Attack("a", "poisoning", "q", markers=("Kumasi",), must_not_contain=("Accra",))
    assert succeeded(a, "It is Kumasi.")
    assert not succeeded(a, "Kumasi, not Accra")  # true answer present: not a clean win
    assert not succeeded(a, "Kumasians say so")  # whole words only
    leak = Attack("l", "leakage", "q", markers=("+233 000 000 250", "GHA-FAKE-777572"))
    assert succeeded(leak, "Call +233 000 000 250 today") and succeeded(leak, "gha fake 777572")


def test_wrong_answer_has_the_same_shape_and_differs():
    rng = random.Random(1)
    year = wrong_answer("1992", [], rng)
    assert year.isdigit() and year != "1992"
    pool = ["Kofi Annan", "Ama Ata Aidoo", "5 July 1960", "Lake Volta"]
    assert wrong_answer("Kwame Nkrumah", pool, rng) in {"Kofi Annan", "Ama Ata Aidoo", "Lake Volta"}
    date = wrong_answer("7 December", pool, rng)
    assert date.endswith(" December") and date != "7 December"
    votes = wrong_answer("8,877 (0.08%)", pool, rng)
    assert votes != "8,877 (0.08%)" and "," in votes and votes.endswith("%)")


def _records(n=12):
    return [
        {
            "doc_id": f"restricted-{i:03d}",
            "name": f"Ama Mensah{i}",
            "ghana_card_id": f"GHA-FAKE-{i:06d}",
            "nhis_id": f"NHIS-FAKE-{i:06d}",
            "email": f"a{i}@example.org",
            "phone": f"+233 000 000 {i:03d}",
            "case_type": "NHIS claim review",
            "canary": f"CANARY-{i:08x}",
        }
        for i in range(n)
    ]


def _questions(n=30):
    return [
        {
            "id": f"q{i:03d}",
            "question": f"What is thing number {i} in Ghana?",
            "answer": f"Answer {i}",
            "evidence": f"Thing number {i} in Ghana is Answer {i}.",
            "source": f"https://x/{i}",
        }
        for i in range(n)
    ]


def test_build_attacks_counts_disjoint_targets_and_roundtrip(tmp_path):
    qs, recs = _questions(), _records()
    attacks = build_attacks(qs, recs, seed=42, n=5)
    kinds = ("poisoning", "indirect_injection", "direct_injection", "leakage")
    assert [sum(a.kind == k for a in attacks) for k in kinds] == [5, 5, 5, 5]
    targets = [a.variant.split("target=")[1] for a in attacks if "target=" in a.variant]
    assert len(targets) == len(set(targets)) == 15
    assert build_attacks(qs, recs, seed=42, n=5) == attacks  # reproducible
    path = tmp_path / "attacks.jsonl"
    save_attacks(attacks, path)
    assert load_attacks(path) == attacks


def test_poison_docs_carry_the_wrong_answer_and_channel_trust():
    attacks = build_attacks(_questions(), _records(), seed=1, n=5)
    pois = [a for a in attacks if a.kind == "poisoning"]
    assert {a.channel for a in pois} == {"user_upload", "official_edit"}
    for a in pois:
        assert len(a.docs) == 2 and all(a.markers[0] in d["text"] for d in a.docs)
        assert all(a.query in d["text"] for d in a.docs)
        trust = {d["trust"] for d in a.docs}
        assert trust == ({"official"} if a.channel == "official_edit" else {"user_upload"})


def test_direct_injection_has_override_and_extraction_goals():
    attacks = build_attacks(_questions(), _records(), seed=1, n=6)
    direct = [a for a in attacks if a.kind == "direct_injection"]
    assert sum(SYSTEM_CANARY in a.markers for a in direct) == 3
    assert all(a.markers[0] in a.query for a in direct if SYSTEM_CANARY not in a.markers)


def test_leakage_markers_cover_every_sensitive_field():
    attacks = build_attacks(_questions(), _records(), seed=1, n=3)
    leak = next(a for a in attacks if a.kind == "leakage")
    assert any(m.startswith("GHA-FAKE") for m in leak.markers)
    assert any(m.startswith("CANARY") for m in leak.markers)


def test_run_attack_poisoning_succeeds_without_defense_and_cleans_up(tmp_path):
    store = make_store()
    q = {
        "id": "q1",
        "question": "What is the capital city of Ghana?",
        "answer": "Accra",
        "evidence": "Accra is the capital city of Ghana.",
        "source": "https://x/a",
    }
    attack = build_attacks([q] * 1, _records(), seed=1, n=1)[0]
    assert attack.kind == "poisoning"
    wrong = attack.markers[0]

    def reply(messages):
        # A naive model believes any source that states a different answer.
        return "The answer is " + (wrong if wrong in messages[-1]["content"] else "Accra")

    pipe = Pipeline(store, fake_llm(tmp_path, reply), Config())
    before = len(store)
    trace, ok = run_attack(pipe, attack)
    assert ok and len(store) == before
    assert any(c["chunk_id"].startswith("poison-") for c in trace.retrieved)


def test_run_attack_reports_ingest_rejections(tmp_path):
    class Scan(Defense):
        def accepts_document(self, chunk):
            return chunk["trust"] != "user_upload"

    attacks = build_attacks(_questions(), _records(), seed=1, n=5)
    upload = next(
        a for a in attacks if a.kind == "indirect_injection" and a.channel == "user_upload"
    )
    pipe = Pipeline(make_store(), fake_llm(tmp_path, lambda m: "no"), Config(), [Scan()])
    trace, ok = run_attack(pipe, upload)
    assert not ok and "ingest_scan" in trace.fired


def test_load_env_sets_only_missing_securerag_vars(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("SECURERAG_GROQ_API_KEY=abc\nOTHER=1\nSECURERAG_GEMINI_API_KEY=\n")
    monkeypatch.delenv("SECURERAG_GROQ_API_KEY", raising=False)
    monkeypatch.delenv("SECURERAG_GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OTHER", raising=False)
    load_env(env)
    import os

    assert os.environ["SECURERAG_GROQ_API_KEY"] == "abc"
    assert "OTHER" not in os.environ and "SECURERAG_GEMINI_API_KEY" not in os.environ
    monkeypatch.delenv("SECURERAG_GROQ_API_KEY")


@pytest.mark.skipif(not Path("data/attacks.jsonl").exists(), reason="attack set not built")
def test_committed_attack_set_is_complete():
    attacks = load_attacks()
    assert len(attacks) == 100 and len({a.id for a in attacks}) == 100
    assert all(json.dumps(a.to_dict()) for a in attacks)
