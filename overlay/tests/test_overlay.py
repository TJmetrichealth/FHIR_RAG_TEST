"""Tests for the specialty-regimen overlay.

Uses a minimal synthetic Synthea-like bundle so the tests run without
requiring a Synthea install. The bundle is valid enough to exercise the
overlay: Patient + Encounter + Practitioner entries with ids.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from overlay.specialty_regimen_generator import apply_overlay
from overlay.tiers import ALL_TIERS, Tier, tier_for_patient


def _make_bundle(patient_id: str) -> dict:
    return {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {
                "fullUrl": f"urn:uuid:{patient_id}",
                "resource": {
                    "resourceType": "Patient",
                    "id": patient_id,
                    "birthDate": "1985-06-15",
                    "gender": "female",
                },
            },
            {
                "fullUrl": "urn:uuid:enc-1",
                "resource": {
                    "resourceType": "Encounter",
                    "id": "enc-1",
                    "status": "finished",
                    "class": {"code": "AMB", "display": "ambulatory"},
                    "subject": {"reference": f"Patient/{patient_id}"},
                },
            },
            {
                "fullUrl": "urn:uuid:prac-1",
                "resource": {
                    "resourceType": "Practitioner",
                    "id": "prac-1",
                    "name": [{"family": "Smith", "given": ["Jane"]}],
                },
            },
        ],
    }


def test_tier_assignment_deterministic() -> None:
    pid = "11111111-2222-3333-4444-555555555555"
    assert tier_for_patient(pid) == tier_for_patient(pid)
    # Cover all three tiers across patient ids
    tiers_seen = {tier_for_patient(f"patient-{i:04d}") for i in range(30)}
    assert tiers_seen == {Tier.LOW, Tier.MEDIUM, Tier.HIGH}


def test_overlay_adds_all_resource_types() -> None:
    pid = "00000000-aaaa-bbbb-cccc-000000000001"
    bundle = _make_bundle(pid)
    updated, meta = apply_overlay(
        bundle, seed=20260427, reference_today=date(2026, 4, 27)
    )
    types = [
        e["resource"]["resourceType"] for e in updated["entry"] if "resource" in e
    ]
    assert "Medication" in types
    assert "MedicationRequest" in types
    assert "CarePlan" in types
    # Tier 1 has no scheduled intake of PRN, but every tier has at least one
    # MedicationAdministration (primary component) within the 365-day horizon.
    assert "MedicationAdministration" in types
    assert meta["patient_id"] == pid
    assert meta["tier"] in (1, 2, 3)
    assert meta["careplan_ref"] == f"spec-cp-{pid}"
    assert meta["regimen_start"] <= meta["regimen_end"]


def test_overlay_deterministic() -> None:
    pid = "00000000-aaaa-bbbb-cccc-000000000002"
    b1 = _make_bundle(pid)
    b2 = _make_bundle(pid)
    u1, m1 = apply_overlay(b1, seed=20260427, reference_today=date(2026, 4, 27))
    u2, m2 = apply_overlay(b2, seed=20260427, reference_today=date(2026, 4, 27))
    # Metadata (excluding UUID fullUrls) must match exactly
    assert m1 == m2
    # Dose-event counts per component match
    c1 = {c["component_id"]: len(c["dose_event_dates"]) for c in m1["components"]}
    c2 = {c["component_id"]: len(c["dose_event_dates"]) for c in m2["components"]}
    assert c1 == c2


def test_tier_spec_coverage() -> None:
    # All three tier specs exist with at least one component
    for t in (Tier.LOW, Tier.MEDIUM, Tier.HIGH):
        assert t in ALL_TIERS
        assert len(ALL_TIERS[t].components) >= 1


def test_raises_on_missing_patient() -> None:
    bundle = {"resourceType": "Bundle", "type": "collection", "entry": []}
    with pytest.raises(ValueError):
        apply_overlay(bundle, seed=1, reference_today=date(2026, 4, 27))


def test_overlay_idempotent_write(tmp_path: Path) -> None:
    pid = "00000000-aaaa-bbbb-cccc-000000000003"
    bundle = _make_bundle(pid)
    updated, _ = apply_overlay(
        bundle, seed=20260427, reference_today=date(2026, 4, 27)
    )
    out = tmp_path / f"{pid}.json"
    out.write_text(json.dumps(updated, indent=2, sort_keys=True))
    reloaded = json.loads(out.read_text())
    assert reloaded["entry"][0]["resource"]["resourceType"] == "Patient"
