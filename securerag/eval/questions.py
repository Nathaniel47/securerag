"""Generate the clean question set from the question-source pages, with automatic checks.

Run (needs SECURERAG_GROQ_API_KEY):  python -m securerag.eval.questions
Output: data/questions.jsonl. Every item must still be hand-checked (PLAN.md week 2).
"""

import argparse
import csv
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
    if re.search(r"\b(passage|article|text|excerpt)\b", q.lower()):
        return False  # questions must stand alone, because retrieval will not show the passage
    if re.search(r"\bcurrent(ly)?\b", q.lower()):
        return False  # the answer is only true on the article's revision date
    return norm_words(a) not in norm_words(q)


STOPWORDS = frozenset(
    "a an the of in on at to for by and or is was were are be been what which who whom whose when "
    "where how many much did does do from with as that this it its his her their".split()
)


def evidence_sentence(passage: str, answer: str, question: str = "") -> str:
    """The sentence containing the answer that shares the most words with the question, so a
    reviewer can verify it at a glance. Ties go to the earliest sentence."""
    target = norm_words(answer)
    wanted = set(norm_words(question).split()) - STOPWORDS
    best, best_overlap = "", -1
    # The lookbehind keeps initials such as "G. E. K. Aikins" inside one sentence.
    for sent in re.split(r"(?<=[.!?])(?<!\s[A-Z]\.)\s+|\n+", passage):
        if target not in norm_words(sent):
            continue
        overlap = len(wanted & set(norm_words(sent).split()))
        if overlap > best_overlap:
            best, best_overlap = sent.strip(), overlap
    return best


def auto_flags(q: dict) -> str:
    """Hints for the reviewer: questions that may be ambiguous without their source page."""
    flags = []
    if not q["evidence"]:
        flags.append("no_evidence_sentence")
    if not re.search(r"[A-Z0-9]", q["question"][1:]):
        flags.append("no_named_entity")
    if re.search(
        r"\b(the school|the party|the candidate|this|that|the company)\b", q["question"].lower()
    ):
        flags.append("vague_reference")
    return ";".join(flags)


REVIEW_COLUMNS = (
    "id", "question", "reference_answer", "evidence_sentence", "source_url", "auto_flags",
    "keep (y/n)", "corrected_question", "corrected_answer", "notes",
)  # fmt: skip


def export_review_csv(questions: list[dict], path: Path) -> None:
    """Spreadsheet for the hand-check; utf-8 with BOM so Excel shows accents correctly."""
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(REVIEW_COLUMNS)
        for q in questions:
            w.writerow(
                [
                    q["id"],
                    q["question"],
                    q["answer"],
                    q["evidence"],
                    q["source"],
                    auto_flags(q),
                    "",
                    "",
                    "",
                    "",
                ]
            )


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
                            "evidence": evidence_sentence(
                                chunk["text"], item["answer"], item["question"]
                            ),
                            "hand_checked": False,
                        }
                    )
    out_path.write_text(
        "".join(json.dumps(q, ensure_ascii=False) + "\n" for q in questions), encoding="utf-8"
    )
    return questions


if __name__ == "__main__":
    from securerag.config import load_env
    from securerag.llm.groq import groq_client

    load_env()

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
    export_review_csv(qs, Path("results/questions_review.csv"))
    print(f"generated {len(qs)} questions")
