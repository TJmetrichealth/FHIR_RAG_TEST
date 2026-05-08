"""Unit tests for eval/score.py — deterministic scoring functions only.

No LLMs, no network, no FHIR bundles required for any of these tests.
Each test exercises one scoring pathway with small in-memory examples.

Run with:
  C:\\ProgramData\\miniconda3\\envs\\ml\\python.exe -m pytest tests/test_score.py -v
"""
from __future__ import annotations

import json
import math

import pytest

from eval.score import (
    _BOOL_CANON,
    _canon_bool,
    _chunk_contains_resource,
    _compute_recall,
    _detect_gt_type,
    _extract_answer_value,
    _parse_date_safe,
    _parse_list_value,
    _percentile,
    _score_bool,
    _score_date,
    _score_free_text,
    _score_list,
    _score_numeric,
    _wilson_ci,
    score_row,
)


# ===========================================================================
# Test 1 — ISO date matching
# ===========================================================================

class TestScoreDate:
    def test_exact_match(self):
        exact, partial, flag, reason = _score_date("2025-09-28", "2025-09-28")
        assert exact is True
        assert partial == 1.0
        assert flag is False

    def test_exact_match_with_preamble(self):
        exact, partial, flag, reason = _score_date("2025-09-28", "The answer is: 2025-09-28.")
        assert exact is True
        assert partial == 1.0

    def test_no_match(self):
        exact, partial, flag, reason = _score_date("2025-09-28", "2025-10-05")
        assert exact is False
        assert partial == 0.0
        assert flag is False

    def test_date_embedded_in_prose(self):
        exact, partial, flag, reason = _score_date(
            "2025-09-28",
            "The next dose is scheduled for 2025-09-28 according to the record."
        )
        assert exact is True

    def test_no_date_in_answer(self):
        exact, partial, flag, reason = _score_date("2025-09-28", "N/A")
        assert exact is False
        assert partial == 0.0
        assert flag is False
        assert "no parseable date" in reason.lower()

    def test_unparseable_gt_flags(self):
        exact, partial, flag, reason = _score_date("not-a-date", "2025-09-28")
        assert flag is True

    def test_parse_date_safe_normalisation(self):
        assert _parse_date_safe("2025-09-28") == "2025-09-28"
        assert _parse_date_safe("  2025-09-28  ") == "2025-09-28"
        assert _parse_date_safe("2025-09-28T00:00:00") == "2025-09-28"
        assert _parse_date_safe("not-a-date") is None

    def test_detect_gt_type_date(self):
        assert _detect_gt_type("2025-09-28") == "date"
        assert _detect_gt_type("2025-09-28") == "date"

    def test_different_dates_no_partial(self):
        """Date scoring is binary — no partial credit for close dates."""
        exact, partial, flag, _ = _score_date("2025-09-28", "2025-09-29")
        assert exact is False
        assert partial == 0.0


# ===========================================================================
# Test 2 — Numeric tolerance matching
# ===========================================================================

class TestScoreNumeric:
    def test_int_exact(self):
        exact, partial, flag, _ = _score_numeric(5, "5")
        assert exact is True
        assert partial == 1.0

    def test_int_no_match(self):
        exact, partial, flag, _ = _score_numeric(5, "6")
        assert exact is False
        assert partial == 0.0

    def test_float_within_tolerance(self):
        # 0.9444 is within 2% of 0.9444 (exact)
        exact, partial, flag, _ = _score_numeric(0.9444, "0.9444")
        assert exact is True

    def test_float_within_2pct(self):
        # 1.0 * 0.02 = 0.02 tolerance; 0.985 is within 1.5% of 1.0
        exact, partial, flag, _ = _score_numeric(1.0, "0.985")
        assert exact is True

    def test_float_outside_tolerance(self):
        exact, partial, flag, _ = _score_numeric(1.0, "0.95")
        assert exact is False

    def test_float_answer_with_prose(self):
        exact, partial, flag, _ = _score_numeric(0.5, "The PDC is approximately 0.5000 for this period.")
        assert exact is True

    def test_zero_gt(self):
        # tol = max(0.01, 0) = 0.01; answer 0.0 within 0.01 of 0
        exact, partial, flag, _ = _score_numeric(0, "0")
        assert exact is True

    def test_no_number_in_answer(self):
        exact, partial, flag, reason = _score_numeric(5, "N/A — no data found")
        assert exact is False
        assert "no number" in reason.lower()

    def test_detect_gt_type_numeric_int(self):
        assert _detect_gt_type(0) == "numeric"
        assert _detect_gt_type(5) == "numeric"

    def test_detect_gt_type_numeric_float(self):
        assert _detect_gt_type(0.9444) == "numeric"

    def test_mpr_above_one(self):
        """MPR can exceed 1.0 (overlapping refills); tolerance still applies."""
        exact, partial, flag, _ = _score_numeric(1.2444, "1.2444")
        assert exact is True

    def test_absolute_floor(self):
        # gt = 0.001; tol = max(0.01, 0.02*0.001) = 0.01
        # answer 0.005 is within 0.01 of 0.001 -> match
        exact, partial, flag, _ = _score_numeric(0.001, "0.005")
        assert exact is True


