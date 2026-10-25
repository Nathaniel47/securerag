"""D1 source filtering: public users see only official sources, and new documents are scanned."""

from securerag.defenses.base import Defense
from securerag.defenses.patterns import INSTRUCTION


class SourceFilter(Defense):
    name = "d1_source_filter"
    allowed_trust = frozenset({"official"})

    def accepts_document(self, chunk: dict) -> bool:
        return INSTRUCTION.search(chunk["text"]) is None
