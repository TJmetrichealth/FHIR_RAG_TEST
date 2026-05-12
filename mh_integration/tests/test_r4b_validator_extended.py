"""Extended tests for mh_integration.r4b_validator.

Covers:
  - One test per fixture (valid and invalid bundles)
  - walk_references: deep-nesting coverage with synthetic dict
  - resolve_reference: each possible return status code
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from mh_integration.r4b_validator import (
    ReferenceIndex,
    ValidationResult,
    build_reference_index,
    resolve_reference,
    validate_bundle,
    walk_references,
)


# ---------------------------------------------------------------------------
# Fixture-based tests
# ---------------------------------------------------------------------------


def test_valid_minimal_urn(fixture) -> None:
    """Bundle with urn:uuid cross-references must pass with zero errors."""
    result = validate_bundle(fixture("valid_minimal_urn.json"))
    assert isinstance(result, ValidationResult)
    assert result.passed is True, f"Expected pass, got errors: {result.errors}"
    assert result.error_count == 0


def test_valid_minimal_relative(fixture) -> None:
    """Bundle with ResourceType/id cross-references must pass with zero errors."""
    result = validate_bundle(fixture("valid_minimal_relative.json"))
    assert result.passed is True, f"Expected pass, got errors: {result.errors}"
    assert result.error_count == 0


def test_broken_subject_ref(fixture) -> None:
    """MedRequest.subject pointing at a non-existent urn must fail."""
    result = validate_bundle(fixture("broken_subject_ref.json"))
    assert result.passed is False
    assert result.error_count > 0
    combined = " ".join(result.errors)
    assert "DOES-NOT-EXIST" in combined, f"Expected 'DOES-NOT-EXIST' in errors: {result.errors}"
    # The json_path must mention the subject field
    assert "subject" in combined, f"Expected 'subject' in errors: {result.errors}"


def test_broken_nested_ref(fixture) -> None:
    """MedAdmin.context pointing at Encounter/MISSING must fail (proves walker is recursive)."""
    result = validate_bundle(fixture("broken_nested_ref.json"))
    assert result.passed is False
    assert result.error_count > 0
    combined = " ".join(result.errors)
    assert "MISSING" in combined, f"Expected 'MISSING' in errors: {result.errors}"
    assert "context" in combined, f"Expected 'context' mention in errors: {result.errors}"


def test_missing_careplan(fixture) -> None:
    """Bundle without a CarePlan must fail with 'CarePlan' in the error message."""
    result = validate_bundle(fixture("missing_careplan.json"))
    assert result.passed is False
    combined = " ".join(result.errors)
    assert "CarePlan" in combined, f"Expected 'CarePlan' in errors: {result.errors}"


def test_bad_status(fixture) -> None:
    """MedicationRequest with status='unknown-status' must fail."""
    result = validate_bundle(fixture("bad_status.json"))
    assert result.passed is False
    combined = " ".join(result.errors)
    assert "unknown-status" in combined, f"Expected 'unknown-status' in errors: {result.errors}"


def test_logical_reference(fixture) -> None:
    """Bundle with Practitioner?identifier=... logical ref must pass (logical refs are not errors)."""
    result = validate_bundle(fixture("logical_reference.json"))
    assert result.passed is True, f"Expected pass (logical ref is not error), got: {result.errors}"
    assert result.error_count == 0


def test_contained_resource(fixture) -> None:
    """MedRequest with #m1 contained reference must pass."""
    result = validate_bundle(fixture("contained_resource.json"))
    assert result.passed is True, f"Expected pass (contained ref resolves), got: {result.errors}"
    assert result.error_count == 0


# ---------------------------------------------------------------------------
# walk_references: deep nesting
# ---------------------------------------------------------------------------


def test_walk_references_deeply_nested() -> None:
    """walk_references must yield all Reference-shaped dicts at any depth."""
    node = {
        "resourceType": "MedicationAdministration",
        "id": "adm-deep",
        "subject": {"reference": "Patient/p-deep"},
        "context": {"reference": "Encounter/enc-deep"},
        "dosage": {
            "route": {
                "coding": [
                    {"system": "http://snomed.info/sct", "code": "47625008"},
                ]
            },
            "rateRatio": {
                "numerator": {
                    "extension": [
                        {"url": "http://hl7.org/fhir/ref", "valueReference": {"reference": "Observation/obs-1"}}
                    ]
                }
            }
        },
        "note": [
            {"authorReference": {"reference": "Practitioner/prac-1"}}
        ],
    }

    results = list(walk_references(node, "entry[0].resource"))

    ref_values = [r for _, r in results]
    paths = [p for p, _ in results]

    assert "Patient/p-deep" in ref_values
    assert "Encounter/enc-deep" in ref_values
    assert "Observation/obs-1" in ref_values
    assert "Practitioner/prac-1" in ref_values

    # Paths must be non-empty strings containing the parent path
    for p in paths:
        assert "entry[0].resource" in p, f"Path missing root prefix: {p}"


