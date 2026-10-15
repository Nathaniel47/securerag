"""Clean Wikipedia plain-text extracts and flag pages that should not enter the corpus."""

import re

MIN_CHARS = 1000  # shorter articles are stubs with too little to ask questions about
MIN_GHANA_MENTIONS = 5
TAIL_SECTIONS = {
    "references",
    "external links",
    "see also",
    "further reading",
    "notes",
    "sources",
    "bibliography",
    "citations",
    "footnotes",
}
HEADING = re.compile(r"^(={2,6})\s*(.*?)\s*\1\s*$")


def extract_text(raw: str) -> str:
    """Convert '== Heading ==' markup to '## Heading', drop reference-style tail sections."""
    out: list[str] = []
    skipping = False
    for line in raw.splitlines():
        m = HEADING.match(line.strip())
        if m:
            skipping = m.group(2).lower() in TAIL_SECTIONS
            if not skipping:
                out.append(f"\n## {m.group(2)}\n")
            continue
        if not skipping:
            out.append(line.strip())
    text = "\n".join(out)
    text = re.sub(r"\(\s*[;,]?\s*\)", "", text)  # empty brackets left by removed pronunciations
    text = re.sub(r"[ \t ]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()


def clean_document(page: dict, manifest_row: dict | None = None) -> tuple[str, list[str]]:
    """Return (text, problems). Problems are reasons the page should be dropped."""
    text = extract_text(page.get("extract", ""))
    problems = []
    if len(text) < MIN_CHARS:
        problems.append("too_short")
    # Category crawls pull in treaties and organisations that only mention Ghana in passing.
    if len(re.findall(r"\bGhana(?:ian)?s?\b", text)) < MIN_GHANA_MENTIONS:
        problems.append("off_topic")
    if "disambiguation" in page.get("pageprops", {}) or (
        manifest_row and manifest_row.get("disambiguation")
    ):
        problems.append("disambiguation")
    return text, problems
