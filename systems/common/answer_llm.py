"""Answer-LLM wrapper for Qwen 3 32B via Groq free tier.

This is the *single* module all three systems (A, B, C) call to get an
answer.  The prompt template, temperature, model, and cache key scheme are
fixed here — any change to any of these requires a decisions-log entry.

Design:
- Delegates to GroqClient for HTTP 429 backoff, rate-limit throttling, and
  persistent disk caching (eval/cache/answers/).
- Cache key = SHA-256(system_prompt + user_prompt + model_id + temperature)
  as implemented in systems.common.cache.request_hash.
- Returns a typed AnswerResult with (answer, tokens_in, tokens_out,
  latency_ms, cache_hit).

Controlled variables (must be identical across A, B, C):
  - ANSWER_LLM_MODEL     (eval.config)
  - ANSWER_TEMPERATURE   (eval.config)
  - ANSWER_SYSTEM_PROMPT (eval.config)
  - ANSWER_USER_PROMPT_TEMPLATE (eval.config)
  - TOP_K                (eval.config — used by callers, not here)
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from eval.config import (
    ANSWER_CACHE_DIR,
    ANSWER_LLM_MODEL,
    ANSWER_MAX_TOKENS,
    ANSWER_SYSTEM_PROMPT,
    ANSWER_TEMPERATURE,
    ANSWER_USER_PROMPT_TEMPLATE,
    GROQ_BACKOFF_BASE,
    GROQ_BACKOFF_MAX,
    GROQ_MAX_RETRIES,
    GROQ_RPM,
    GROQ_TPM,
)
from systems.common.cache import ResponseCache
from systems.common.groq_client import GroqClient, GroqResult


@dataclass(frozen=True)
class AnswerResult:
    answer: str
    tokens_in: int
    tokens_out: int
    latency_ms: float
    cache_hit: bool
    prompt_sha256: str


# Module-level client pool keyed by resolved cache_dir. One client per distinct
# cache_dir per process; repeated calls with the same dir reuse the client so
# rate-limit and token budgets are shared, while tests passing a tmp cache_dir
# get their own isolated client instead of silently inheriting the first one.
_clients: dict[Path, GroqClient] = {}


def _get_client(cache_dir: Path | None = None) -> GroqClient:
    key = Path(cache_dir or ANSWER_CACHE_DIR).resolve()
    client = _clients.get(key)
    if client is None:
        client = GroqClient(
            model=ANSWER_LLM_MODEL,
            rpm=GROQ_RPM,
            tpm=GROQ_TPM,
            cache=ResponseCache(key),
        )
        _clients[key] = client
    return client


def ask(
    question: str,
    context: str,
    *,
    cache_dir: Path | None = None,
) -> AnswerResult:
    """Ask the answer LLM a question given retrieved context.

    Parameters
    ----------
    question:
        The natural-language question (from questions.jsonl ``question`` field).
    context:
        Concatenated retrieved chunks (formatted by the caller).
    cache_dir:
        Override the answer cache directory (useful in tests).

    Returns
    -------
    AnswerResult
    """
    user_prompt = ANSWER_USER_PROMPT_TEMPLATE.format(
        context=context.strip(),
        question=question.strip(),
    )
    client = _get_client(cache_dir)
    result: GroqResult = client.complete(
        prompt=user_prompt,
        system=ANSWER_SYSTEM_PROMPT,
        temperature=ANSWER_TEMPERATURE,
        max_tokens=ANSWER_MAX_TOKENS,
    )
    return AnswerResult(
        answer=result.text,
        tokens_in=result.tokens_in,
        tokens_out=result.tokens_out,
        latency_ms=result.latency_ms,
        cache_hit=result.cache_hit,
        prompt_sha256=result.prompt_sha256,
    )
