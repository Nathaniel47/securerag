import pytest

from securerag.llm.groq import call_with_retries


class Flaky:
    def __init__(self, fails: int, exc=ConnectionError):
        self.fails, self.exc, self.calls = fails, exc, 0

    def __call__(self):
        self.calls += 1
        if self.calls <= self.fails:
            raise self.exc("boom")
        return "ok", 7


def test_retries_then_succeeds():
    waits = []
    f = Flaky(3)
    assert call_with_retries(f, (ConnectionError,), sleep=waits.append) == ("ok", 7)
    assert f.calls == 4
    assert waits == [5, 10, 20]


def test_gives_up_after_attempts():
    f = Flaky(99)
    with pytest.raises(RuntimeError, match="resume later"):
        call_with_retries(f, (ConnectionError,), attempts=3, sleep=lambda s: None)
    assert f.calls == 3


def test_other_errors_are_not_retried():
    f = Flaky(1, exc=ValueError)
    with pytest.raises(ValueError):
        call_with_retries(f, (ConnectionError,), sleep=lambda s: None)
    assert f.calls == 1
