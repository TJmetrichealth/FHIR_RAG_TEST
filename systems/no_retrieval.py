"""System N: no-retrieval baseline (reviewer revision #3).

Passes the question text directly to the answer LLM with empty context. The
intent is to decompose absolute accuracy on each question into a
"question-text-attributable" floor (this system) and a
"retrieval-attributable" remainder (Systems A/B/C minus this).

Cache-key isolation: the answer-LLM cache key is
SHA256(system_prompt + user_prompt + model + temperature). Because the user
prompt has an empty context, the cache key differs from any A/B/C call, so
existing cached entries are not shadowed.

No new hyperparameters are introduced. Temperature, model, system prompt and
the user-prompt template all come from ``eval.config``.
"""
from __future__ import annotations

import time
from pathlib import Path

from systems.base import SystemResponse
from systems.common.answer_llm import ask as answer_llm_ask


class NoRetrieval:
    """Question-text-only baseline. No FHIR access, no narrative, no chunks."""

    def __init__(
        self,
        *,
        name: str = "system_n_noretrieval",
        cache_dir: Path | None = None,
    ) -> None:
        self.name = name
        # Allow callers to route this system to a separate cache directory
        # without monkey-patching the module-level default. The
        # ``answer_llm.ask`` wrapper accepts a ``cache_dir`` override.
        self._cache_dir = cache_dir

    def answer(self, question: str, patient_id: str) -> SystemResponse:
        """Answer *question* for *patient_id* with no retrieved context.

        ``patient_id`` is accepted for interface compatibility with the
        BaseSystem protocol but is unused: this baseline does not look at any
        per-patient artefact. The question string is the only signal.

        Parameters
        ----------
        question:
            Natural-language question string.
        patient_id:
            Ignored. Present for protocol compatibility.

        Returns
        -------
        SystemResponse
            answer, empty retrieved list, tokens_in/out, latency_ms.
        """
        t0 = time.perf_counter()
        if self._cache_dir is None:
            llm_result = answer_llm_ask(question=question, context="")
        else:
            llm_result = answer_llm_ask(
                question=question, context="", cache_dir=self._cache_dir
            )
        latency_ms = (time.perf_counter() - t0) * 1000.0
        return SystemResponse(
            answer=llm_result.answer,
            retrieved=[],
            tokens_in=llm_result.tokens_in,
            tokens_out=llm_result.tokens_out,
            latency_ms=latency_ms,
            extras={
                "system": self.name,
                "cache_hit": llm_result.cache_hit,
                "prompt_sha256": llm_result.prompt_sha256,
                "patient_id_ignored": patient_id,
            },
        )
