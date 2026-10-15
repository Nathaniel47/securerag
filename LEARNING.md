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

## Step 3: Data pipeline

- **Fetch** (`ingest/fetch_govuk.py`): searches GOV.UK for 46 broad topics, shuffles the candidate pages with a fixed seed, and keeps the first 420 that are plain guidance (answer, guide, detailed guide). It saves raw JSON locally and writes `data/manifest.jsonl` with a sha256 per page. Why: GOV.UK changes over time, so the hash lets you see whether a later re-fetch differs from the corpus your results came from.
- **Clean** (`ingest/clean.py`): turns the HTML into plain text, keeping headings and bullet points, and drops pages that are too short, withdrawn, or mention third-party/copyright material (the OGL covers most but not all GOV.UK content).
- **Chunk** (`ingest/chunk.py`): splits pages into pieces of about 300 tokens (approximated as 225 words) along paragraph boundaries. Each chunk is tagged with source URL, `trust` and `role`. Those two tags are what defense D1 (source filtering) and the role-based retrieval filter will use later.
- **Synthetic restricted records** (`ingest/synthetic_restricted.py`): 40 invented staff-only case notes, each with a unique canary string. If a canary shows up in an answer to a public user, leakage is proven automatically with no judge. Fake NI numbers use the never-issued `QQ` prefix so they cannot match a real person.
- **Splits** (`data/splits.json`): 200 pages are set aside as the source for the 150 clean questions; the rest are the "other" pool. Saving the split with a seed means week 2's question generation is reproducible.
- **Report** (`results/data_report.md`): counts, distributions, samples and quality problems (very long pages, tiny chunks, duplicates).
- **Deviation noted**: BUILD_STEPS mentions a question set of 300+, but PLAN.md says 150 clean questions plus 100 attacks, generated in week 2 with hand-checking. PLAN.md wins, so questions are not generated in this step.
- **Not committed**: `data/raw`, `corpus.jsonl` and `chunks.jsonl` are git-ignored (several MB each, and the pre-commit large-file check would block them). Rebuild them with the two commands in the README.

How to check: `pytest` passes; `python -m securerag.ingest.build` regenerates the same chunks and splits from the same raw files.