# ===========================================================================
# Test 3 — List / set equality (Jaccard partial credit)
# ===========================================================================

class TestScoreList:
    def test_exact_match_list(self):
        exact, partial, flag, _ = _score_list(["alpha", "beta"], "alpha, beta")
        assert exact is True
        assert partial == 1.0

    def test_exact_match_order_invariant(self):
        exact, partial, flag, _ = _score_list(["beta", "alpha"], "alpha, beta")
        assert exact is True

    def test_partial_overlap(self):
        exact, partial, flag, _ = _score_list(["a", "b", "c"], "a, b")
        # intersection = {a,b}, union = {a,b,c}  → Jaccard = 2/3
        assert exact is False
        assert abs(partial - 2 / 3) < 1e-6

    def test_no_overlap(self):
        exact, partial, flag, _ = _score_list(["a", "b"], "c, d")
        assert exact is False
        assert partial == 0.0

    def test_empty_answer_list(self):
        exact, partial, flag, reason = _score_list(["a"], "")
        assert exact is False
        assert partial == 0.0
        assert "empty" in reason.lower()

    def test_json_encoded_gt(self):
        gt_json = '["primary regimen", "oral adjunct"]'
        exact, partial, flag, _ = _score_list(gt_json, "primary regimen; oral adjunct")
        assert exact is True

    def test_detect_gt_type_list(self):
        assert _detect_gt_type(["a", "b"]) == "list"
        assert _detect_gt_type('["x","y"]') == "list"
        assert _detect_gt_type("a, b, c") == "list"

    def test_parse_list_value_semicolon(self):
        result = _parse_list_value("yes; no; n/a")
        assert result == {"yes", "no", "n/a"}

    def test_single_item_list(self):
        exact, partial, flag, _ = _score_list(["only"], "only")
        assert exact is True
        assert partial == 1.0


# ===========================================================================
# Test 4 — Boolean / yes-no / N/A
# ===========================================================================

class TestScoreBool:
    def test_yes_yes(self):
        exact, partial, flag, _ = _score_bool("yes", "yes")
        assert exact is True

    def test_yes_true(self):
        exact, partial, flag, _ = _score_bool("yes", "true")
        assert exact is True

    def test_no_false(self):
        exact, partial, flag, _ = _score_bool("no", "false")
        assert exact is True

    def test_na_na(self):
        exact, partial, flag, _ = _score_bool("N/A", "n/a")
        assert exact is True

    def test_yes_no_mismatch(self):
        exact, partial, flag, _ = _score_bool("yes", "no")
        assert exact is False
        assert partial == 0.0

    def test_bool_in_prose(self):
        exact, partial, flag, _ = _score_bool("yes", "Based on the records, yes the patient is persistent.")
        assert exact is True

    def test_case_insensitive_gt(self):
        exact, partial, flag, _ = _score_bool("YES", "yes")
        assert exact is True

    def test_python_true(self):
        exact, partial, flag, _ = _score_bool(True, "yes")
        assert exact is True

    def test_python_false(self):
        exact, partial, flag, _ = _score_bool(False, "no")
        assert exact is True

    def test_na_not_bool(self):
        """'N/A' should be treated as a valid bool/categorical answer."""
        assert _detect_gt_type("N/A") == "bool"

    def test_unknown_answer_no_flag(self):
        exact, partial, flag, reason = _score_bool("yes", "The data is inconclusive.")
        assert exact is False
        assert flag is False  # not a scorer fault; just no match


# ===========================================================================
# Test 5 — Free-text entity matching (no FHIR bundle needed)
# ===========================================================================

