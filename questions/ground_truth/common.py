"""Shared helpers for programmatic ground-truth evaluation.

All ground-truth functions are pure Python over the regimen metadata
produced by the overlay. No LLMs. No external lookups.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Callable

# Sentinel used when the question does not apply to this patient.
NA = "N/A"


@dataclass(frozen=True)
class QuestionTemplate:
    """One template. Resolves to one concrete question per patient."""

    template_id: str
    qtype: str  # "temporal_lookup" | "temporal_comparison" | "regimen_compliance" | "regimen_aggregation" | "cross_resource"
    question: str  # may contain {component}, {days}, etc.; must be fully-specified
    paraphrases: tuple[str, str]
    answer_fn: Callable[[dict[str, Any], date], Any]
    provenance: str  # hint about which FHIR field the answer comes from


def reference_date(patient_id: str, regimen_start: date, seed: int) -> date:
    """Deterministic uniform sample in [regimen_start − 30, regimen_start + 90]."""
    h = hashlib.sha256(f"{seed}:refdate:{patient_id}".encode("utf-8")).hexdigest()
    offset = (int(h[:8], 16) % 121) - 30  # 0..120 → -30..+90
    return regimen_start + timedelta(days=offset)


def get_component(meta: dict[str, Any], component_id: str) -> dict[str, Any] | None:
    for c in meta["components"]:
        if c["component_id"] == component_id:
            return c
    return None


def parse_date(s: str) -> date:
    return date.fromisoformat(s[:10])


def doses(component: dict[str, Any]) -> list[date]:
    return [parse_date(d) for d in component.get("dose_event_dates") or []]


def doses_in_window(component: dict[str, Any], start: date, end: date) -> list[date]:
    return [d for d in doses(component) if start <= d <= end]


def next_scheduled(component: dict[str, Any], ref: date) -> date | str:
    future = [d for d in doses(component) if d >= ref]
    return future[0] if future else NA


def last_administered(component: dict[str, Any], ref: date) -> date | str:
    past = [d for d in doses(component) if d <= ref]
    return past[-1] if past else NA


def days_until_next(component: dict[str, Any], ref: date) -> int | str:
    nxt = next_scheduled(component, ref)
    return (nxt - ref).days if isinstance(nxt, date) else NA


def days_since_last(component: dict[str, Any], ref: date) -> int | str:
    last = last_administered(component, ref)
    return (ref - last).days if isinstance(last, date) else NA


def cycle_position(component: dict[str, Any], ref: date, regimen_start: date) -> str:
    """For a cyclic component, return 'on-week' or 'off-week' or NA."""
    if component.get("schedule_kind") != "cyclic":
        return NA
    on_weeks = component.get("cycle_on_weeks") or 0
    off_weeks = component.get("cycle_off_weeks") or 0
    if not on_weeks or not off_weeks:
        return NA
    cycle_days = (on_weeks + off_weeks) * 7
    offset = (ref - regimen_start).days % cycle_days
    on_days = on_weeks * 7
    return "on-week" if 0 <= offset < on_days else "off-week"


def fmt_answer(v: Any) -> Any:
    """Convert date objects to ISO strings for JSON output."""
    if isinstance(v, date):
        return v.isoformat()
    return v
