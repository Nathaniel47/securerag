"""Fetch GOV.UK guidance pages through the public Search and Content APIs.

Raw JSON goes to data/raw/ (git-ignored); data/manifest.jsonl records what was fetched, with a
content hash so later drift in the live pages is detectable.
"""

import argparse
import hashlib
import json
import random
import time
from datetime import date
from pathlib import Path

import httpx

SEARCH_URL = "https://www.gov.uk/api/search.json"
CONTENT_URL = "https://www.gov.uk/api/content"
ACCEPTED_SCHEMAS = ("answer", "guide", "detailed_guide")
LICENCE = "OGL-3.0"
USER_AGENT = "securerag-research/0.1 (security testbed; contact via GitHub repo)"

# Broad topics so the corpus covers many service areas, not one department.
TOPICS = (
    "driving licence",
    "vehicle tax",
    "passport",
    "visa",
    "state pension",
    "universal credit",
    "child benefit",
    "council tax",
    "income tax",
    "self assessment",
    "VAT",
    "starting a business",
    "employing someone",
    "redundancy",
    "maternity leave",
    "statutory sick pay",
    "minimum wage",
    "tenancy deposit",
    "renting",
    "buying a home",
    "stamp duty",
    "student finance",
    "school",
    "apprenticeship",
    "NHS",
    "disability benefits",
    "carer",
    "births deaths marriages",
    "probate",
    "inheritance tax",
    "jury service",
    "voting",
    "immigration",
    "citizenship",
    "import export",
    "customs",
    "flooding",
    "planning permission",
    "recycling waste",
    "bereavement",
    "armed forces",
    "fishing licence",
    "environmental permit",
    "food hygiene",
    "data protection",
    "charity",
)


def _get(client: httpx.Client, url: str, params: dict | None = None, retries: int = 3) -> dict:
    for attempt in range(retries):
        resp = client.get(url, params=params)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 404:
            return {}
        time.sleep(2**attempt)
    resp.raise_for_status()
    return {}


def candidate_paths(client: httpx.Client, per_topic: int, delay: float) -> list[str]:
    seen: dict[str, None] = {}
    for topic in TOPICS:
        data = _get(client, SEARCH_URL, {"q": topic, "count": per_topic, "fields": "link"})
        for r in data.get("results", []):
            link = r.get("link", "")
            # Only plain www.gov.uk paths; skip external links and non-guidance areas.
            if link.startswith("/") and not link.startswith(("/government/", "/browse/")):
                seen.setdefault(link)
        time.sleep(delay)
    return list(seen)


def fetch_corpus(
    out_dir: Path, target: int, seed: int, per_topic: int = 40, delay: float = 0.25
) -> list[dict]:
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    manifest: list[dict] = []
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30, follow_redirects=True) as c:
        paths = sorted(candidate_paths(c, per_topic, delay))
        rng.shuffle(paths)
        for path in paths:
            if len(manifest) >= target:
                break
            doc = _get(c, f"{CONTENT_URL}{path}")
            time.sleep(delay)
            if doc.get("schema_name") not in ACCEPTED_SCHEMAS:
                continue
            blob = json.dumps(doc, sort_keys=True, ensure_ascii=False)
            fname = hashlib.sha1(path.encode()).hexdigest()[:16] + ".json"
            (raw_dir / fname).write_text(blob, encoding="utf-8")
            manifest.append(
                {
                    "path": path,
                    "url": f"https://www.gov.uk{path}",
                    "title": doc.get("title", ""),
                    "schema": doc["schema_name"],
                    "public_updated_at": doc.get("public_updated_at"),
                    "raw_file": fname,
                    "sha256": hashlib.sha256(blob.encode()).hexdigest(),
                    "licence": LICENCE,
                    "fetched_on": date.today().isoformat(),
                }
            )
    manifest.sort(key=lambda m: m["path"])
    (out_dir / "manifest.jsonl").write_text(
        "".join(json.dumps(m, ensure_ascii=False) + "\n" for m in manifest), encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=Path("data"))
    ap.add_argument("--target", type=int, default=420)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    m = fetch_corpus(args.out, args.target, args.seed)
    print(f"fetched {len(m)} pages")
