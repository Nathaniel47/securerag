import csv
import json

from securerag.eval.apply_review import REPLACEMENTS, apply, spot_check_ids
from securerag.eval.questions import REVIEW_COLUMNS

CHUNK_TEXT = (
    "The founders include Kofi Mensah. Kofi Mensah was the treasurer in 2010 of the council."
)


def _setup(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "results").mkdir()
    chunks = [
        {"chunk_id": "/a#0", "doc_id": "/a", "source": "https://x/a", "title": "T",
         "text": CHUNK_TEXT, "trust": "official", "role": "public"},
        {"chunk_id": REPLACEMENTS[0][3], "doc_id": "/b", "source": "https://x/b", "title": "T",
         "text": "The Ghana Standards Authority then a Board, was set up in 1973 by decree.",
         "trust": "official", "role": "public"},
    ]  # fmt: skip
    (tmp_path / "data/chunks.jsonl").write_text("".join(json.dumps(c) + "\n" for c in chunks))
    old = {
        "id": "q000",
        "question": "Who was the treasurer in 2010?",
        "answer": "Kofi Mensah",
        "chunk_id": "/a#0",
        "doc_id": "/a",
        "source": "s",
        "evidence": "",
        "hand_checked": False,
    }
    (tmp_path / "data/questions.jsonl").write_text(json.dumps(old) + "\n")
    row = dict.fromkeys(REVIEW_COLUMNS, "")
    rows = [
        {**row, "id": "q000", "question": old["question"], "reference_answer": "Kofi Mensah",
         "keep (y/n)": "y"},
        {**row, "id": "q001", "keep (y/n)": "n"},
    ]  # fmt: skip
    path = tmp_path / "results/questions_review_reviewed.csv"
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, REVIEW_COLUMNS)
        w.writeheader()
        w.writerows(rows)
    summary = "x\n## Spot-check list (1 row)\n\n| id | why |\n|---|---|\n| q000 | rewrite |\n"
    (tmp_path / "results/question_review_summary.md").write_text(summary)


def test_spot_check_ids_reads_only_the_table(tmp_path):
    _setup(tmp_path)
    assert spot_check_ids(tmp_path / "results/question_review_summary.md") == {"q000"}


def test_apply_merges_flags_and_replacements(tmp_path, monkeypatch):
    _setup(tmp_path)
    monkeypatch.setattr("securerag.eval.apply_review.REPLACEMENTS", REPLACEMENTS[:1])
    items = apply(tmp_path)
    by_id = {q["id"]: q for q in items}
    assert set(by_id) == {"q000", "q160"}  # q001 rejected
    assert by_id["q000"]["spot_checked"] and not by_id["q000"]["llm_verified"]
    assert by_id["q160"]["llm_verified"] and not by_id["q160"]["spot_checked"]
    assert not any(q["hand_checked"] for q in items)
    assert by_id["q000"]["evidence"].startswith("Kofi Mensah was the treasurer")
