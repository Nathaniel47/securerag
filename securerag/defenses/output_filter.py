"""D4 output filter: block answers that contain canaries, personal data or the system prompt."""

from securerag.defenses.base import Defense
from securerag.defenses.patterns import CANARY, PII
from securerag.eval.questions import norm_words
from securerag.rag.prompt import SYSTEM, SYSTEM_CANARY

REFUSAL = "I can't share that information."
SHINGLE = 5  # five consecutive words of the system prompt count as copying it


def _shingles(text: str) -> set[str]:
    words = norm_words(text).split()
    return {" ".join(words[i : i + SHINGLE]) for i in range(len(words) - SHINGLE + 1)}


class OutputFilter(Defense):
    name = "d4_output_filter"

    def __init__(self, system_prompt: str = SYSTEM):
        self.system_shingles = _shingles(system_prompt)

    def violations(self, answer: str) -> list[str]:
        found = []
        if CANARY.search(answer) or SYSTEM_CANARY.lower() in answer.lower():
            found.append("canary")
        if PII.search(answer):
            found.append("personal_data")
        if self.system_shingles & _shingles(answer):
            found.append("system_prompt")
        return found

    def filter_answer(self, answer, trace):
        found = self.violations(answer)
        if not found:
            return answer
        trace.blocked = True
        trace.flag(self.name, "blocked: " + ", ".join(found))
        return REFUSAL
