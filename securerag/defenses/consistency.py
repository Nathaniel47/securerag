"""D3 answer consistency: answer from two disjoint halves of the sources and compare.

A single planted chunk can only steer one half, so a disagreement exposes it. A half whose sources
do not contain the answer abstains and does not count as a disagreement. Costs 2 LLM calls.
"""

import re

from securerag.defenses.base import Defense
from securerag.eval.questions import STOPWORDS, norm_words

CAUTIOUS = "I could not verify an answer from the sources, so I am not giving one."
ABSTAIN = re.compile(
    r"don'?t know|do not know|not (contain|provide|mention|specif)|no information|cannot (find|"
    r"determine)|can'?t (find|determine)|unable to",
    re.I,
)


def is_abstention(answer: str) -> bool:
    return not answer.strip() or ABSTAIN.search(answer) is not None


def agree(a: str, b: str, threshold: float = 0.5) -> bool:
    """Same answer in different words: enough of the content words of the shorter one are shared."""
    ta = set(norm_words(a).split()) - STOPWORDS
    tb = set(norm_words(b).split()) - STOPWORDS
    if not ta or not tb:
        return norm_words(a) == norm_words(b)
    return len(ta & tb) / min(len(ta), len(tb)) >= threshold


class AnswerConsistency(Defense):
    name = "d3_consistency"

    def generate(self, pipe, question, chunks, trace, repeat):
        halves = (chunks[0::2], chunks[1::2])
        if not halves[1]:  # a single source cannot be cross-checked
            return None
        a, b = (pipe.generate(question, half, trace, repeat) for half in halves)
        if is_abstention(a) or is_abstention(b):
            return b if is_abstention(a) else a
        if agree(a, b):
            return a
        trace.blocked = True
        trace.flag(self.name, f"halves disagree: {a!r} vs {b!r}")
        return CAUTIOUS
