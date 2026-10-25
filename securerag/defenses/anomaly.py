"""D2 retrieval anomaly score: drop retrieved chunks that look planted. No LLM calls.

Three signals, each a known sign of an attack:
- instruction-like text (an injection),
- a chunk that is nearly identical to another retrieved chunk (poisoning plants several copies),
- a similarity to the question far above what real passages reach (poison documents repeat the
  question word for word).
"""

import numpy as np

from securerag.defenses.base import Defense
from securerag.defenses.patterns import INSTRUCTION

# Calibrated on the 150 clean questions: the highest top-1 similarity of a genuine passage (0.834)
# stays below SIMILARITY_LIMIT (see LEARNING.md, "D2 calibration").
SIMILARITY_LIMIT = 0.85
DUPLICATE_LIMIT = 0.915


class AnomalyScore(Defense):
    name = "d2_anomaly"

    def __init__(
        self, similarity_limit: float = SIMILARITY_LIMIT, duplicate_limit: float = DUPLICATE_LIMIT
    ):
        self.similarity_limit = similarity_limit
        self.duplicate_limit = duplicate_limit

    def reasons(self, chunks: list[dict]) -> dict[str, list[str]]:
        found: dict[str, list[str]] = {}
        for i, c in enumerate(chunks):
            why = found.setdefault(c["chunk_id"], [])
            if INSTRUCTION.search(c["text"]):
                why.append("instruction_text")
            if c["score"] >= self.similarity_limit:
                why.append(f"similarity_{c['score']:.2f}")
            for other in chunks[i + 1 :]:
                if float(np.dot(c["embedding"], other["embedding"])) >= self.duplicate_limit:
                    found.setdefault(other["chunk_id"], []).append("near_duplicate")
                    why.append("near_duplicate")
        return {cid: why for cid, why in found.items() if why}

    def filter_chunks(self, question, chunks, trace):
        flagged = self.reasons(chunks)
        if flagged:
            trace.flag(self.name, "dropped " + "; ".join(f"{c}: {w}" for c, w in flagged.items()))
        return [c for c in chunks if c["chunk_id"] not in flagged]
