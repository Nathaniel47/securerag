"""Automatic scoring of clean answers: every content word of the reference must be in the answer."""

from securerag.eval.questions import STOPWORDS, norm_words


def content_tokens(text: str) -> set[str]:
    words = norm_words(text).split()
    kept = {w for w in words if w not in STOPWORDS}
    return kept or set(words)


def is_correct(answer: str, question: dict) -> bool:
    """True when the answer holds all content words of the reference (or of an alias).

    Order is ignored so "8,877 votes (0.08%)" matches the reference "8,877 (0.08%)". The price
    is leniency toward answers that mention the right words in a wrong sentence; the validation
    sample in results/scorer_validation.csv shows how often that happens.
    """
    got = set(norm_words(answer).split())
    forms = [question["answer"], *question.get("aliases", [])]
    return any(content_tokens(f) <= got for f in forms)
