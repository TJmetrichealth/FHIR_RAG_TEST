"""Rate-limit-aware Groq client with HTTP 429 exponential backoff and response cache.

Free-tier budgets (per model, per API key) as of v2 decisions:
  - 30 requests/minute
  - 6,000 tokens/minute (the real bottleneck for ~650-token calls)
  - 14,400 requests/day

The client enforces a local token-minute budget so we never hit the server-side
limit; on an unexpected 429, it backs off exponentially (2s, 4s, 8s, 16s, 32s, 60s)
up to 6 retries before raising.

Every successful call is persisted via systems.common.cache.ResponseCache —
no call is ever made twice for the same (model, system, prompt, temperature).
"""
from __future__ import annotations

import os
import random
import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .cache import CachedResponse, ResponseCache, request_hash


DEFAULT_RPM = 30
DEFAULT_TPM = 6_000
MAX_RETRIES = 6
_BASE_DELAY = 2.0
_MAX_DELAY = 60.0


@dataclass
class GroqResult:
    text: str
    tokens_in: int
    tokens_out: int
    model: str
    prompt_sha256: str
    latency_ms: float
    cache_hit: bool


class _TokenBucket:
    """Sliding-window limiter for requests-per-minute and tokens-per-minute.

    Thread-safe: a single lock guards both internal deques. Required because
    the eval harness uses a ThreadPoolExecutor when run with --concurrency K>1
    (decisions log: 2026-05-06 concurrency entry).
    """

    def __init__(self, rpm: int, tpm: int) -> None:
        self.rpm = rpm
        self.tpm = tpm
        self._req_times: deque[float] = deque()
        self._tok_events: deque[tuple[float, int]] = deque()
        self._lock = threading.Lock()

    def _expire(self, now: float) -> None:
        # caller holds self._lock
        cutoff = now - 60.0
        while self._req_times and self._req_times[0] < cutoff:
            self._req_times.popleft()
        while self._tok_events and self._tok_events[0][0] < cutoff:
            self._tok_events.popleft()

    def wait(self, tokens_needed: int) -> None:
        while True:
            with self._lock:
                now = time.monotonic()
                self._expire(now)
                used_tokens = sum(t for _, t in self._tok_events)
                if (
                    len(self._req_times) < self.rpm
                    and used_tokens + tokens_needed <= self.tpm
                ):
                    return
                next_release = min(
                    (self._req_times[0] + 60.0) if self._req_times else now + 0.1,
                    (self._tok_events[0][0] + 60.0) if self._tok_events else now + 0.1,
                )
                sleep_for = max(0.05, next_release - now)
            time.sleep(sleep_for)

    def record(self, tokens: int) -> None:
        with self._lock:
            now = time.monotonic()
            self._req_times.append(now)
            self._tok_events.append((now, tokens))


class GroqClient:
    """Thin wrapper around the official Groq SDK with caching + rate limiting."""

    def __init__(
        self,
        model: str,
        *,
        api_key: str | None = None,
        rpm: int = DEFAULT_RPM,
        tpm: int = DEFAULT_TPM,
        cache: ResponseCache | None = None,
        cache_dir: Path | None = None,
    ) -> None:
        self.model = model
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.bucket = _TokenBucket(rpm, tpm)
        self.cache = cache or ResponseCache(cache_dir or Path("eval/cache"))
        self._client: Any = None

    def _ensure_client(self) -> Any:
        if self._client is None:
            if not self.api_key:
                raise RuntimeError(
                    "GROQ_API_KEY is not set. Create a Groq account (free tier, no "
                    "credit card) at https://console.groq.com and export GROQ_API_KEY."
                )
            from groq import Groq  # type: ignore

            self._client = Groq(api_key=self.api_key)
        return self._client

    def complete(
        self,
        prompt: str,
        *,
        system: str = "",
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> GroqResult:
        key = request_hash(
            model=self.model, prompt=prompt, temperature=temperature, system=system
        )
        cached = self.cache.get(self.model, key)
        if cached is not None:
            return GroqResult(
                text=cached.text,
                tokens_in=cached.tokens_in,
                tokens_out=cached.tokens_out,
                model=cached.model,
                prompt_sha256=cached.prompt_sha256,
                latency_ms=cached.latency_ms,
                cache_hit=True,
            )

        # Rough pre-request token estimate: ~4 chars / token + expected output.
        est_tokens = max(1, int(len(prompt) / 4) + max_tokens)
        self.bucket.wait(est_tokens)

        client = self._ensure_client()
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        attempt = 0
        last_exc: Exception | None = None
        while attempt <= MAX_RETRIES:
            t0 = time.perf_counter()
            try:
                resp = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                latency_ms = (time.perf_counter() - t0) * 1000.0
                text = (resp.choices[0].message.content or "").strip()
                usage = getattr(resp, "usage", None)
                tokens_in = int(getattr(usage, "prompt_tokens", 0) or 0)
                tokens_out = int(getattr(usage, "completion_tokens", 0) or 0)
                self.bucket.record(tokens_in + tokens_out)
                cached = CachedResponse(
                    text=text,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    model=self.model,
                    prompt_sha256=key,
                    latency_ms=latency_ms,
                    raw={"model_snapshot": getattr(resp, "model", self.model)},
                )
                self.cache.put(self.model, key, cached)
                return GroqResult(
                    text=text,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    model=self.model,
                    prompt_sha256=key,
                    latency_ms=latency_ms,
                    cache_hit=False,
                )
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                msg = str(exc).lower()
                retriable = (
                    "429" in msg
                    or "rate limit" in msg
                    or "timeout" in msg
                    or "connection" in msg
                )
                if not retriable or attempt == MAX_RETRIES:
                    break
                delay = min(_MAX_DELAY, _BASE_DELAY * (2**attempt))
                # Full jitter
                delay = random.uniform(0.5 * delay, delay)
                time.sleep(delay)
                attempt += 1
        assert last_exc is not None
        raise last_exc
