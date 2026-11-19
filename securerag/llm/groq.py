"""Groq backend. The SDK is imported lazily so tests and CI do not need it."""

import os
import time

from securerag.config import RATE_LIMITS, Config, groq_api_key
from securerag.llm.budget import TokenBudget
from securerag.llm.cache import DEFAULT_DIR
from securerag.llm.client import LLMClient


def groq_backend(
    model: str, messages: list[dict], temperature: float | None, seed: int | None, settings: dict
) -> tuple[str, int]:
    from groq import APIConnectionError, Groq, RateLimitError

    key = groq_api_key()
    if not key:
        raise RuntimeError("SECURERAG_GROQ_API_KEY is not set")
    client = Groq(api_key=key)
    kwargs = dict(settings)
    if temperature is not None:
        kwargs["temperature"] = temperature
    if seed is not None:
        kwargs["seed"] = seed

    def call() -> tuple[str, int]:
        resp = client.chat.completions.create(model=model, messages=messages, **kwargs)
        return resp.choices[0].message.content or "", resp.usage.total_tokens

    # The public demo sets a small value so a visitor is not left waiting through long backoffs.
    attempts = int(os.environ.get("SECURERAG_GROQ_ATTEMPTS", "8"))
    return call_with_retries(call, (RateLimitError, APIConnectionError), attempts=attempts)


def call_with_retries(call, retryable: tuple, attempts: int = 8, sleep=time.sleep):
    """Retry rate limits and network faults (timeouts are connection errors) with backoff,
    so a flaky connection does not stop a multi-day run. Cached answers are never re-asked."""
    for attempt in range(attempts):
        try:
            return call()
        except retryable:
            if attempt == attempts - 1:
                break
            sleep(min(60, 5 * 2**attempt))
    raise RuntimeError("Groq not reachable or rate limit not clearing; resume later")


def groq_client(cfg: Config | None = None) -> LLMClient:
    cfg = cfg or Config()
    return LLMClient(
        groq_backend,
        cfg.groq_model,
        cfg.temperature,
        cfg.seed,
        settings={
            "reasoning_effort": cfg.reasoning_effort,
            "max_completion_tokens": cfg.max_completion_tokens,
        },
        budget=TokenBudget(DEFAULT_DIR, cfg.groq_model, RATE_LIMITS[cfg.groq_model]),
        expected_completion_tokens=cfg.expected_completion_tokens,
    )


def guard_client(cfg: Config | None = None) -> LLMClient:
    """Prompt Guard is a classifier: no sampling settings, and it returns a score string."""
    cfg = cfg or Config()
    model = cfg.prompt_guard_model
    return LLMClient(
        groq_backend,
        model,
        None,
        None,
        budget=TokenBudget(DEFAULT_DIR, model, RATE_LIMITS[model]),
        expected_completion_tokens=8,
    )
