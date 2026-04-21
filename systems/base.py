"""System interface — the protocol all three retrieval systems must implement.

Systems A, B, and C each expose a single ``answer`` method with this exact
signature.  The eval harness (eval/harness.py) calls this method and expects
a ``SystemResponse`` back.

Protocol (structural subtyping):
    A class satisfies BaseSystem if it has an ``answer`` method that accepts
    (question: str, patient_id: str) and returns SystemResponse.

Usage in eval harness::

    from systems.base import SystemResponse
    response: SystemResponse = system.answer(question, patient_id)

Do NOT import concrete systems here — this module must be importable with
zero side effects (no model loading, no disk I/O).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class SystemResponse:
    """Return value of BaseSystem.answer().

    Attributes
    ----------
    answer:
        The system's text answer to the question.
    retrieved:
        The chunks / resources that were retrieved and passed to the LLM.
        Each element is a plain dict so it serialises cleanly to JSON.
        At minimum each dict should have ``"text"`` and ``"source_id"``
        keys; systems may add ``"score"``, ``"resource_type"``, etc.
    tokens_in:
        Prompt tokens consumed by the answer LLM.
    tokens_out:
        Completion tokens produced by the answer LLM.
    latency_ms:
        Wall-clock milliseconds from ``answer()`` entry to return.
    extras:
        Optional bag for system-specific metadata (e.g. System C's
        filter decisions, resource traversal graph).  Not used for
        scoring; preserved verbatim in the JSONL trace.
    """

    answer: str
    retrieved: list[dict[str, Any]]
    tokens_in: int
    tokens_out: int
    latency_ms: float
    extras: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class BaseSystem(Protocol):
    """Protocol that Systems A, B, and C must satisfy.

    Structural (duck-typed) — no need to inherit from BaseSystem.
    The eval harness uses ``isinstance(system, BaseSystem)`` to validate
    the contract at startup.
    """

    def answer(self, question: str, patient_id: str) -> SystemResponse:
        """Answer *question* for *patient_id*.

        Parameters
        ----------
        question:
            Natural-language question string (``question`` field from
            ``questions.jsonl``).
        patient_id:
            UUID string identifying the patient (``patient_id`` field from
            ``questions.jsonl``).  The system uses this to locate the correct
            FHIR bundle / narrative(s).

        Returns
        -------
        SystemResponse
        """
        ...
