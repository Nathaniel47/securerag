"""Turn a raw GOV.UK content-API document into plain text, and check it for licence problems."""

import re

from bs4 import BeautifulSoup

MIN_CHARS = 300
# Pages that say they include material outside the OGL are dropped (PLAN.md risk 2).
THIRD_PARTY_PATTERNS = (
    r"not covered by the open government licence",
    r"third[- ]party (copyright|material)",
    r"©|\(c\) \d{4}",
    r"all rights reserved",
)


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    for h in soup.find_all(re.compile(r"^h[1-6]$")):
        h.string = f"\n\n## {h.get_text(' ', strip=True)}\n\n"
    for li in soup.find_all("li"):
        li.string = f"\n- {li.get_text(' ', strip=True)}\n"
    for p in soup.find_all("p"):
        p.append("\n\n")
    for br in soup.find_all("br"):
        br.replace_with("\n")
    # Separator "" keeps inline tags (links, bold) inside their sentence.
    text = soup.get_text("")
    text = re.sub(r"[ \t ]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return "\n".join(line.strip() for line in text.splitlines()).strip()


def extract_text(doc: dict) -> str:
    details = doc.get("details", {})
    parts: list[str] = []
    if doc.get("description"):
        parts.append(doc["description"].strip())
    if "parts" in details:  # guides are split into parts, each with its own title
        for p in details["parts"]:
            parts.append(f"## {p.get('title', '')}\n{html_to_text(p.get('body', ''))}")
    elif details.get("body"):
        parts.append(html_to_text(details["body"]))
    return "\n\n".join(p for p in parts if p.strip())


def third_party_flag(text: str) -> bool:
    low = text.lower()
    return any(re.search(p, low) for p in THIRD_PARTY_PATTERNS)


def clean_document(doc: dict) -> tuple[str, list[str]]:
    """Return (text, problems). Problems are reasons the page should be dropped."""
    text = extract_text(doc)
    problems = []
    if len(text) < MIN_CHARS:
        problems.append("too_short")
    if third_party_flag(text):
        problems.append("possible_third_party_material")
    if doc.get("withdrawn_notice"):
        problems.append("withdrawn")
    return text, problems
