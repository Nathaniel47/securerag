import json

from securerag.eval.questions import generate, is_valid, parse_items
from securerag.llm.cache import ResponseCache
from securerag.llm.client import LLMClient


def make_client(tmp_path, replies):
    calls = []

    def backend(model, messages, temperature, seed):
        calls.append(messages)
        return replies(len(calls))

    return LLMClient(backend, "m", 0.3, 42, ResponseCache(tmp_path / "c")), calls


def test_cache_hit_avoids_second_call(tmp_path):
    client, calls = make_client(tmp_path, lambda n: f"reply {n}")
    assert client.complete("hi") == client.complete("hi") == "reply 1"
    assert len(calls) == 1 and client.cache_hits == 1


def test_repeat_index_gives_independent_samples(tmp_path):
    client, calls = make_client(tmp_path, lambda n: f"reply {n}")
    assert client.complete("hi", repeat=0) != client.complete("hi", repeat=1)
    assert len(calls) == 2


def test_cache_survives_new_client(tmp_path):
    c1, _ = make_client(tmp_path, lambda n: "a")
    c1.complete("hi")
    c2, calls = make_client(tmp_path, lambda n: "b")
    assert c2.complete("hi") == "a" and not calls


def test_parse_items_handles_noise():
    reply = 'Sure!\n[{"question": "Q?", "answer": "A"}, {"bad": 1}]'
    assert parse_items(reply) == [{"question": "Q?", "answer": "A"}]
    assert parse_items("no json") == [] and parse_items("[oops") == []


def test_is_valid_gates():
    passage = "Accra is the capital of Ghana and lies on the coast."
    assert is_valid({"question": "What is the capital of Ghana?", "answer": "Accra"}, passage)
    assert not is_valid({"question": "Capital of Ghana", "answer": "Accra"}, passage)  # no ?
    assert not is_valid({"question": "Who is Kumasi?", "answer": "Kumasi"}, passage)  # not in text
    assert not is_valid({"question": "Is Accra Accra?", "answer": "Accra"}, passage)  # leaks
    assert not is_valid({"question": "Where?", "answer": "w " * 9}, passage)  # too long


def test_generate_is_reproducible_and_grounded(tmp_path):
    text = "Kumasi is the capital of the Ashanti Region of Ghana. " * 12
    chunks = [
        {"chunk_id": f"/d{i}#0", "doc_id": f"/d{i}", "source": "s", "title": "T", "text": text,
         "trust": "official", "role": "public"}
        for i in range(5)
    ]  # fmt: skip
    (tmp_path / "chunks.jsonl").write_text("".join(json.dumps(c) + "\n" for c in chunks))
    (tmp_path / "splits.json").write_text(
        json.dumps({"question_source": [c["doc_id"] for c in chunks], "other": []})
    )
    reply = json.dumps(
        [{"question": "Which region is Kumasi the capital of?", "answer": "Ashanti Region"}]
    )
    outs = []
    for sub in ("a", "b"):
        client, _ = make_client(tmp_path / sub, lambda n: reply)
        qs = generate(
            client,
            tmp_path / "chunks.jsonl",
            tmp_path / "splits.json",
            tmp_path / f"{sub}.jsonl",
            1,
        )
        outs.append(qs)
    assert outs[0] == outs[1] and len(outs[0]) == 1  # duplicate questions are dropped
    assert outs[0][0]["hand_checked"] is False