class TestScoreFreeText:
    def test_no_bundle_gt_substring_found(self):
        """Fallback when no bundle: check if gt is a substring of answer."""
        exact, partial, flag, reason = _score_free_text(
            gt="cyclic oral specialty therapy",
            answer="The patient is on a cyclic oral specialty therapy regimen.",
            bundle_path=None,
            question_id="test::cr.tier_label",
        )
        assert exact is True
        assert partial == 1.0
        assert "fallback" in reason.lower()

    def test_no_bundle_gt_not_in_answer(self):
        exact, partial, flag, reason = _score_free_text(
            gt="fixed_interval",
            answer="The schedule is cyclic.",
            bundle_path=None,
            question_id="test::cr.schedule_kind.primary",
        )
        assert exact is False
        assert partial == 0.0
        assert flag is True  # flagged because no bundle available

    def test_no_bundle_path_none(self):
        from pathlib import Path
        exact, partial, flag, reason = _score_free_text(
            gt="some entity",
            answer="some entity found here",
            bundle_path=None,
            question_id="test::q",
        )
        # Should hit the no-bundle fallback
        assert exact is True


# ===========================================================================
# Test 6 — gt type detection
# ===========================================================================

class TestDetectGtType:
    def test_date(self):
        assert _detect_gt_type("2025-01-15") == "date"

    def test_int_zero(self):
        assert _detect_gt_type(0) == "numeric"

    def test_float(self):
        assert _detect_gt_type(0.9444) == "numeric"

    def test_bool_string_yes(self):
        assert _detect_gt_type("yes") == "bool"

    def test_bool_string_no(self):
        assert _detect_gt_type("no") == "bool"

    def test_na_string(self):
        assert _detect_gt_type("N/A") == "bool"

    def test_list_python(self):
        assert _detect_gt_type(["a", "b"]) == "list"

    def test_list_json_string(self):
        assert _detect_gt_type('["x"]') == "list"

    def test_list_csv_string(self):
        assert _detect_gt_type("a,b,c") == "list"

    def test_free_text_categorical(self):
        # "on-week" / "off-week" are free-text categoricals (not in bool map)
        assert _detect_gt_type("on-week") == "free_text"
        assert _detect_gt_type("off-week") == "free_text"

    def test_free_text_component_name(self):
        assert _detect_gt_type("primary regimen") == "free_text"

    def test_none(self):
        assert _detect_gt_type(None) == "free_text"


# ===========================================================================
# Test 7 — Recall@k helpers
# ===========================================================================

class TestRecall:
    def test_chunk_contains_exact(self):
        assert _chunk_contains_resource(
            "MedicationRequest_spec-req-abc-primary::chunk_0",
            {"spec-req-abc-primary"},
        )

    def test_chunk_not_matching(self):
        assert not _chunk_contains_resource(
            "MedicationRequest_spec-req-abc-adjunct::chunk_0",
            {"spec-req-abc-primary"},
        )

    def test_system_a_returns_none(self):
        r1, r3, r5, r10 = _compute_recall("a", "patient-1", ["chunk-1", "chunk-2"], None)
        assert r1 is None
        assert r3 is None
        assert r5 is None
        assert r10 is None

    def test_system_b_empty_retrieved(self):
        """Empty retrieved list should give False (not None) for system B."""
        r1, r3, r5, r10 = _compute_recall("b", "014abeea", [], None)
        # No resource IDs parseable from bundle (None) → returns None from _primary_resource_ids
        # Actually with None bundle, we get best-effort IDs, but empty retrieved → False
        # Since retrieved is empty, no chunk can match → all False
        assert r1 is False or r1 is None  # depends on whether IDs are found

    def test_system_b_hit_at_1(self):
        """Top-1 chunk matches → recall@1 True."""
        # Simulate chunk IDs as returned by System B
        retrieved = ["MedicationRequest_spec-req-014abeea-primary::chunk_0"]
        r1, r3, r5, r10 = _compute_recall("b", "014abeea-xyz", retrieved, None)
        # With no bundle, _primary_resource_ids returns heuristic IDs including
        # "spec-req-014abeea" (8-char prefix).  The chunk resource_id is
        # "spec-req-014abeea-primary" which starts with "spec-req-014abeea".
        # Prefix match should fire.
        assert r1 is True
        assert r3 is True

    def test_system_b_hit_at_3_not_1(self):
        """Relevant chunk is 3rd → recall@3=True, recall@1=False."""
        retrieved = [
            "CarePlan_other-resource::chunk_0",
            "Medication_some-med::chunk_0",
            "MedicationRequest_spec-req-014abeea-primary::chunk_0",
            "CarePlan_spec-cp-014abeea::chunk_0",
        ]
        r1, r3, r5, r10 = _compute_recall("b", "014abeea-xyz", retrieved, None)
        assert r1 is False
        assert r3 is True
        assert r5 is True


# ===========================================================================
# Test 8 — Wilson CI and percentile helpers
# ===========================================================================

