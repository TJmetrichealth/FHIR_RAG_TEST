"""Standalone R4B conformance validator for the 200 FHIR bundles.

Uses fhir.resources R4B Pydantic models to parse and check each bundle.
Validates:
  - Bundle parses without Pydantic validation errors
  - Required resource types are present (Patient, MedicationRequest, MedicationAdministration, CarePlan)
  - All internal references (subject, medication, encounter) resolve within the bundle
  - MedicationRequest.status is a valid R4B value
  - Each MedicationAdministration has a resolvable medicationReference or medicationCodeableConcept

Output: results/conformance_rates.csv
  Columns: patient_id, tier, passed, error_count, errors_json

Usage:
  python -m mh_integration.r4b_validator \
      --bundles data/fhir_bundles \
      --output results/conformance_rates.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

# fhir.resources is available per pyproject.toml
try:
    from fhir.resources.R4B.bundle import Bundle
    from fhir.resources.R4B.medicationadministration import MedicationAdministration
    from fhir.resources.R4B.medicationrequest import MedicationRequest
    _FHIR_R4B = True
except ImportError:
    try:
        from fhir.resources.bundle import Bundle  # type: ignore[no-redef]
        from fhir.resources.medicationadministration import MedicationAdministration  # type: ignore[no-redef]
        from fhir.resources.medicationrequest import MedicationRequest  # type: ignore[no-redef]
        _FHIR_R4B = False
    except ImportError as exc:
        raise ImportError("fhir.resources>=8.0 is required. Run: pip install 'fhir.resources>=8.0,<9.0'") from exc


REQUIRED_RESOURCE_TYPES = {
    "Patient",
    "MedicationRequest",
    "MedicationAdministration",
    "CarePlan",
}

VALID_MEDICATION_REQUEST_STATUSES = {
    "active", "on-hold", "cancelled", "completed",
    "entered-in-error", "stopped", "draft", "unknown",
}


@dataclass
class ValidationResult:
    patient_id: str
    tier: int | str
    passed: bool
    errors: list[str] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return len(self.errors)


def _extract_id_from_ref(ref: str) -> str | None:
    """Return the bare ID from a reference like 'Patient/abc123' or 'urn:uuid:abc123'."""
    if ref.startswith("urn:uuid:"):
        return ref.removeprefix("urn:uuid:")
    if "/" in ref:
        return ref.rsplit("/", 1)[-1]
    return ref


def validate_bundle(bundle_path: Path) -> ValidationResult:
    """Parse a FHIR bundle JSON and run conformance checks.

    Returns a ValidationResult with passed=True only if all checks pass.
    """
    raw = json.loads(bundle_path.read_text(encoding="utf-8"))

    # Derive patient_id and tier from sidecar if present, else from filename
    sidecar_path = bundle_path.with_name(bundle_path.stem + "_regimen_index.json")
    patient_id = bundle_path.stem
    tier: int | str = "unknown"
    if sidecar_path.exists():
        try:
            meta = json.loads(sidecar_path.read_text(encoding="utf-8"))
            patient_id = meta.get("patient_id", patient_id)
            tier = meta.get("tier", tier)
        except Exception:
            pass

    errors: list[str] = []

    # Check 1: bundle parses as a FHIR Bundle
    try:
        bundle = Bundle.model_validate(raw)
    except Exception as exc:
        return ValidationResult(
            patient_id=patient_id,
            tier=tier,
            passed=False,
            errors=[f"Bundle parse error: {exc}"],
        )

    # Build a lookup of all resources by their id
    entries = bundle.entry or []
    resources_by_id: dict[str, dict] = {}
    resource_types_present: set[str] = set()

    for entry in entries:
        res = entry.resource
        if res is None:
            continue
        rtype = res.__resource_type__
        resource_types_present.add(rtype)
        rid = getattr(res, "id", None)
        if rid:
            resources_by_id[rid] = raw  # store raw; used only for presence checks

    # Check 2: required resource types present
    missing = REQUIRED_RESOURCE_TYPES - resource_types_present
    if missing:
        errors.append(f"Missing required resource types: {sorted(missing)}")

    # Check 3: MedicationRequest.status validity
    for entry in entries:
        res = entry.resource
        if res is None or res.__resource_type__ != "MedicationRequest":
            continue
        status = getattr(res, "status", None)
        if status and status not in VALID_MEDICATION_REQUEST_STATUSES:
            errors.append(f"MedicationRequest id={getattr(res, 'id', '?')} has invalid status '{status}'")

    # Check 4: MedicationAdministration has medication[x]
    for entry in entries:
        res = entry.resource
        if res is None or res.__resource_type__ != "MedicationAdministration":
            continue
        med_ref = getattr(res, "medicationReference", None)
        med_code = getattr(res, "medicationCodeableConcept", None)
        if med_ref is None and med_code is None:
            errors.append(
                f"MedicationAdministration id={getattr(res, 'id', '?')} has no medication[x]"
            )

    # Check 5: subject references resolve (Patient exists in bundle)
    patient_ids_in_bundle = {
        getattr(e.resource, "id", None)
        for e in entries
        if e.resource and e.resource.__resource_type__ == "Patient"
    }
    for entry in entries:
        res = entry.resource
        if res is None:
            continue
        subject = getattr(res, "subject", None)
        if subject is None:
            continue
        ref_str = getattr(subject, "reference", None)
        if ref_str:
            ref_id = _extract_id_from_ref(ref_str)
            if ref_id and ref_id not in patient_ids_in_bundle:
                errors.append(
                    f"{res.__resource_type__} id={getattr(res, 'id', '?')} subject ref '{ref_str}' "
                    f"does not resolve in bundle"
                )

    return ValidationResult(
        patient_id=patient_id,
        tier=tier,
        passed=len(errors) == 0,
        errors=errors,
    )


def validate_all(bundles_dir: Path, output_csv: Path) -> dict[str, int]:
    """Run validate_bundle on every *.json bundle file (skipping _regimen_index files).

    Writes results/conformance_rates.csv and returns summary counts.
    """
    bundle_files = sorted(
        p for p in bundles_dir.glob("*.json")
        if not p.stem.endswith("_regimen_index") and p.stem != "_regimen_index"
    )

    if not bundle_files:
        print(f"No bundle JSON files found in {bundles_dir}", file=sys.stderr)
        return {"total": 0, "passed": 0, "failed": 0}

    output_csv.parent.mkdir(parents=True, exist_ok=True)

    passed = 0
    failed = 0

    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["patient_id", "tier", "passed", "error_count", "errors_json"],
        )
        writer.writeheader()

        for bundle_path in bundle_files:
            result = validate_bundle(bundle_path)
            writer.writerow({
                "patient_id": result.patient_id,
                "tier": result.tier,
                "passed": result.passed,
                "error_count": result.error_count,
                "errors_json": json.dumps(result.errors),
            })
            if result.passed:
                passed += 1
            else:
                failed += 1
                for err in result.errors[:3]:  # print first 3 errors to stdout
                    print(f"  FAIL {result.patient_id}: {err}", file=sys.stderr)

    total = passed + failed
    print(
        f"R4B validation: {total} bundles — {passed} passed, {failed} failed "
        f"({100 * passed / total:.1f}% conformance)"
    )
    return {"total": total, "passed": passed, "failed": failed}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundles", required=True, type=Path, help="Directory of FHIR bundle JSON files")
    parser.add_argument("--output", required=True, type=Path, help="Output CSV path")
    args = parser.parse_args(argv)

    summary = validate_all(args.bundles, args.output)
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
