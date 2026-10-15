# LEARNING.md

Plain-English notes on what was built and why it matters.

## Step 2: Repo setup

- **Package layout** (`securerag/`, `api/`, `ui/`, `tests/`): mirrors PLAN.md so each part of the pipeline (ingest, retrieval, attacks, defenses, evaluation) has one obvious home. Empty packages are placeholders for later steps.
- **`config.py`**: one place for the defense on/off switches and retrieval settings. `CONFIGS` lists the 6 configurations that will be evaluated (no defense, each of four alone, all combined). Keeping this central means every experiment is described by a config you can save and reproduce.
- **Secrets**: keys come only from `SECURERAG_*` environment variables. `.env` is git-ignored and `.env.example` has names only. The pre-commit hook runs **gitleaks**, which scans each commit for key-like strings and blocks it. Why it matters: free-tier API keys leaked to GitHub get scraped within minutes. Reading: the gitleaks README (pre-commit section).
- **Pre-commit + ruff + CI**: ruff formats and lints; GitHub Actions re-runs lint and tests on every push so a broken commit is visible straight away.
- **Docker**: `docker-compose.yml` defines api, ui and an optional Ollama profile, with memory caps inside the 8 GB budget. The api/ui entry points (`api/main.py`, `ui/playground.py`) are built in step 5, so compose won't start until then.
- **Two requirements files**: `requirements.txt` is the app (heavy: Chroma, sentence-transformers); `requirements-dev.txt` is lint/test tools. CI installs only the dev file for now to stay fast; add runtime packages to CI when tests need them.

How to check: `pytest` and `ruff check .` should both pass.

## Step 3: Data pipeline (redone for a Ghana corpus)

- **Corpus change**: the owner switched the corpus from GOV.UK to Ghana-related Wikipedia articles (about 420 on government, health, education, regions, economy, law and institutions). PLAN.md was updated to match. Wikipedia text is CC BY-SA 4.0: reuse needs attribution and the derived corpus must be shared under the same licence, which is recorded in the README.
- **Fetch** (`ingest/fetch_wikipedia.py`): walks 34 Wikipedia categories (plus one level of subcategories), shuffles the candidates with a fixed seed, and keeps articles until 420 pass the quality checks. 971 candidates were rejected (off-topic, stubs, disambiguation). The manifest stores title, URL, revision id, hash and licence, which is exactly what attribution and drift checks need.
- **Why a relevance filter**: category trees leak. "Law of Ghana" contains international treaties that mention Ghana once. Requiring at least 5 mentions of Ghana removed them; without it a retrieval test would be answering questions about whales.
- **Clean** (`ingest/clean.py`): converts `== Heading ==` markup to `## Heading`, drops References/External links style sections, and removes empty brackets left where Wikipedia strips pronunciations.
- **Chunk** (`ingest/chunk.py`): about 300 tokens (approximated as 225 words) along paragraph boundaries; a tiny leftover is folded into the previous chunk. Each chunk carries source URL, `trust` and `role`. In this corpus `trust: official` means "the trusted base knowledge base", not "government-authored"; Wikipedia is editable by anyone, which is itself a realistic poisoning risk worth stating in the write-up.
- **Synthetic restricted records**: 40 invented staff-only case notes with Ghanaian-style names, `GHA-FAKE-...` and `NHIS-FAKE-...` IDs and a unique canary string. A canary in a public answer is automatic proof of leakage. Each note is labelled SYNTHETIC.
- **LLM client** (`llm/`): a cache in front of a pluggable backend (Groq now). The cache key includes model, messages, temperature, seed and a repeat index, so reruns are free and repeats stay independent. It was needed now because question generation must go through it.
- **Questions** (`eval/questions.py`): asks the model for two questions per chunk, then keeps only items whose answer is short, appears verbatim in the passage and is not given away by the question. This is an automatic grounding check, not a replacement for the hand-check PLAN.md requires. Not yet run: it needs `SECURERAG_GROQ_API_KEY`.
- **Splits** (`data/splits.json`): 200 pages are the question source, 220 the rest.
- **Not committed**: `data/raw`, `corpus.jsonl`, `chunks.jsonl` are git-ignored; rebuild with the README commands.

How to check: `pytest` and `ruff check .` pass; `python -m securerag.ingest.build` regenerates identical chunks and splits.
