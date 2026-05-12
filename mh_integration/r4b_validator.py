"""Standalone R4B conformance validator for the 200 FHIR bundles.

Uses fhir.resources R4B Pydantic models to parse and check each bundle.
Validates:
  - Bundle parses without Pydantic validation errors
  - Required resource types are present (Patient, MedicationRequest, MedicationAdministration, CarePlan)
  - All internal references resolve within the bundle (generic walker, not subject-only)
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
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

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

logger = logging.getLogger(__name__)

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


@dataclass
class ReferenceIndex:
    by_full_url: dict[str, tuple[str, str]] = field(default_factory=dict)
    # fullUrl -> (resourceType, id)
    by_type_id: dict[tuple[str, str], str] = field(default_factory=dict)
    # (resourceType, id) -> fullUrl
    contained_by_parent: dict[str, set[str]] = field(default_factory=dict)
    # parent resource id -> {contained.id}


def walk_references(node: object, path: str = "") -> Iterator[tuple[str, str]]:
    """Recursively yield (json_path, reference_string) for every Reference-shaped dict in node.

    A Reference is a dict with a string 'reference' key; may also have 'type',
    'identifier', 'display'. Recurses through every nested dict and list.
    """
    if isinstance(node, dict):
        ref_val = node.get("reference")
        if isinstance(ref_val, str):
            logger.debug("walk_references: found reference at path=%s value=%s", path, ref_val)
            yield (path, ref_val)
        for key, value in node.items():
            child_path = f"{path}.{key}" if path else key
            yield from walk_references(value, child_path)
    elif isinstance(node, list):
        for idx, item in enumerate(node):
            child_path = f"{path}[{idx}]"
            yield from walk_references(item, child_path)


def build_reference_index(bundle_raw: dict) -> ReferenceIndex:
    """Build by_full_url and by_type_id from bundle.entry; also index contained per parent id.

    Inputs: raw bundle dict (before Pydantic parsing).
    Returns: populated ReferenceIndex.
    """
    index = ReferenceIndex()
    entries = bundle_raw.get("entry", []) or []

    for entry in entries:
        full_url = entry.get("fullUrl", "")
        resource = entry.get("resource") or {}
        rtype = resource.get("resourceType", "")
        rid = resource.get("id", "")

        if full_url and rtype and rid:
            index.by_full_url[full_url] = (rtype, rid)
            index.by_type_id[(rtype, rid)] = full_url
        elif full_url and rtype:
            # Resource without id: still index by fullUrl only
            index.by_full_url[full_url] = (rtype, "")
        elif rtype and rid:
            index.by_type_id[(rtype, rid)] = ""

        # Index contained resources scoped to this parent resource
        if rid:
            contained_list = resource.get("contained") or []
            if contained_list:
                contained_ids: set[str] = set()
                for c in contained_list:
                    if isinstance(c, dict):
                        cid = c.get("id", "")
                        if cid:
                            contained_ids.add(cid)
                if contained_ids:
                    index.contained_by_parent[rid] = contained_ids
                    logger.debug(
                        "build_reference_index: parent=%s contained=%s", rid, contained_ids
                    )

    logger.info(
        "build_reference_index: indexed %d fullUrls, %d type/id pairs, %d parents with contained",
        len(index.by_full_url),
        len(index.by_type_id),
        len(index.contained_by_parent),
    )
    return index


def resolve_reference(
    ref_str: str,
    parent_resource_id: str | None,
    index: ReferenceIndex,
) -> tuple[str, str | None]:
    """Return (resolution_status, target_key_or_None).

    Status values:
      'RESOLVED_FULL_URL'   - matched in index.by_full_url
      'RESOLVED_TYPE_ID'    - matched in index.by_type_id
      'RESOLVED_CONTAINED'  - matched in index.contained_by_parent for parent
      'LOGICAL_REFERENCE'   - contains '?' (logged, not an error)
      'UNRESOLVED'          - no match found, or empty/None input
      'EXTERNAL'            - starts with http(s):// and not in bundle
    """
    if not ref_str:
        logger.debug("resolve_reference: empty or None reference -> UNRESOLVED")
        return ("UNRESOLVED", None)

    # Contained reference: #localid
    if ref_str.startswith("#"):
        local_id = ref_str[1:]
        if parent_resource_id and parent_resource_id in index.contained_by_parent:
            if local_id in index.contained_by_parent[parent_resource_id]:
                logger.debug(
                    "resolve_reference: contained ref=%s resolved in parent=%s",
                    ref_str,
                    parent_resource_id,
                )
                return ("RESOLVED_CONTAINED", local_id)
        logger.debug(
            "resolve_reference: contained ref=%s not found in parent=%s", ref_str, parent_resource_id
        )
        return ("UNRESOLVED", None)

    # Logical reference: contains '?'
    if "?" in ref_str:
        logger.debug("resolve_reference: logical reference=%s", ref_str)
        return ("LOGICAL_REFERENCE", None)

    # External reference: http(s):// not in bundle
    if ref_str.startswith("http://") or ref_str.startswith("https://"):
        if ref_str in index.by_full_url:
            return ("RESOLVED_FULL_URL", ref_str)
        logger.debug("resolve_reference: external reference=%s", ref_str)
        return ("EXTERNAL", None)

    # urn:uuid: or other fullUrl form
    if ref_str.startswith("urn:uuid:") or ref_str.startswith("urn:"):
        if ref_str in index.by_full_url:
            logger.debug("resolve_reference: fullUrl ref=%s resolved", ref_str)
            return ("RESOLVED_FULL_URL", ref_str)
        # Try stripping path suffix for malformed urn:uuid:X/Y
        if "/" in ref_str:
            parts = ref_str.rsplit("/", 1)
            if parts[0] in index.by_full_url:
                return ("RESOLVED_FULL_URL", parts[0])
        logger.debug("resolve_reference: urn ref=%s not found", ref_str)
        return ("UNRESOLVED", None)

    # ResourceType/id form (relative reference)
    if "/" in ref_str:
        slash_idx = ref_str.index("/")
        rtype = ref_str[:slash_idx]
        rid = ref_str[slash_idx + 1:]
        key = (rtype, rid)
        if key in index.by_type_id:
            logger.debug("resolve_reference: type/id ref=%s resolved", ref_str)
            return ("RESOLVED_TYPE_ID", ref_str)
        # Also try the fullUrl index in case it's stored directly
        if ref_str in index.by_full_url:
            return ("RESOLVED_FULL_URL", ref_str)
        logger.debug("resolve_reference: type/id ref=%s not found", ref_str)
        return ("UNRESOLVED", None)

    # Bare id (no slash, no prefix) - try as a fullUrl directly
    if ref_str in index.by_full_url:
        return ("RESOLVED_FULL_URL", ref_str)

    logger.debug("resolve_reference: unrecognized form ref=%s -> UNRESOLVED", ref_str)
    return ("UNRESOLVED", None)


def _check_all_references(
    bundle: object,
    bundle_raw: dict,
    errors: list[str],
) -> None:
    """Walk every resource in the bundle, resolve every reference, append errors for unresolved."""
    index = build_reference_index(bundle_raw)
    entries = bundle_raw.get("entry", []) or []

    for entry_idx, entry in enumerate(entries):
        resource = entry.get("resource") or {}
        rtype = resource.get("resourceType", "UNKNOWN")
        rid = resource.get("id", "")

        # Walk the full resource dict for all Reference-shaped nodes
        base_path = f"entry[{entry_idx}].resource"
        for json_path, ref_str in walk_references(resource, base_path):
            # Skip system/url/display fields that happen to have string values
            # A true Reference field should resolve; only check "reference" keys
            status, _target = resolve_reference(ref_str, rid if rid else None, index)

            if status == "UNRESOLVED":
                errors.append(
                    f"{rtype} id={rid or '?'} at {json_path}: reference '{ref_str}' "
                    f"does not resolve in bundle"
                )
                logger.warning(
                    "_check_all_references: UNRESOLVED rtype=%s id=%s path=%s ref=%s",
                    rtype, rid, json_path, ref_str,
                )
            elif status == "LOGICAL_REFERENCE":
                logger.info(
                    "_check_all_references: LOGICAL_REFERENCE rtype=%s id=%s path=%s ref=%s",
                    rtype, rid, json_path, ref_str,
                )
            elif status == "EXTERNAL":
                logger.info(
                    "_check_all_references: EXTERNAL rtype=%s id=%s path=%s ref=%s",
                    rtype, rid, json_path, ref_str,
                )


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
    logger.info("validate_bundle: processing %s", bundle_path.name)

    # Derive patient_id and tier:
    #   - patient_id: prefer the per-patient sidecar (<stem>_regimen_index.json) if
    #     present; otherwise fall back to the file stem. (Project does not currently
    #     emit per-patient sidecars — the regimen index is a single shared file at
    #     `data/fhir_bundles/_regimen_index.json` — so the file-stem path is the
    #     usual one.)
    #   - tier: prefer the per-patient sidecar; otherwise extract from the
    #     specialty CarePlan's `note[].text` field via the regex `tier=(\d+)`
    #     (same convention as `narratives/fidelity_audit.py`).
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
    if tier == "unknown":
        import re as _re
        for _entry in raw.get("entry", []) or []:
            _res = _entry.get("resource") or {}
            if _res.get("resourceType") == "CarePlan" and _res.get("id", "").startswith("spec-cp-"):
                for _note in _res.get("note", []) or []:
                    _m = _re.search(r"tier=(\d+)", _note.get("text", "") or "")
                    if _m:
                        tier = _m.group(1)
                        break
                if tier != "unknown":
                    break

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
    resource_types_present: set[str] = set()

    for entry in entries:
        res = entry.resource
        if res is None:
            continue
        rtype = res.__resource_type__
        resource_types_present.add(rtype)

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

    # Check 5: generic reference walk (replaces subject-only check)
    _check_all_references(bundle, raw, errors)

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
        f"R4B validation: {total} bundles -- {passed} passed, {failed} failed "
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