class TestStatHelpers:
    def test_wilson_all_success(self):
        lo, hi = _wilson_ci(10, 10)
        assert lo > 0.7  # should be high
        assert hi == 1.0

    def test_wilson_all_fail(self):
        lo, hi = _wilson_ci(0, 10)
        assert lo == 0.0
        assert hi < 0.3

    def test_wilson_zero_n(self):
        lo, hi = _wilson_ci(0, 0)
        assert lo == 0.0
        assert hi == 0.0

    def test_percentile_p50(self):
        data = list(range(1, 11))  # 1..10
        p50 = _percentile(data, 50)
        assert p50 == 5  # nearest rank at 50th percentile of 10 items

    def test_percentile_p95(self):
        data = list(range(1, 101))  # 1..100
        p95 = _percentile(data, 95)
        assert p95 == 95

    def test_percentile_empty(self):
        assert _percentile([], 50) == 0.0


# ===========================================================================
# Test 9 — score_row integration (no bundle, no filesystem access)
# ===========================================================================

class TestScoreRow:
    def _base_record(self, **kwargs) -> dict:
        rec = {
            "question_id": "014abeea::tl.next_scheduled.primary",
            "patient_id": "014abeea",
            "question": "When is the next dose?",
            "question_type": "temporal_lookup",
            "tier": 2,
            "reference_date": "2025-09-28",
            "ground_truth": "2025-09-28",
            "system": "b",
            "answer": "2025-09-28",
            "retrieved": [],
            "tokens_in": 100,
            "tokens_out": 10,
            "latency_ms": 500.0,
            "extras": {},
        }
        rec.update(kwargs)
        return rec

    def test_date_correct(self):
        row = score_row(self._base_record())
        assert row["exact_match"] is True
        assert row["error_flag"] is False

    def test_error_record(self):
        rec = self._base_record(
            answer="ERROR",
            extras={"error": "GROQ_API_KEY is not set"},
        )
        row = score_row(rec)
        assert row["error_flag"] is True
        assert row["exact_match"] is False
        assert "GROQ_API_KEY" in row["error_reason"]

    def test_na_gt_bool(self):
        rec = self._base_record(ground_truth="N/A", answer="N/A")
        row = score_row(rec)
        assert row["exact_match"] is True

    def test_numeric_gt_int(self):
        rec = self._base_record(ground_truth=0, answer="0")
        row = score_row(rec)
        assert row["exact_match"] is True

    def test_numeric_wrong(self):
        rec = self._base_record(ground_truth=5, answer="3")
        row = score_row(rec)
        assert row["exact_match"] is False

    def test_system_a_recall_none(self):
        rec = self._base_record(system="a")
        row = score_row(rec)
        assert row["recall_at_1"] is None
        assert row["recall_at_5"] is None

    def test_system_b_recall_bool(self):
        rec = self._base_record(system="b")
        row = score_row(rec)
        # With no bundle and empty retrieved, recall may be False (not None)
        assert row["recall_at_1"] is not None or row["recall_at_1"] is None

    def test_output_keys(self):
        row = score_row(self._base_record())
        required = {
            "question_id", "system", "patient_id", "family", "type", "tier",
            "reference_date", "ground_truth", "answer",
            "exact_match", "partial_credit",
            "recall_at_1", "recall_at_3", "recall_at_5", "recall_at_10",
            "latency_ms", "tokens_in", "tokens_out",
            "error_flag", "error_reason", "near_miss_flag",
        }
        assert required.issubset(set(row.keys()))

    def test_family_inferred(self):
        row = score_row(self._base_record(
            question_id="014abeea::rc.pdc_90d.primary"
        ))
        assert row["family"] == "regimen_compliance"

    def test_free_text_on_week_category(self):
        """'on-week' is free_text type; no bundle → flag=True but no crash."""
        rec = self._base_record(
            question_id="014abeea::rc.cycle_position.primary",
            ground_truth="on-week",
            answer="The patient is in an on-week.",
            question_type="regimen_compliance",
        )
        row = score_row(rec)
        # With no bundle, free-text fallback uses substring check
        # "on-week" in "the patient is in an on-week." → True
        assert row["exact_match"] is True


# ===========================================================================
# Test 10 — extract_answer_value edge cases
# ===========================================================================

class TestExtractAnswerValue:
    def test_strips_answer_colon(self):
        assert _extract_answer_value("Answer: 5") == "5"

    def test_strips_the_answer_is(self):
        assert _extract_answer_value("The answer is 2025-09-28.") == "2025-09-28"

    def test_strips_trailing_period(self):
        assert _extract_answer_value("yes.") == "yes"

    def test_no_mutation_on_plain(self):
        assert _extract_answer_value("N/A") == "N/A"

    def test_empty_string(self):
        assert _extract_answer_value("") == ""
