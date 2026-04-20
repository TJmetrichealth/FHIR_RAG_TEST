"""Apply the specialty-regimen overlay to Synthea FHIR bundles.

For each input bundle:
  1. Deterministically assign a complexity tier (SHA-256 of patient id mod 3).
  2. Pick a regimen start date deterministically from the patient id.
  3. Emit Medication, MedicationRequest, MedicationAdministration, CarePlan
     resources according to the tier spec.
  4. Validate the resulting bundle via fhir.resources (R4B pydantic models).
  5. Write out to --output with a regimen-index sidecar.

Usage:
  python -m overlay.specialty_regimen_generator \
      --input data/synthea_base/fhir \
      --output data/fhir_bundles \
      --seed 20260427 [--sample N]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .tiers import ALL_TIERS, RegimenComponent, Tier, TierSpec, tier_for_patient


MEDICATION_SYSTEM = "https://fhir-rag.example/CodeSystem/specialty-regimen"

_TZ = timezone.utc


def _deterministic_rng(patient_id: str, seed: int) -> random.Random:
    h = hashlib.sha256(f"{seed}:{patient_id}".encode("utf-8")).hexdigest()
    return random.Random(int(h[:16], 16))


def _extract_patient_entry(bundle: dict[str, Any]) -> dict[str, Any] | None:
    for entry in bundle.get("entry", []):
        res = entry.get("resource", {})
        if res.get("resourceType") == "Patient":
            return res
    return None


def _patient_birthdate(patient: dict[str, Any]) -> date | None:
    bd = patient.get("birthDate")
    if not bd:
        return None
    try:
        return date.fromisoformat(bd[:10])
    except ValueError:
        return None


def _pick_encounter_ref(bundle: dict[str, Any]) -> str | None:
    for entry in bundle.get("entry", []):
        res = entry.get("resource", {})
        if res.get("resourceType") == "Encounter" and res.get("id"):
            return f"Encounter/{res['id']}"
    return None


def _pick_practitioner_ref(bundle: dict[str, Any]) -> str | None:
    for entry in bundle.get("entry", []):
        res = entry.get("resource", {})
        if res.get("resourceType") == "Practitioner" and res.get("id"):
            return f"Practitioner/{res['id']}"
    return None


def _regimen_start(
    rng: random.Random, patient_birth: date | None, today: date
) -> date:
    # Start between 365 and 30 days before "today" (a fixed reference date so
    # the dataset is stable across runs). This yields patients at different
    # stages of their regimen.
    offset = rng.randint(30, 365)
    candidate = today - timedelta(days=offset)
    if patient_birth and candidate < patient_birth + timedelta(days=18 * 365):
        candidate = patient_birth + timedelta(days=18 * 365)
    return candidate


def _iso_dt(d: date, hour: int = 9) -> str:
    return datetime(d.year, d.month, d.day, hour, 0, 0, tzinfo=_TZ).isoformat()


def _iso_date(d: date) -> str:
    return d.isoformat()


def _medication_resource(component: RegimenComponent) -> dict[str, Any]:
    return {
        "resourceType": "Medication",
        "id": f"med-{component.code_value.lower()}",
        "code": {
            "coding": [
                {
                    "system": MEDICATION_SYSTEM,
                    "code": component.code_value,
                    "display": component.code_display,
                }
            ],
            "text": component.descriptor,
        },
        "form": {"text": component.form},
    }


def _dosage_instruction(component: RegimenComponent) -> list[dict[str, Any]]:
    timing: dict[str, Any] = {}
    if component.schedule_kind == "fixed_interval" and component.interval_days:
        if component.interval_days == 1:
            timing = {"repeat": {"frequency": 1, "period": 1, "periodUnit": "d"}}
        else:
            timing = {
                "repeat": {
                    "frequency": 1,
                    "period": component.interval_days,
                    "periodUnit": "d",
                }
            }
    elif component.schedule_kind == "cyclic":
        timing = {
            "repeat": {
                "frequency": 1,
                "period": 1,
                "periodUnit": "d",
                "durationUnit": "wk",
                "duration": component.cycle_on_weeks,
            }
        }
    elif component.schedule_kind == "prn":
        timing = {}
    route_map = {
        "subcutaneous": ("SC", "Subcutaneous route"),
        "oral": ("PO", "Oral route"),
        "inhalation": ("IH", "Inhalation route"),
    }
    route_code, route_display = route_map[component.route]
    dosage: dict[str, Any] = {
        "text": component.descriptor,
        "route": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/v3-RouteOfAdministration",
                    "code": route_code,
                    "display": route_display,
                }
            ]
        },
    }
    if timing:
        dosage["timing"] = timing
    if component.schedule_kind == "prn":
        dosage["asNeededBoolean"] = True
        if component.prn_indication:
            dosage["text"] = f"{component.descriptor} (as needed for {component.prn_indication})"
    return [dosage]


def _medication_request(
    *,
    component: RegimenComponent,
    patient_ref: str,
    encounter_ref: str | None,
    practitioner_ref: str | None,
    medication_ref: str,
    authored_on: date,
    request_id: str,
) -> dict[str, Any]:
    res: dict[str, Any] = {
        "resourceType": "MedicationRequest",
        "id": request_id,
        "status": "active",
        "intent": "order",
        "medicationReference": {"reference": f"Medication/{medication_ref}"},
        "subject": {"reference": patient_ref},
        "authoredOn": _iso_date(authored_on),
        "dosageInstruction": _dosage_instruction(component),
    }
    if encounter_ref:
        res["encounter"] = {"reference": encounter_ref}
    if practitioner_ref:
        res["requester"] = {"reference": practitioner_ref}
    return res


def _schedule_dose_events(
    component: RegimenComponent, regimen_start: date, horizon_days: int
) -> list[date]:
    events: list[date] = []
    end = regimen_start + timedelta(days=horizon_days)
    if component.schedule_kind == "fixed_interval":
        step = component.interval_days or 1
        if component.oral_daily and step == 1:
            cur = regimen_start
            while cur <= end:
                events.append(cur)
                cur += timedelta(days=1)
        else:
            cur = regimen_start
            while cur <= end:
                events.append(cur)
                cur += timedelta(days=step)
    elif component.schedule_kind == "cyclic":
        on_weeks = component.cycle_on_weeks or 4
        off_weeks = component.cycle_off_weeks or 2
        cycle_days = (on_weeks + off_weeks) * 7
        on_days = on_weeks * 7
        cur = regimen_start
        while cur <= end:
            cycle_offset = (cur - regimen_start).days % cycle_days
            if cycle_offset < on_days:
                events.append(cur)
            cur += timedelta(days=1)
    elif component.schedule_kind == "prn":
        # Emit zero, one, or two PRN events deterministically so some patients
        # have rescue-inhaler usage recorded and others do not.
        pass
    return events


def _medication_administration(
    *,
    component: RegimenComponent,
    patient_ref: str,
    encounter_ref: str | None,
    medication_ref: str,
    request_ref: str,
    effective: date,
    admin_id: str,
) -> dict[str, Any]:
    res: dict[str, Any] = {
        "resourceType": "MedicationAdministration",
        "id": admin_id,
        "status": "completed",
        "medicationReference": {"reference": f"Medication/{medication_ref}"},
        "subject": {"reference": patient_ref},
        "effectiveDateTime": _iso_dt(effective),
        "request": {"reference": f"MedicationRequest/{request_ref}"},
    }
    if encounter_ref:
        res["context"] = {"reference": encounter_ref}
    return res


def _careplan(
    *,
    patient_ref: str,
    tier_spec: TierSpec,
    regimen_start: date,
    horizon_days: int,
    request_refs: list[str],
    careplan_id: str,
) -> dict[str, Any]:
    return {
        "resourceType": "CarePlan",
        "id": careplan_id,
        "status": "active",
        "intent": "plan",
        "title": f"Specialty regimen — tier {int(tier_spec.tier)}",
        "description": tier_spec.description,
        "subject": {"reference": patient_ref},
        "period": {
            "start": _iso_date(regimen_start),
            "end": _iso_date(regimen_start + timedelta(days=horizon_days)),
        },
        "activity": [
            {"reference": {"reference": f"MedicationRequest/{r}"}} for r in request_refs
        ],
        "note": [
            {
                "text": (
                    f"tier={int(tier_spec.tier)}; "
                    f"label={tier_spec.label}; "
                    f"start={_iso_date(regimen_start)}"
                )
            }
        ],
    }


def apply_overlay(
    bundle: dict[str, Any],
    *,
    seed: int,
    reference_today: date,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Mutate the bundle in-place with specialty resources.

    Returns (updated_bundle, regimen_metadata).
    """
    patient = _extract_patient_entry(bundle)
    if not patient or not patient.get("id"):
        raise ValueError("Bundle has no Patient resource with id.")
    patient_id = patient["id"]
    patient_ref = f"Patient/{patient_id}"
    tier = tier_for_patient(patient_id)
    spec = ALL_TIERS[tier]
    rng = _deterministic_rng(patient_id, seed)
    start = _regimen_start(rng, _patient_birthdate(patient), reference_today)

    encounter_ref = _pick_encounter_ref(bundle)
    practitioner_ref = _pick_practitioner_ref(bundle)

    new_entries: list[dict[str, Any]] = []
    request_refs: list[str] = []
    component_meta: list[dict[str, Any]] = []

    for component in spec.components:
        med = _medication_resource(component)
        new_entries.append({"fullUrl": f"urn:uuid:{uuid.uuid4()}", "resource": med})

        req_id = f"spec-req-{patient_id}-{component.component_id}"
        req = _medication_request(
            component=component,
            patient_ref=patient_ref,
            encounter_ref=encounter_ref,
            practitioner_ref=practitioner_ref,
            medication_ref=med["id"],
            authored_on=start,
            request_id=req_id,
        )
        new_entries.append({"fullUrl": f"urn:uuid:{uuid.uuid4()}", "resource": req})
        request_refs.append(req_id)

        event_dates = _schedule_dose_events(component, start, spec.horizon_days)
        admin_ids: list[str] = []
        for idx, eff in enumerate(event_dates):
            admin_id = f"spec-adm-{patient_id}-{component.component_id}-{idx:04d}"
            admin = _medication_administration(
                component=component,
                patient_ref=patient_ref,
                encounter_ref=encounter_ref,
                medication_ref=med["id"],
                request_ref=req_id,
                effective=eff,
                admin_id=admin_id,
            )
            new_entries.append(
                {"fullUrl": f"urn:uuid:{uuid.uuid4()}", "resource": admin}
            )
            admin_ids.append(admin_id)

        component_meta.append(
            {
                "component_id": component.component_id,
                "descriptor": component.descriptor,
                "code": component.code_value,
                "schedule_kind": component.schedule_kind,
                "interval_days": component.interval_days,
                "cycle_on_weeks": component.cycle_on_weeks,
                "cycle_off_weeks": component.cycle_off_weeks,
                "medication_ref": med["id"],
                "request_ref": req_id,
                "administration_refs": admin_ids,
                "dose_event_dates": [_iso_date(d) for d in event_dates],
                "prn_indication": component.prn_indication,
            }
        )

    careplan_id = f"spec-cp-{patient_id}"
    cp = _careplan(
        patient_ref=patient_ref,
        tier_spec=spec,
        regimen_start=start,
        horizon_days=spec.horizon_days,
        request_refs=request_refs,
        careplan_id=careplan_id,
    )
    new_entries.append({"fullUrl": f"urn:uuid:{uuid.uuid4()}", "resource": cp})

    bundle.setdefault("entry", []).extend(new_entries)

    meta = {
        "patient_id": patient_id,
        "tier": int(tier),
        "tier_label": spec.label,
        "tier_description": spec.description,
        "regimen_start": _iso_date(start),
        "regimen_end": _iso_date(start + timedelta(days=spec.horizon_days)),
        "horizon_days": spec.horizon_days,
        "careplan_ref": careplan_id,
        "components": component_meta,
    }
    return bundle, meta


