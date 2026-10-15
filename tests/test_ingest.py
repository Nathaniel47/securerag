import json

from securerag.ingest.build import build, make_report
from securerag.ingest.chunk import chunk_text, make_chunks
from securerag.ingest.clean import clean_document, html_to_text, third_party_flag
from securerag.ingest.synthetic_restricted import make_records, record_to_chunk


def test_html_to_text_keeps_inline_links_and_lists():
    html = (
        "<h2>Overview</h2><p>You can <a href='x'>apply online</a> now.</p>"
        "<ul><li>one</li><li>two</li></ul>"
    )
    text = html_to_text(html)
    assert "## Overview" in text
    assert "You can apply online now." in text
    assert "- one" in text and "- two" in text


def test_third_party_flag():
    assert third_party_flag("Photo © 2020 Someone")
    assert third_party_flag("This is not covered by the Open Government Licence")
    assert not third_party_flag("Plain guidance about driving.")


def test_clean_document_flags_short_and_withdrawn():
    doc = {"description": "tiny", "details": {"body": "<p>x</p>"}, "withdrawn_notice": {"a": 1}}
    _, problems = clean_document(doc)
    assert set(problems) == {"too_short", "withdrawn"}


def test_guide_parts_are_joined():
    body = "<p>" + "word " * 100 + "</p>"
    doc = {"details": {"parts": [{"title": "A", "body": body}, {"title": "B", "body": body}]}}
    text, problems = clean_document(doc)
    assert "## A" in text and "## B" in text and not problems


def test_chunks_respect_size_and_lose_nothing():
    text = "\n\n".join(" ".join(f"w{i}_{j}" for j in range(100)) for i in range(10))
    chunks = chunk_text(text, chunk_tokens=200)  # 150 words max
    assert all(len(c.split()) <= 150 for c in chunks)
    assert " ".join(chunks).split() == text.split()


def test_long_single_paragraph_is_split():
    chunks = chunk_text("a " * 1000, chunk_tokens=100)
    assert len(chunks) > 1 and all(len(c.split()) <= 75 for c in chunks)


def test_chunk_tags():
    c = make_chunks("/p", "https://www.gov.uk/p", "T", "hello world")[0]
    assert (c["trust"], c["role"], c["chunk_id"]) == ("official", "public", "/p#0")


def test_restricted_records_are_synthetic_and_reproducible():
    a, b = make_records(20, seed=1), make_records(20, seed=1)
    assert a == b and a != make_records(20, seed=2)
    assert all(r["ni_number"].startswith("QQ") for r in a)
    assert all(r["email"].endswith("@example.org") for r in a)
    assert len({r["canary"] for r in a}) == 20
    chunk = record_to_chunk(a[0])
    assert chunk["trust"] == "restricted" and a[0]["canary"] in chunk["text"]


def _write_fixture(data_dir, n):
    (data_dir / "raw").mkdir(parents=True)
    manifest = []
    for i in range(n):
        body = f"<p>{'guidance sentence ' * 80} page {i}</p>"
        doc = {"title": f"T{i}", "schema_name": "answer", "details": {"body": body}}
        (data_dir / "raw" / f"{i}.json").write_text(json.dumps(doc))
        manifest.append(
            {"path": f"/p{i}", "url": f"https://www.gov.uk/p{i}", "title": f"T{i}",
             "schema": "answer", "raw_file": f"{i}.json"}
        )  # fmt: skip
    (data_dir / "manifest.jsonl").write_text("".join(json.dumps(m) + "\n" for m in manifest))


def test_build_is_deterministic_and_splits_disjoint(tmp_path):
    d1, d2 = tmp_path / "a", tmp_path / "b"
    for d in (d1, d2):
        d.mkdir()
        _write_fixture(d, 12)
    r1, r2 = build(d1, 7, 300), build(d2, 7, 300)
    assert r1["splits"] == r2["splits"]
    s = r1["splits"]
    assert not set(s["question_source"]) & set(s["other"])
    assert len(s["question_source"]) + len(s["other"]) == 12
    assert any(c["trust"] == "restricted" for c in r1["chunks"])
    assert "# Data report" in make_report(r1, 12)
