"""Tests for mh_integration.hl7_validator.

The jar-dependent test is skipped if tools/hl7-validator/validator_cli.jar
is not present. The allowlist-parsing test runs without the jar.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from mh_integration.hl7_validator import (
    HL7Issue,
    HL7ValidationResult,
    HL7Validator,
    _is_allowlisted,
    _load_allowlist,
    _parse_operation_outcome,
)

# Path at which the jar would be installed (relative to repo root)
_REPO_ROOT = Path(__file__).parents[2]
_JAR_PATH = _REPO_ROOT / "tools" / "hl7-validator" / "validator_cli.jar"
_JRE_PATH = _REPO_ROOT / "tools" / "jre"
_ALLOWLIST_PATH = _REPO_ROOT / "mh_integration" / "expected_warnings.json"

_JAR_PRESENT = _JAR_PATH.exists()


# ---------------------------------------------------------------------------
# Allowlist tests (no jar required)
# ---------------------------------------------------------------------------


def test_allowlist_routes_specialty_regimen_code_unknown() -> None:
    """A code-unknown issue against the specialty-regimen URL must be allowlisted."""
    allowlist = _load_allowlist(_ALLOWLIST_PATH)
    assert len(allowlist) >= 2, "expected_warnings.json must have at least 2 real entries"

    issue = HL7Issue(
        severity="warning",
        code="code-unknown",
        location="Bundle.entry[5].resource.code.coding[0]",
        diagnostics="Unknown code 'tier2-oral' in system 'https://fhir-rag.example/CodeSystem/specialty-regimen'",
    )
    assert _is_allowlisted(issue, allowlist) is True


def test_allowlist_does_not_match_unrelated_issue() -> None:
    """An error unrelated to the allowlist entries must not be allowlisted."""
    allowlist = _load_allowlist(_ALLOWLIST_PATH)

    issue = HL7Issue(
        severity="error",
        code="structure",
        location="Bundle.entry[0].resource",
        diagnostics="Unknown resource type 'Frob'",
    )
    assert _is_allowlisted(issue, allowlist) is False


def test_parse_operation_outcome_splits_correctly() -> None:
    """_parse_operation_outcome correctly sorts issues into errors / expected / other."""
    allowlist = _load_allowlist(_ALLOWLIST_PATH)

    synthetic_outcome = {
        "resourceType": "OperationOutcome",
        "issue": [
            {
                "severity": "error",
                "code": "code-unknown",
                "diagnostics": "Code in https://fhir-rag.example/CodeSystem/specialty-regimen not found",
                "expression": ["Bundle.entry[2].resource.code.coding[0]"],
            },
            {
                "severity": "error",
                "code": "structure",
                "diagnostics": "Unknown key 'bogusField'",
                "expression": ["Bundle.entry[0].resource"],
            },
            {
                "severity": "warning",
                "code": "not-found",
                "diagnostics": "Profile https://hl7.org/fhir/StructureDefinition/Patient not resolved",
                "expression": ["Bundle.entry[0].resource"],
            },
        ],
    }

    dummy_path = Path("/tmp/dummy.json")
    result = _parse_operation_outcome(synthetic_outcome, "test-patient", dummy_path, allowlist)

    assert isinstance(result, HL7ValidationResult)
    # The code-unknown issue must go to expected_warnings (allowlisted)
    allowlisted_codes = [i.code for i in result.expected_warnings]
    assert "code-unknown" in allowlisted_codes

    # The structure error must go to errors (not allowlisted)
    error_codes = [i.code for i in result.errors]
    assert "structure" in error_codes

    # The warning must go to other_warnings
    other_codes = [i.code for i in result.other_warnings]
    assert "not-found" in other_codes

    # severity_counts must include all three
    assert result.severity_counts.get("error", 0) == 2
    assert result.severity_counts.get("warning", 0) == 1


def test_hl7_validator_constructs_without_side_effects() -> None:
    """HL7Validator.__init__ must not raise or perform I/O if jar is absent
    (constructor checks happen at validate time, not init time)."""
    v = HL7Validator(
        jar_path=Path("/nonexistent/validator_cli.jar"),
        jre_path=Path("/nonexistent/jre"),
        allowlist_path=None,
    )
    assert v._fhir_version == "4.3.0"


def test_hl7_validator_raises_on_missing_jar() -> None:
    """validate_bundle must raise RuntimeError when jar is absent."""
    v = HL7Validator(
        jar_path=Path("/nonexistent/validator_cli.jar"),
        jre_path=Path("/nonexistent/jre"),
    )
    with pytest.raises(RuntimeError, match="HL7 validator jar not found"):
        v.validate_bundle(Path("/any/file.json"), Path("/any/out.json"))


# ---------------------------------------------------------------------------
# Jar-dependent tests (skipped if jar not installed)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _JAR_PRESENT,
    reason="HL7 validator jar not installed at tools/hl7-validator/validator_cli.jar; "
           "run bash scripts/setup_hl7_validator.sh to install",
)
def test_validate_bundle_returns_result(fixtures_dir: Path) -> None:
    """validate_bundle on a valid fixture returns a well-formed HL7ValidationResult."""
    import tempfile

    v = HL7Validator(
        jar_path=_JAR_PATH,
        jre_path=_JRE_PATH,
        allowlist_path=_ALLOWLIST_PATH,
        fhir_version="4.3.0",
    )
    bundle_path = fixtures_dir / "valid_minimal_urn.json"
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "valid_minimal_urn_hl7.json"
        result = v.validate_bundle(bundle_path, out)

    assert isinstance(result, HL7ValidationResult)
    assert isinstance(result.severity_counts, dict)
    assert isinstance(result.errors, list)
    assert isinstance(result.expected_warnings, list)
    assert isinstance(result.other_warnings, list)
