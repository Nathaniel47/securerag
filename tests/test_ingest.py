import json

from securerag.ingest.build import build, make_report
from securerag.ingest.chunk import chunk_text, make_chunks
from securerag.ingest.clean import clean_document, extract_text
from securerag.ingest.synthetic_restricted import make_records, record_to_chunk

LONG_GHANA = "Ghana is a country in West Africa. " * 100


def test_extract_text_converts_headings_and_drops_tail_sections():
    raw = (
        "Intro line.\n\n== History ==\nSome history.\n\n=== Early ===\nMore.\n\n"
        "== References ==\nref one\n\n== Economy ==\nTrade."
    )
    text = extract_text(raw)
    assert "## History" in text and "## Early" in text and "## Economy" in text
    assert "ref one" not in text
    assert "Trade." in text


def test_empty_brackets_removed():
    assert "()" not in extract_text("Accra () is the capital.")


def test_clean_document_flags_short_and_disambiguation():
    page = {"extract": "tiny", "pageprops": {"disambiguation": ""}}
    _, problems = clean_document(page)
    assert set(problems) == {"too_short", "disambiguation", "off_topic"}


def test_clean_document_flags_off_topic_article():
    _, problems = clean_document({"extract": "Whales are large animals. " * 100})
    assert problems == ["off_topic"]


def test_clean_document_accepts_long_ghana_article():
    _, problems = clean_document({"extract": LONG_GHANA})
    assert problems == []


def test_chunks_respect_size_and_lose_nothing():
    text = "\n\n".join(" ".join(f"w{i}_{j}" for j in range(100)) for i in range(10))
    chunks = chunk_text(text, chunk_tokens=200)  # 150 words max
    assert all(len(c.split()) <= 150 for c in chunks)
    assert " ".join(chunks).split() == text.split()


def test_long_single_paragraph_is_split():
    chunks = chunk_text("a " * 1000, chunk_tokens=100)
    assert len(chunks) > 1 and all(len(c.split()) <= 75 for c in chunks)


def test_tiny_trailing_chunk_is_merged():
    chunks = chunk_text(("a " * 224).strip() + "\n\n" + "b b b", chunk_tokens=300)
    assert len(chunks) == 1


def test_chunk_tags():
    c = make_chunks("/p", "https://en.wikipedia.org/wiki/p", "T", "hello world")[0]
    assert (c["trust"], c["role"], c["chunk_id"]) == ("official", "public", "/p#0")


def test_restricted_records_are_synthetic_and_reproducible():
    a, b = make_records(20, seed=1), make_records(20, seed=1)
    assert a == b and a != make_records(20, seed=2)
    assert all("FAKE" in r["ghana_card_id"] and "FAKE" in r["nhis_id"] for r in a)
    assert all(r["email"].endswith("@example.org") for r in a)
    assert len({r["canary"] for r in a}) == 20
    chunk = record_to_chunk(a[0])
    assert chunk["trust"] == "restricted" and a[0]["canary"] in chunk["text"]
    assert "SYNTHETIC" in chunk["text"]


def _write_fixture(data_dir, n):
    (data_dir / "raw").mkdir(parents=True)
    manifest = []
    for i in range(n):
        doc = {"title": f"T{i}", "extract": LONG_GHANA + f" page {i}"}
        (data_dir / "raw" / f"{i}.json").write_text(json.dumps(doc))
        manifest.append(
            {
                "path": f"/wiki/p{i}",
                "url": f"https://en.wikipedia.org/wiki/p{i}",
                "title": f"T{i}",
                "seed_category": "Health in Ghana",
                "revid": i,
                "raw_file": f"{i}.json",
            }
        )
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
