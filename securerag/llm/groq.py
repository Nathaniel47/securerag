"""Groq backend. The SDK is imported lazily so tests and CI do not need it."""

import time

from securerag.config import Config, groq_api_key
from securerag.llm.client import LLMClient


def groq_backend(model: str, messages: list[dict], temperature: float, seed: int) -> str:
    from groq import Groq, RateLimitError

    key = groq_api_key()
    if not key:
        raise RuntimeError("SECURERAG_GROQ_API_KEY is not set")
    client = Groq(api_key=key)
    for attempt in range(6):
        try:
            resp = client.chat.completions.create(
                model=model, messages=messages, temperature=temperature, seed=seed, max_tokens=400
            )
            return resp.choices[0].message.content or ""
        except RateLimitError:
            time.sleep(min(60, 5 * 2**attempt))
    raise RuntimeError("Groq rate limit not clearing; resume later (responses are cached)")


def groq_client(cfg: Config | None = None) -> LLMClient:
    cfg = cfg or Config()
    return LLMClient(groq_backend, cfg.groq_model, cfg.temperature, cfg.seed)
