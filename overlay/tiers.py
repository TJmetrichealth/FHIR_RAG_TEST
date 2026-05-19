"""Tier definitions for the specialty-regimen overlay.

Uses plausible class-level descriptors only (no real drug names).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class Tier(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


@dataclass(frozen=True)
class RegimenComponent:
    """A single medication component within a regimen."""

    component_id: str  # "primary" | "adjunct" | "rescue"
    descriptor: str  # human-readable class-level descriptor
    code_value: str  # synthetic placeholder code (e.g. "SPEC-T1-PRIMARY")
    code_display: str
    route: str  # "subcutaneous" | "oral" | "inhalation"
    form: str  # "injectable solution" | "tablet" | "metered-dose inhaler"
    schedule_kind: str  # "fixed_interval" | "cyclic" | "prn"
    interval_days: int | None = None  # fixed-interval: days between doses
    cycle_on_weeks: int | None = None  # cyclic: weeks-on
    cycle_off_weeks: int | None = None  # cyclic: weeks-off
    oral_daily: bool = False  # adjunct taken daily
    prn_indication: str | None = None


@dataclass(frozen=True)
class TierSpec:
    tier: Tier
    label: str
    description: str
    components: tuple[RegimenComponent, ...]
    horizon_days: int  # how long to project dose events forward


TIER_1 = TierSpec(
    tier=Tier.LOW,
    label="T1-long-acting-injectable",
    description="Single long-acting subcutaneous injectable, administered every 8 weeks.",
    components=(
        RegimenComponent(
            component_id="primary",
            descriptor="long-acting subcutaneous injectable biologic",
            code_value="SPEC-T1-PRIMARY",
            code_display="Specialty biologic (long-acting, q8w)",
            route="subcutaneous",
            form="injectable solution",
            schedule_kind="fixed_interval",
            interval_days=56,
        ),
    ),
    horizon_days=365,
)

TIER_2 = TierSpec(
    tier=Tier.MEDIUM,
    label="T2-cyclic-oral",
    description="Cyclic oral therapy, 4 weeks on / 2 weeks off.",
    components=(
        RegimenComponent(
            component_id="primary",
            descriptor="cyclic oral specialty therapy (4 weeks on, 2 weeks off)",
            code_value="SPEC-T2-PRIMARY",
            code_display="Specialty oral therapy (cyclic 4/2)",
            route="oral",
            form="tablet",
            schedule_kind="cyclic",
            cycle_on_weeks=4,
            cycle_off_weeks=2,
            oral_daily=True,
        ),
    ),
    horizon_days=365,
)

TIER_3 = TierSpec(
    tier=Tier.HIGH,
    label="T3-multidrug",
    description=(
        "Biologic injectable every 4 weeks, daily oral adjunct, "
        "and PRN rescue inhaler for breakthrough symptoms."
    ),
    components=(
        RegimenComponent(
            component_id="primary",
            descriptor="biologic injectable, every 4 weeks",
            code_value="SPEC-T3-BIOLOGIC",
            code_display="Specialty biologic (q4w)",
            route="subcutaneous",
            form="injectable solution",
            schedule_kind="fixed_interval",
            interval_days=28,
        ),
        RegimenComponent(
            component_id="adjunct",
            descriptor="daily oral adjunct",
            code_value="SPEC-T3-ADJUNCT",
            code_display="Specialty oral adjunct (daily)",
            route="oral",
            form="tablet",
            schedule_kind="fixed_interval",
            interval_days=1,
            oral_daily=True,
        ),
        RegimenComponent(
            component_id="rescue",
            descriptor="PRN rescue inhaler for breakthrough symptoms",
            code_value="SPEC-T3-RESCUE",
            code_display="Specialty rescue inhaler (PRN)",
            route="inhalation",
            form="metered-dose inhaler",
            schedule_kind="prn",
            prn_indication="breakthrough symptoms",
        ),
    ),
    horizon_days=365,
)

ALL_TIERS: dict[Tier, TierSpec] = {
    Tier.LOW: TIER_1,
    Tier.MEDIUM: TIER_2,
    Tier.HIGH: TIER_3,
}


def tier_for_patient(patient_id: str) -> Tier:
    """Deterministic tier assignment from patient id (SHA-256 mod 3)."""
    import hashlib

    h = int(hashlib.sha256(patient_id.encode("utf-8")).hexdigest(), 16)
    return Tier((h % 3) + 1)
