"""Merge the hand-reviewed question CSV into data/questions.jsonl.

Run: python -m securerag.eval.apply_review
Verification flags: spot_checked (owner re-read the row), llm_verified (checked against the source
chunk by the assistant only), hand_checked (every row read by the owner; none yet).
"""

import csv
import json
import re
from pathlib import Path

from securerag.eval.questions import evidence_sentence

OVERRIDE_ANSWERS = {"q154": "GHS 3.377 billion"}
# Other accepted forms where the reviewed answer is not the wording the source uses.
ALIASES = {"q082": ["Eighty percent", "80 percent"]}
# Removed after review: q057 has two valid answers, q083 is superseded by the Land Act 2020,
# q068 is about Bolivia (its chunk never mentions Ghana), q035 asks about a "current" position.
DROPPED = {"q035", "q057", "q068", "q083"}
REPLACEMENTS = [
    ("q160", "In what year was the Ghana Standards Authority, then a Board, set up?", "1973",
     "/wiki/Ghana_Standards_Authority#0"),
    ("q161", "On what date was the Ghana CARES programme launched in Accra?", "18 November 2020",
     "/wiki/Ghana_CARES#0"),
    ("q162", "Who founded the Black Star International Film Festival in Ghana?", "Juliet Asante",
     "/wiki/Black_Star_International_Film_Festival#0"),
    ("q163", "On what date was the Petroleum Revenue Management Act 2011 (Act 815) approved by "
     "Ghana's President?", "11 April 2011", "/wiki/Ghana_Petroleum_Funds#0"),
]  # fmt: skip


def spot_check_ids(summary: Path) -> set[str]:
    text = summary.read_text(encoding="utf-8").split("## Spot-check list", 1)[1]
    return set(re.findall(r"^\| (q\d{3}) \|", text, re.M))


def apply(root: Path = Path(".")) -> list[dict]:
    chunks = {}
    for line in (root / "data/chunks.jsonl").read_text(encoding="utf-8").splitlines():
        c = json.loads(line)
        chunks[c["chunk_id"]] = c
    old = {}
    for line in (root / "data/questions.jsonl").read_text(encoding="utf-8").splitlines():
        q = json.loads(line)
        old[q["id"]] = q
    with (root / "results/questions_review_reviewed.csv").open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    spot = spot_check_ids(root / "results/question_review_summary.md")

    out: dict[str, dict] = {}
    for r in rows:
        qid = r["id"]
        if r["keep (y/n)"] != "y" or qid in DROPPED:
            continue
        # Replacements q150+ are not in the old file, so the chunk comes from the review notes.
        if qid in old:
            chunk_id = old[qid]["chunk_id"]
        else:
            chunk_id = re.search(r"chunk (\S+?#\d+)", r["notes"]).group(1)
        question = r["corrected_question"] or r["question"]
        answer = OVERRIDE_ANSWERS.get(qid) or r["corrected_answer"] or r["reference_answer"]
        out[qid] = _item(qid, question, answer, chunks[chunk_id], qid in spot)
    for qid, question, answer, chunk_id in REPLACEMENTS:
        out[qid] = _item(qid, question, answer, chunks[chunk_id], False)
    for q in out.values():
        assert q["evidence"], f"{q['id']}: answer not found in its chunk"
        assert not re.search(r"\bcurrent(ly)?\b", q["question"].lower()), q["id"]
    items = [out[k] for k in sorted(out)]
    (root / "data/questions.jsonl").write_text(
        "".join(json.dumps(q, ensure_ascii=False) + "\n" for q in items), encoding="utf-8"
    )
    return items


def _evidence(text: str, forms: list[str], question: str) -> str:
    return next((e for f in forms if (e := evidence_sentence(text, f, question))), "")


def _item(qid: str, question: str, answer: str, chunk: dict, spot: bool) -> dict:
    return {
        "id": qid,
        "question": question,
        "answer": answer,
        **({"aliases": ALIASES[qid]} if qid in ALIASES else {}),
        "doc_id": chunk["doc_id"],
        "chunk_id": chunk["chunk_id"],
        "source": chunk["source"],
        "evidence": _evidence(chunk["text"], [answer, *ALIASES.get(qid, [])], question),
        "spot_checked": spot,
        "llm_verified": not spot,
        "hand_checked": False,
    }


if __name__ == "__main__":
    items = apply()
    print(
        f"{len(items)} questions, {sum(q['spot_checked'] for q in items)} spot_checked, "
        f"{sum(q['llm_verified'] for q in items)} llm_verified"
    )
