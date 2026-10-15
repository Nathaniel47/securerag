"""Generate the clean question set from the question-source pages, with automatic checks.

Run (needs SECURERAG_GROQ_API_KEY):  python -m securerag.eval.questions
Output: data/questions.jsonl. Every item must still be hand-checked (PLAN.md week 2).
"""

import argparse
import json
import random
import re
from pathlib import Path

from securerag.config import Config
from securerag.llm.client import LLMClient

TARGET = 150
MAX_ANSWER_WORDS = 8

SYSTEM = "You write exam questions from a passage. Reply with JSON only."
PROMPT = """Passage (from the Wikipedia article "{title}"):
\"\"\"
{text}
\"\"\"

Write {n} different factual questions that this passage answers on its own, without needing the
article title. Each answer must be a short phrase of at most {max_words} words copied exactly
from the passage (a name, number, date, place or term). Reply as a JSON list:
[{{"question": "...", "answer": "..."}}]"""


def norm_words(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", text.lower()).split())


def parse_items(reply: str) -> list[dict]:
    match = re.search(r"\[.*\]", reply, re.S)
    if not match:
        return []
    try:
        items = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    return [
        {"question": i["question"].strip(), "answer": i["answer"].strip()}
        for i in items
        if isinstance(i, dict)
        and isinstance(i.get("question"), str)
        and isinstance(i.get("answer"), str)
    ]


def is_valid(item: dict, passage: str) -> bool:
    """Automatic gates: short, grounded in the passage, a real question, not leaking the answer."""
    q, a = item["question"], item["answer"]
    if not q.endswith("?") or not a or len(a.split()) > MAX_ANSWER_WORDS:
        return False
    if norm_words(a) not in norm_words(passage):
        return False
    return norm_words(a) not in norm_words(q)


def generate(
    client: LLMClient, chunks_path: Path, splits_path: Path, out_path: Path, seed: int
) -> list[dict]:
    splits = json.loads(splits_path.read_text(encoding="utf-8"))
    source = set(splits["question_source"])
    by_doc: dict[str, list[dict]] = {}
    for line in chunks_path.read_text(encoding="utf-8").splitlines():
        c = json.loads(line)
        if c["doc_id"] in source and c["trust"] == "official" and len(c["text"].split()) >= 80:
            by_doc.setdefault(c["doc_id"], []).append(c)
    rng = random.Random(seed)
    docs = sorted(by_doc)
    rng.shuffle(docs)
    questions: list[dict] = []
    seen_q: set[str] = set()
    # Round 1 takes one chunk per page; later rounds take further random chunks until full.
    for _round in range(5):
        for doc in docs:
            if len(questions) >= TARGET:
                break
            chunk = rng.choice(by_doc[doc])
            reply = client.complete(
                PROMPT.format(
                    title=chunk["title"], text=chunk["text"], n=2, max_words=MAX_ANSWER_WORDS
                ),
                system=SYSTEM,
                repeat=_round,
            )
            for item in parse_items(reply):
                if len(questions) >= TARGET or item["question"] in seen_q:
                    continue
                if is_valid(item, chunk["text"]):
                    seen_q.add(item["question"])
                    questions.append(
                        {
                            "id": f"q{len(questions):03d}",
                            **item,
                            "doc_id": doc,
                            "chunk_id": chunk["chunk_id"],
                            "source": chunk["source"],
                            "hand_checked": False,
                        }
                    )
    out_path.write_text(
        "".join(json.dumps(q, ensure_ascii=False) + "\n" for q in questions), encoding="utf-8"
    )
    return questions


if __name__ == "__main__":
    from securerag.llm.groq import groq_client

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", type=Path, default=Path("data"))
    args = ap.parse_args()
    qs = generate(
        groq_client(),
        args.data / "chunks.jsonl",
        args.data / "splits.json",
        args.data / "questions.jsonl",
        Config().seed,
    )
    print(f"generated {len(qs)} questions")
