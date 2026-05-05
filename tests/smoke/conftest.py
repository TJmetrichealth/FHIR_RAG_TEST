"""Shared fixtures for smoke tests (Systems A, B, C).

Patient selection: sorted filenames under data/fhir_bundles/, first 10.
Question selection: one question per type (5 types) taken from questions.jsonl
  for the first patient whose records contain all five types.

Invariants:
- Dataset is frozen (dataset-freeze-v1). Do NOT write to data/ or questions/.
- LLM calls are cached in eval/cache/ — must be preserved across runs.
- No accuracy assertions here (that is W3 T3.2 for the evaluator).
- Schema uses 'question' and 'type' fields (W1 retrospective note).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Paths (absolute, resolved from project root via eval.config)
# ---------------------------------------------------------------------------
from eval.config import FHIR_BUNDLES_DIR, QUESTIONS_PATH

# ---------------------------------------------------------------------------
# The 5 question families / types in the bank
# ---------------------------------------------------------------------------
QUESTION_TYPES: list[str] = [
    "temporal_lookup",
    "temporal_comparison",
    "regimen_aggregation",
    "regimen_compliance",
    "cross_resource",
]


def _load_patient_ids() -> list[str]:
    """Return the first 10 patient IDs, deterministically (sorted filenames)."""
    bundle_files = sorted(FHIR_BUNDLES_DIR.glob("*.json"))
    return [f.stem for f in bundle_files[:10]]


def _load_sample_questions(patient_ids: list[str]) -> list[dict[str, Any]]:
    """Return exactly 1 question per question type from questions.jsonl.

    Strategy: for each type, take the first question (in file order) whose
    patient_id is in the 10-patient sample.  This keeps the smoke matrix
    small: 5 questions total (not 5 × 10 = 50), so the smoke suite is fast
    and stays well inside the Groq free-tier budget.

    All 5 selected questions will share the same patient_id if that patient
    has all 5 types, or will span different patients otherwise.
    """
    patient_set = set(patient_ids)
    sample: dict[str, dict[str, Any]] = {}  # type -> first matching question

    with QUESTIONS_PATH.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            q = json.loads(line)
            qtype = q.get("type", "")
            pid = q.get("patient_id", "")
            if qtype in QUESTION_TYPES and qtype not in sample and pid in patient_set:
                sample[qtype] = q
            if len(sample) == len(QUESTION_TYPES):
                break  # all five found

    # Return in the canonical order
    return [sample[t] for t in QUESTION_TYPES if t in sample]


# ---------------------------------------------------------------------------
# Module-level fixtures (computed once per test session)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def patient_ids() -> list[str]:
    """10 patient IDs, deterministically selected."""
    ids = _load_patient_ids()
    assert len(ids) == 10, (
        f"Expected 10 patient IDs from {FHIR_BUNDLES_DIR}; got {len(ids)}. "
        "Check that data/fhir_bundles/ has at least 10 bundles."
    )
    return ids


@pytest.fixture(scope="session")
def sample_questions() -> list[dict[str, Any]]:
    """One question per type (5 questions) from within the 10-patient sample."""
    ids = _load_patient_ids()
    qs = _load_sample_questions(ids)
    assert len(qs) == len(QUESTION_TYPES), (
        f"Could not find one question per type for the 10-patient sample. "
        f"Found types: {[q['type'] for q in qs]}"
    )
    return qs
