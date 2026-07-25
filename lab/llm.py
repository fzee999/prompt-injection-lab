"""chat(): the one door to the model.

Every part of the lab (the assistant, the attack harness, the defenses) sends
its messages through this function. That is what makes the model swappable,
and it gives one place to handle pacing, retries and bookkeeping: tokens,
latency, and which model actually answered.

The server speaks the OpenAI chat-completions format. Ollama and OpenRouter
both implement it, so the same OpenAI client works against either.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from openai import APIConnectionError, OpenAI, RateLimitError

from .config import get_settings

Message = dict[str, str]  # {"role": "system" | "user" | "assistant", "content": "..."}


@dataclass(frozen=True)
class ChatResult:
    text: str  # the reply, stripped of surrounding whitespace
    model: str  # model name the server reports; can differ from what was asked
    provider: str | None  # OpenRouter's backend when reported; None on Ollama
    prompt_tokens: int
    completion_tokens: int
    seconds: float  # wall-clock time of the call


_client: OpenAI | None = None
_last_call_at = 0.0


def client() -> OpenAI:
    """One shared connection, built on first use."""
    global _client
    if _client is None:
        s = get_settings()
        _client = OpenAI(base_url=s.base_url, api_key=s.api_key)
    return _client


def _pace() -> None:
    """Sleep so that consecutive calls are at least min_interval seconds apart."""
    global _last_call_at
    s = get_settings()
    if s.min_interval > 0:
        wait = s.min_interval - (time.monotonic() - _last_call_at)
        if wait > 0:
            time.sleep(wait)
    _last_call_at = time.monotonic()


def chat(
    messages: list[Message],
    *,
    model: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 512,
    retries: int = 3,
) -> ChatResult:
    """Send a conversation and return the reply plus bookkeeping.

    temperature=0 and a fixed seed make the model as repeatable as it can be,
    which matters when the same attack runs under several defense settings.
    Rate-limit and connection errors are retried with doubling back-off.
    """
    s = get_settings()
    extra: dict[str, Any] = {}
    if s.provider:  # OpenRouter-only routing hint; harmless elsewhere
        extra["provider"] = {"order": [s.provider], "allow_fallbacks": False}

    delay = 5.0
    for attempt in range(retries + 1):
        _pace()
        started = time.perf_counter()
        try:
            resp = client().chat.completions.create(
                model=model or s.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                seed=s.seed,
                extra_body=extra or None,
            )
        except (RateLimitError, APIConnectionError):
            if attempt == retries:
                raise
            time.sleep(delay)
            delay *= 2
            continue

        usage = resp.usage
        extras = getattr(resp, "model_extra", None) or {}
        return ChatResult(
            text=(resp.choices[0].message.content or "").strip(),
            model=resp.model,
            provider=extras.get("provider"),
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            seconds=time.perf_counter() - started,
        )
    raise AssertionError("unreachable")
