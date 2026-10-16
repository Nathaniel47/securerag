"""Rate-limit and daily-token budget so long runs pause and resume instead of failing."""

import json
import math
import re
import time
from collections import deque
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path


class DailyBudgetExhausted(RuntimeError):
    """Raised when the next call would pass the daily limit. Rerun after 00:00 UTC; the cache
    keeps everything already answered."""


def estimate_tokens(text: str) -> int:
    return math.ceil(len(text) / 4)


def plan_days(calls: int, tokens_per_call: int, tpd: int) -> float:
    return calls * tokens_per_call / tpd


def _utc_day(now: float) -> str:
    return datetime.fromtimestamp(now, tz=UTC).strftime("%Y-%m-%d")


class TokenBudget:
    """Per-model limiter. RPM and TPM use a sliding 60 s window and sleep; RPD and TPD persist in
    a small file so a rerun the same UTC day continues from where the last run stopped."""

    def __init__(
        self,
        directory: Path,
        model: str,
        limits: dict[str, int],
        margin: float = 0.95,
        clock: Callable[[], float] = time.time,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.path = directory / f"usage_{re.sub(r'[^A-Za-z0-9]+', '_', model)}.json"
        self.limits, self.margin, self.clock, self.sleep = limits, margin, clock, sleep
        self.window: deque[tuple[float, int]] = deque()

    def _load(self) -> dict:
        today = _utc_day(self.clock())
        if self.path.exists():
            data = json.loads(self.path.read_text())
            if data.get("day") == today:
                return data
        return {"day": today, "tokens": 0, "requests": 0}

    def before_call(self, est_tokens: int) -> None:
        usage = self._load()
        if usage["tokens"] + est_tokens > self.limits["tpd"] * self.margin:
            raise DailyBudgetExhausted(
                f"{usage['tokens']} of {self.limits['tpd']} tokens used today (UTC); resume later"
            )
        if usage["requests"] + 1 > self.limits["rpd"] * self.margin:
            raise DailyBudgetExhausted(f"{usage['requests']} requests used today (UTC)")
        while True:
            now = self.clock()
            while self.window and now - self.window[0][0] >= 60:
                self.window.popleft()
            used = sum(t for _, t in self.window)
            if len(self.window) < self.limits["rpm"] and used + est_tokens <= self.limits["tpm"]:
                return
            self.sleep(max(0.5, 60 - (now - self.window[0][0])) if self.window else 1)

    def record(self, tokens: int) -> None:
        self.window.append((self.clock(), tokens))
        usage = self._load()
        usage["tokens"] += tokens
        usage["requests"] += 1
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(usage))