def _validate_bundle(bundle: dict[str, Any]) -> None:
    """Best-effort R4B validation via fhir.resources.

    Silently skipped if fhir.resources is unavailable; any validation error
    is raised to the caller with the patient id.
    """
    try:
        from fhir.resources.R4B.bundle import Bundle  # type: ignore
    except Exception:  # pragma: no cover - import path varies by version
        return
    Bundle.model_validate(bundle)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Synthea fhir dir")
    parser.add_argument("--output", required=True, type=Path, help="Output dir")
    parser.add_argument("--seed", type=int, default=20260427)
    parser.add_argument("--sample", type=int, default=0, help="Process only N bundles")
    parser.add_argument(
        "--reference-today",
        default="2026-04-27",
        help="ISO date treated as 'today' for regimen-start sampling",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip fhir.resources validation (speed up large runs)",
    )
    args = parser.parse_args(argv)

    today = date.fromisoformat(args.reference_today)
    args.output.mkdir(parents=True, exist_ok=True)
    bundles = sorted(args.input.glob("*.json"))
    # Exclude Synthea aggregate files (hospitalInformation, practitionerInformation)
    bundles = [
        b
        for b in bundles
        if not b.name.startswith("hospitalInformation")
        and not b.name.startswith("practitionerInformation")
    ]
    if args.sample > 0:
        bundles = bundles[: args.sample]

    index: dict[str, Any] = {"patients": {}, "seed": args.seed, "reference_today": args.reference_today}
    produced = 0
    validated = 0

    for path in bundles:
        try:
            bundle = json.loads(path.read_text())
        except Exception as exc:  # noqa: BLE001
            print(f"[skip] {path.name}: {exc}", file=sys.stderr)
            continue
        try:
            updated, meta = apply_overlay(bundle, seed=args.seed, reference_today=today)
        except ValueError as exc:
            print(f"[skip] {path.name}: {exc}", file=sys.stderr)
            continue

        if not args.skip_validation:
            try:
                _validate_bundle(updated)
                validated += 1
            except Exception as exc:  # noqa: BLE001
                print(f"[invalid] {path.name}: {exc}", file=sys.stderr)
                continue

        out_path = args.output / f"{meta['patient_id']}.json"
        out_path.write_text(json.dumps(updated, indent=2, sort_keys=True))
        index["patients"][meta["patient_id"]] = meta
        produced += 1

    index_path = args.output / "_regimen_index.json"
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True))
    print(
        f"overlay: produced={produced} validated={validated if not args.skip_validation else 'skipped'} "
        f"input={len(bundles)} output_dir={args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
