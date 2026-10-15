# SecureRAG: RAG Security Testbed

A RAG assistant over public Ghana-related Wikipedia articles, plus a harness that attacks it (knowledge-base poisoning, indirect and direct prompt injection, data leakage), applies four defenses, and scores each defense automatically.

> Status: under construction. See [PLAN.md](PLAN.md) and [BUILD_STEPS.md](BUILD_STEPS.md).

## Run locally

Requires Python 3.11+ (Docker optional). Commands below are for Windows PowerShell; macOS/Linux equivalents are in comments.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
copy .env.example .env              # macOS/Linux: cp .env.example .env  (then fill in keys)
pre-commit install                  # enables gitleaks + ruff on every commit
pytest
```

With Docker (api + ui; works once step 5 is built):

```
docker compose up --build
```

## Configuration

Keys are read from environment variables only: `SECURERAG_GROQ_API_KEY`, `SECURERAG_GEMINI_API_KEY`. Never commit `.env`.

## Data

Build the corpus (needs network once; raw pages are git-ignored):

```powershell
python -m securerag.ingest.fetch_wikipedia   # ~420 articles -> data/raw + data/manifest.jsonl
python -m securerag.ingest.build             # -> data/chunks.jsonl, data/splits.json, results/data_report.md
python -m securerag.eval.questions           # 150 questions -> data/questions.jsonl (needs SECURERAG_GROQ_API_KEY)
```

See [results/data_report.md](results/data_report.md) for counts, distributions and quality problems.

## Data licences and attribution

| Data | Source | Licence / terms |
|---|---|---|
| Ghana-related articles (English Wikipedia, text only) | MediaWiki API, `en.wikipedia.org/w/api.php` | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Attribution: each article's title, URL, revision id and fetch date are in `data/manifest.jsonl` (`history_url` lists the authors). **The derived corpus (cleaned text, chunks) and the question set built from it are shared under CC BY-SA 4.0 too.** Text only: Wikipedia images and non-text media are not used. |
| Synthetic restricted case notes (40) | `securerag/ingest/synthetic_restricted.py` | Invented records, marked SYNTHETIC. Ghanaian-style names (any match with a real person is coincidence); IDs contain `FAKE` and cannot be valid Ghana Card or NHIS numbers; emails use `example.org`; phones use the invalid block `+233 000 000 xxx`. Code under the repo licence. |
| Clean question set (150) and attack sets (100) | Generated in later steps | Derived from Wikipedia text, so CC BY-SA 4.0. |

**Official Ghanaian sources considered and skipped**

| Source | Why skipped |
|---|---|
| Ghana Open Data Initiative (data.gov.gh) | Its FAQ says datasets use the Open Data Commons Attribution licence "with exceptions" set per dataset, other sites describe the licence differently, and no standalone licence text was found. That is not "clearly stated". The datasets are also mostly tables, not prose a RAG assistant can answer from. |
| Other ministry/agency publications (PDFs) | Not added: no per-document reuse licence was verified in this step. Add one only after confirming its licence. |

The fetcher identifies itself with a descriptive User-Agent and waits 0.1 s between requests, following Wikimedia's API etiquette.
