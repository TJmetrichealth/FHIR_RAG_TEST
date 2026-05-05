"""Smoke tests for System B — Structured RAG (naive).

Test matrix:
  - 10 patients (sorted, first 10 from data/fhir_bundles/)
  - 5 questions (one per type: temporal_lookup, temporal_comparison,
    regimen_aggregation, regimen_compliance, cross_resource)
  - 1 question answered per patient (rotating across the 5 sample questions)

Assertions (smoke-level only — no accuracy checks):
  1. answer is a non-empty string.
  2. retrieved is a non-empty list (at least one chunk returned).
  3. Each retrieved item has "text", "source_id", "resource_type" keys.
  4. latency_ms is a finite positive number.
  5. tokens_in >= 1.
  6. tokens_out >= 1.

LLM caching: answer_llm.ask() caches on SHA-256(prompt). Re-running this
test does NOT make new Groq API calls for already-answered prompts.
"""
from __future__ import annotations

import math
from typing import Any

import pytest

from systems.base import BaseSystem, SystemResponse
from systems.structured_rag_naive import StructuredRAGNaive


# ---------------------------------------------------------------------------
# Module-level system instance (shared across all tests in this file)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def system_b() -> StructuredRAGNaive:
    """Single StructuredRAGNaive instance reused across all smoke tests in this module."""
    return StructuredRAGNaive()


# ---------------------------------------------------------------------------
# Parametrised smoke tests
# ---------------------------------------------------------------------------

@pytest.mark.smoke
class TestStructuredRAGNaiveSmoke:
    """End-to-end smoke tests for System B (Structured RAG, naive)."""

    def test_satisfies_base_protocol(self, system_b: StructuredRAGNaive) -> None:
        """System B must satisfy the BaseSystem protocol (structural check)."""
        assert isinstance(system_b, BaseSystem), (
            "StructuredRAGNaive does not satisfy the BaseSystem protocol. "
            "Check that it has an answer(question, patient_id) -> SystemResponse method."
        )

    @pytest.mark.parametrize("patient_index", list(range(10)))
    def test_one_question_per_patient(
        self,
        patient_index: int,
        patient_ids: list[str],
        sample_questions: list[dict[str, Any]],
        system_b: StructuredRAGNaive,
    ) -> None:
        """For each of the 10 patients, answer one question and validate the response shape.

        The question is chosen by rotating across the 5 sample questions
        (patient_index % 5) so all question types appear in the matrix.
        """
        patient_id = patient_ids[patient_index]
        question_dict = sample_questions[patient_index % len(sample_questions)]
        question_text = question_dict["question"]

        response: SystemResponse = system_b.answer(question_text, patient_id)

        # 1. Answer is a non-empty string
        assert isinstance(response.answer, str), (
            f"[System B] patient={patient_id} type={question_dict['type']}: "
            f"answer must be a str, got {type(response.answer)}"
        )
        assert response.answer.strip(), (
            f"[System B] patient={patient_id} type={question_dict['type']}: "
            "answer is empty or whitespace-only"
        )

        # 2. Retrieved list is non-empty
        assert isinstance(response.retrieved, list), (
            f"[System B] patient={patient_id}: retrieved must be a list"
        )
        assert len(response.retrieved) >= 1, (
            f"[System B] patient={patient_id} type={question_dict['type']}: "
            "retrieved list is empty — no chunks returned"
        )

        # 3. Each retrieved item has required keys (B adds resource_type)
        for i, chunk in enumerate(response.retrieved):
            assert "text" in chunk, (
                f"[System B] patient={patient_id} chunk[{i}] missing 'text' key"
            )
            assert "source_id" in chunk, (
                f"[System B] patient={patient_id} chunk[{i}] missing 'source_id' key"
            )
            assert "resource_type" in chunk, (
                f"[System B] patient={patient_id} chunk[{i}] missing 'resource_type' key"
            )
            assert chunk["text"].strip(), (
                f"[System B] patient={patient_id} chunk[{i}] 'text' is empty"
            )

        # 4. Latency is finite and positive
        assert math.isfinite(response.latency_ms), (
            f"[System B] patient={patient_id}: latency_ms is not finite: {response.latency_ms}"
        )
        assert response.latency_ms > 0, (
            f"[System B] patient={patient_id}: latency_ms is non-positive: {response.latency_ms}"
        )

        # 5. Token counts are positive integers
        assert isinstance(response.tokens_in, int) and response.tokens_in >= 1, (
            f"[System B] patient={patient_id}: tokens_in={response.tokens_in} must be >= 1"
        )
        assert isinstance(response.tokens_out, int) and response.tokens_out >= 1, (
            f"[System B] patient={patient_id}: tokens_out={response.tokens_out} must be >= 1"
        )