def test_walk_references_empty_node() -> None:
    """walk_references on an empty dict yields nothing."""
    assert list(walk_references({})) == []


def test_walk_references_no_references() -> None:
    """walk_references on a dict with no reference keys yields nothing."""
    node = {"resourceType": "Patient", "id": "p1", "birthDate": "1980-01-01"}
    assert list(walk_references(node)) == []


def test_walk_references_list_top_level() -> None:
    """walk_references handles a top-level list."""
    node = [
        {"reference": "Patient/a"},
        {"notARef": "x"},
        {"reference": "Patient/b"},
    ]
    results = list(walk_references(node, "root"))
    values = [v for _, v in results]
    assert "Patient/a" in values
    assert "Patient/b" in values
    assert len(values) == 2


# ---------------------------------------------------------------------------
# resolve_reference: each status code
# ---------------------------------------------------------------------------


def _make_index() -> ReferenceIndex:
    """Build a minimal ReferenceIndex for resolve_reference tests."""
    idx = ReferenceIndex()
    idx.by_full_url["urn:uuid:abc"] = ("Patient", "p1")
    idx.by_type_id[("Patient", "p1")] = "urn:uuid:abc"
    idx.by_type_id[("MedicationRequest", "mr1")] = "urn:uuid:mr-uuid"
    idx.by_full_url["urn:uuid:mr-uuid"] = ("MedicationRequest", "mr1")
    idx.contained_by_parent["parent-res"] = {"local1", "local2"}
    return idx


def test_resolve_full_url() -> None:
    idx = _make_index()
    status, target = resolve_reference("urn:uuid:abc", None, idx)
    assert status == "RESOLVED_FULL_URL"
    assert target == "urn:uuid:abc"


def test_resolve_type_id() -> None:
    idx = _make_index()
    status, target = resolve_reference("Patient/p1", None, idx)
    assert status == "RESOLVED_TYPE_ID"
    assert target == "Patient/p1"


def test_resolve_contained() -> None:
    idx = _make_index()
    status, target = resolve_reference("#local1", "parent-res", idx)
    assert status == "RESOLVED_CONTAINED"
    assert target == "local1"


def test_resolve_contained_missing_parent() -> None:
    idx = _make_index()
    status, _ = resolve_reference("#local1", "no-such-parent", idx)
    assert status == "UNRESOLVED"


def test_resolve_logical() -> None:
    idx = _make_index()
    status, _ = resolve_reference("Practitioner?identifier=http://example.org|123", None, idx)
    assert status == "LOGICAL_REFERENCE"


def test_resolve_external() -> None:
    idx = _make_index()
    status, _ = resolve_reference("https://example.org/fhir/Patient/remote", None, idx)
    assert status == "EXTERNAL"


def test_resolve_unresolved_urn() -> None:
    idx = _make_index()
    status, _ = resolve_reference("urn:uuid:does-not-exist", None, idx)
    assert status == "UNRESOLVED"


def test_resolve_unresolved_type_id() -> None:
    idx = _make_index()
    status, _ = resolve_reference("Encounter/MISSING", None, idx)
    assert status == "UNRESOLVED"


def test_resolve_empty_string() -> None:
    idx = _make_index()
    status, _ = resolve_reference("", None, idx)
    assert status == "UNRESOLVED"


# ---------------------------------------------------------------------------
# build_reference_index
# ---------------------------------------------------------------------------


def test_build_reference_index_basic() -> None:
    """build_reference_index correctly populates by_full_url and by_type_id."""
    raw = {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": [
            {
                "fullUrl": "urn:uuid:p1",
                "resource": {"resourceType": "Patient", "id": "p1"},
            },
            {
                "fullUrl": "urn:uuid:mr1",
                "resource": {
                    "resourceType": "MedicationRequest",
                    "id": "mr1",
                    "contained": [
                        {"resourceType": "Medication", "id": "m-local"}
                    ],
                },
            },
        ],
    }
    idx = build_reference_index(raw)
    assert ("Patient", "p1") in idx.by_type_id
    assert ("MedicationRequest", "mr1") in idx.by_type_id
    assert "urn:uuid:p1" in idx.by_full_url
    assert "urn:uuid:mr1" in idx.by_full_url
    # Contained resource indexed under parent
    assert "mr1" in idx.contained_by_parent
    assert "m-local" in idx.contained_by_parent["mr1"]
