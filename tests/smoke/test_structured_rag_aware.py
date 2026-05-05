"""Smoke tests for System C — Structured RAG (resource-aware).

Test matrix:
  - 10 patients (sorted, first 10 from data/fhir_bundles/)
  - 5 questions (one per type: temporal_lookup, temporal_comparison,
    regimen_aggregation, regimen_compliance, cross_resource)
  - 1 question answered per patient (rotating across the 5 sample questions)

Assertions (smoke-level only — no accuracy checks):
  1. answer is a non-empty string.
  2. retrieved (primary chunks) is a non-empty list.
  3. Each primary chunk has "text", "source_id", "resource_type", "role" keys.
  4. role == "primary" for all primary chunks.
  5. extras["expansion_chunks"] is a list (may be empty for patients with no references).
  6. Each expansion chunk has "text" and "role" == "expansion" keys.
  7. latency_ms is a finite positive number.
  8. tokens_in >= 1.
  9. tokens_out >= 1.
 10. route_question() returns the correct type (deterministic router check on
     a representative question — fast, no API call).

LLM caching: answer_llm.ask() caches on SHA-256(prompt). Re-running this
test does NOT make new Groq API calls for already-answered prompts.
"""
from __future__ import annotations

import math
from typing import Any

import pytest

from systems.base import BaseSystem, SystemResponse
from systems.structured_rag_aware import StructuredRAGAware, route_question


# ---------------------------------------------------------------------------
# Module-level system instance (shared across all tests in this file)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def system_c() -> StructuredRAGAware:
    """Single StructuredRAGAware instance reused across all smoke tests in this module."""
    return StructuredRAGAware()


# ---------------------------------------------------------------------------
# Parametrised smoke tests
# ---------------------------------------------------------------------------

@pytest.mark.smoke
class TestStructuredRAGAwareSmoke:
    """End-to-end smoke tests for System C (Structured RAG, resource-aware)."""

    def test_satisfies_base_protocol(self, system_c: StructuredRAGAware) -> None:
        """System C must satisfy the BaseSystem protocol (structural check)."""
        assert isinstance(system_c, BaseSystem), (
            "StructuredRAGAware does not satisfy the BaseSystem protocol. "
            "Check that it has an answer(question, patient_id) -> SystemResponse method."
        )

    def test_router_deterministic(self) -> None:
        """route_question() must return expected types for canonical questions.

        This is a fast, no-API-call unit check on the router table embedded
        in structured_rag_aware.py.  It must pass before any system C call.
        """
        # Administration keywords -> MedicationAdministration
        result = route_question("When was the last dose administered?")
        assert "MedicationAdministration" in result, (
            f"Router returned {result!r} for 'last dose administered' — "
            "expected MedicationAdministration in result"
        )

        # Prescription / regimen keywords -> MedicationRequest
        result2 = route_question("What is the patient's current prescription schedule?")
        assert "MedicationRequest" in result2, (
            f"Router returned {result2!r} for 'prescription schedule' — "
            "expected MedicationRequest in result"
        )

        # Patient demographics -> Patient
        result3 = route_question("What is the patient's date of birth?")
        assert "Patient" in result3, (
            f"Router returned {result3!r} for 'date of birth' — "
            "expected Patient in result"
        )

    @pytest.mark.parametrize("patient_index", list(range(10)))
    def test_one_question_per_patient(
        self,
        patient_index: int,
        patient_ids: list[str],
        sample_questions: list[dict[str, Any]],
        system_c: StructuredRAGAware,
    ) -> None:
        """For each of the 10 patients, answer one question and validate the response shape.

        The question is chosen by rotating across the 5 sample questions
        (patient_index % 5) so all question types appear in the matrix.
        """
        patient_id = patient_ids[patient_index]
        question_dict = sample_questions[patient_index % len(sample_questions)]
        question_text = question_dict["question"]

        response: SystemResponse = system_c.answer(question_text, patient_id)

        # 1. Answer is a non-empty string
        assert isinstance(response.answer, str), (
            f"[System C] patient={patient_id} type={question_dict['type']}: "
            f"answer must be a str, got {type(response.answer)}"
        )
        assert response.answer.strip(), (
            f"[System C] patient={patient_id} type={question_dict['type']}: "
            "answer is empty or whitespace-only"
        )

        # 2. Primary retrieved list is non-empty
        assert isinstance(response.retrieved, list), (
            f"[System C] patient={patient_id}: retrieved must be a list"
        )
        assert len(response.retrieved) >= 1, (
            f"[System C] patient={patient_id} type={question_dict['type']}: "
            "retrieved (primary) list is empty — no chunks returned"
        )

        # 3. Each primary chunk has required keys
        for i, chunk in enumerate(response.retrieved):
            assert "text" in chunk, (
                f"[System C] patient={patient_id} primary chunk[{i}] missing 'text' key"
            )
            assert "source_id" in chunk, (
                f"[System C] patient={patient_id} primary chunk[{i}] missing 'source_id' key"
            )
            assert "resource_type" in chunk, (
                f"[System C] patient={patient_id} primary chunk[{i}] missing 'resource_type' key"
            )
            assert chunk["text"].strip(), (
                f"[System C] patient={patient_id} primary chunk[{i}] 'text' is empty"
            )

        # 4. Primary chunks carry role="primary"
        for i, chunk in enumerate(response.retrieved):
            assert chunk.get("role") == "primary", (
                f"[System C] patient={patient_id} primary chunk[{i}] role={chunk.get('role')!r}, "
                "expected 'primary'"
            )

        # 5. extras["expansion_chunks"] exists and is a list
        assert "expansion_chunks" in response.extras, (
            f"[System C] patient={patient_id}: extras missing 'expansion_chunks' key"
        )
        expansion = response.extras["expansion_chunks"]
        assert isinstance(expansion, list), (
            f"[System C] patient={patient_id}: expansion_chunks must be a list, "
            f"got {type(expansion)}"
        )

        # 6. Each expansion chunk has required keys and role="expansion"
        for i, chunk in enumerate(expansion):
            assert "text" in chunk, (
                f"[System C] patient={patient_id} expansion chunk[{i}] missing 'text' key"
            )
            assert chunk.get("role") == "expansion", (
                f"[System C] patient={patient_id} expansion chunk[{i}] "
                f"role={chunk.get('role')!r}, expected 'expansion'"
            )

        # 7. Latency is finite and positive
        assert math.isfinite(response.latency_ms), (
            f"[System C] patient={patient_id}: latency_ms is not finite: {response.latency_ms}"
        )
        assert response.latency_ms > 0, (
            f"[System C] patient={patient_id}: latency_ms is non-positive: {response.latency_ms}"
        )

        # 8-9. Token counts are positive integers
        assert isinstance(response.tokens_in, int) and response.tokens_in >= 1, (
            f"[System C] patient={patient_id}: tokens_in={response.tokens_in} must be >= 1"
        )
        assert isinstance(response.tokens_out, int) and response.tokens_out >= 1, (
            f"[System C] patient={patient_id}: tokens_out={response.tokens_out} must be >= 1"
        )
