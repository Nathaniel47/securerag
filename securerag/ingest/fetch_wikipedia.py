"""Fetch Ghana-related Wikipedia articles through the MediaWiki API (text is CC BY-SA 4.0).

Raw JSON goes to data/raw/ (git-ignored). data/manifest.jsonl records the title, revision id and
a content hash of every article, which is what CC BY-SA attribution and drift checks need.
"""

import argparse
import hashlib
import json
import random
import time
from datetime import date
from pathlib import Path

import httpx

from securerag.ingest.clean import clean_document

API_URL = "https://en.wikipedia.org/w/api.php"
LICENCE = "CC-BY-SA-4.0"
USER_AGENT = "securerag-research/0.1 (https://github.com/Nathaniel47/securerag; research testbed)"

# Seed categories cover the areas asked for: government, health, education, regions and cities,
# institutions, economy. Subcategories are followed one level down.
CATEGORIES = (
    "Government of Ghana",
    "Government ministries of Ghana",
    "Government agencies of Ghana",
    "Politics of Ghana",
    "Elections in Ghana",
    "Political parties in Ghana",
    "Judiciary of Ghana",
    "Law of Ghana",
    "Health in Ghana",
    "Healthcare in Ghana",
    "Hospitals in Ghana",
    "Medical education in Ghana",
    "Education in Ghana",
    "Schools in Ghana",
    "Universities and colleges in Ghana",
    "Regions of Ghana",
    "Districts of Ghana",
    "Populated places in Ghana",
    "Geography of Ghana",
    "Economy of Ghana",
    "Banks of Ghana",
    "Companies of Ghana",
    "Mining in Ghana",
    "Tourism in Ghana",
    "Agriculture in Ghana",
    "Energy in Ghana",
    "Transport in Ghana",
    "Ports and harbours of Ghana",
    "Water in Ghana",
    "Telecommunications in Ghana",
    "Culture of Ghana",
    "History of Ghana",
    "Organisations based in Ghana",
    "Media in Ghana",
)
SKIP_TITLE_PREFIXES = ("List of", "Lists of", "Index of", "Outline of", "Timeline of")


def _get(client: httpx.Client, params: dict, retries: int = 4) -> dict:
    params = {"format": "json", "formatversion": 2, **params}
    for attempt in range(retries):
        resp = client.get(API_URL, params=params)
        if resp.status_code == 200:
            return resp.json()
        time.sleep(2**attempt)
    resp.raise_for_status()
    return {}


def _members(client: httpx.Client, category: str, kind: str, delay: float) -> list[str]:
    out, cont = [], {}
    while True:
        data = _get(
            client,
            {
                "action": "query",
                "list": "categorymembers",
                "cmtitle": f"Category:{category}",
                "cmtype": kind,
                "cmlimit": 500,
                **cont,
            },
        )
        out += [m["title"] for m in data.get("query", {}).get("categorymembers", [])]
        time.sleep(delay)
        if "continue" not in data:
            return out
        cont = data["continue"]


def candidate_titles(client: httpx.Client, delay: float) -> dict[str, str]:
    """Map article title -> first seed category it was found in."""
    found: dict[str, str] = {}
    for cat in CATEGORIES:
        subcats = [s.removeprefix("Category:") for s in _members(client, cat, "subcat", delay)]
        for c in [cat, *subcats]:
            for title in _members(client, c, "page", delay):
                if not title.startswith(SKIP_TITLE_PREFIXES):
                    found.setdefault(title, cat)
    return found


def fetch_page(client: httpx.Client, title: str) -> dict | None:
    data = _get(
        client,
        {
            "action": "query",
            "prop": "extracts|revisions|pageprops",
            "explaintext": 1,
            "rvprop": "ids|timestamp",
            "ppprop": "disambiguation",
            "redirects": 1,
            "titles": title,
        },
    )
    pages = data.get("query", {}).get("pages", [])
    if not pages or pages[0].get("missing"):
        return None
    return pages[0]


def fetch_corpus(out_dir: Path, target: int, seed: int, delay: float = 0.1) -> list[dict]:
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []
    seen_ids: set[int] = set()
    rejected: list[dict] = []
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30) as c:
        found = candidate_titles(c, delay)
        titles = sorted(found)
        random.Random(seed).shuffle(titles)
        for title in titles:
            if len(manifest) >= target:
                break
            page = fetch_page(c, title)
            time.sleep(delay)
            if not page or page["pageid"] in seen_ids:
                continue
            seen_ids.add(page["pageid"])
            _, problems = clean_document(page)
            if problems:
                rejected.append({"title": page["title"], "problems": problems})
                continue
            rev = page["revisions"][0]
            fname = f"{page['pageid']}.json"
            blob = json.dumps(page, sort_keys=True, ensure_ascii=False)
            (raw_dir / fname).write_text(blob, encoding="utf-8")
            slug = page["title"].replace(" ", "_")
            manifest.append(
                {
                    "path": f"/wiki/{slug}",
                    "url": f"https://en.wikipedia.org/wiki/{slug}",
                    "history_url": f"https://en.wikipedia.org/w/index.php?title={slug}&action=history",
                    "title": page["title"],
                    "pageid": page["pageid"],
                    "revid": rev["revid"],
                    "revision_timestamp": rev["timestamp"],
                    "seed_category": found[title],
                    "disambiguation": "disambiguation" in page.get("pageprops", {}),
                    "raw_file": fname,
                    "sha256": hashlib.sha256(blob.encode()).hexdigest(),
                    "licence": LICENCE,
                    "fetched_on": date.today().isoformat(),
                }
            )
    print(f"rejected {len(rejected)} candidates (off-topic, stubs, disambiguation)")
    manifest.sort(key=lambda m: m["pageid"])
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
    print(f"fetched {len(m)} articles")
