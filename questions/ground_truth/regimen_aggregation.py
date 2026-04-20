"""Regimen-aggregation questions — totals, counts, means."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from .common import NA, QuestionTemplate, doses_in_window, get_component


def _total_template(component_id: str, descriptor: str) -> QuestionTemplate:
    def ans(meta: dict[str, Any], ref: date) -> Any:
        c = get_component(meta, component_id)
        if not c:
            return NA
        return len(c.get("dose_event_dates") or [])

    return QuestionTemplate(
        template_id=f"ra.total.{component_id}",
        qtype="regimen_aggregation",
        question=f"What is the total number of {descriptor} administrations across the entire regimen horizon?",
        paraphrases=(
            f"Across the whole horizon, how many {descriptor} doses are recorded?",
            f"Give the total count of {descriptor} administrations over the full window.",
        ),
        answer_fn=ans,
        provenance=f"len(MedicationAdministration[{component_id}])",
    )


def _avg_gap_template(component_id: str, descriptor: str) -> QuestionTemplate:
    def ans(meta: dict[str, Any], ref: date) -> Any:
        c = get_component(meta, component_id)
        if not c:
            return NA
        events = [date.fromisoformat(d) for d in (c.get("dose_event_dates") or [])]
        if len(events) < 2:
            return NA
        gaps = [(events[i + 1] - events[i]).days for i in range(len(events) - 1)]
        # Return the mean rounded to the nearest integer (deterministic)
        return round(sum(gaps) / len(gaps))

    return QuestionTemplate(
        template_id=f"ra.avg_gap.{component_id}",
        qtype="regimen_aggregation",
        question=f"What is the average number of days between consecutive {descriptor} administrations, rounded to the nearest integer?",
        paraphrases=(
            f"Report the mean interval (in whole days) between {descriptor} doses.",
            f"What is the average spacing in days between {descriptor} administrations?",
        ),
        answer_fn=ans,
        provenance=f"mean(gaps(MedicationAdministration[{component_id}]))",
    )


def _n_components_template() -> QuestionTemplate:
    def ans(meta: dict[str, Any], ref: date) -> Any:
        return len(meta["components"])

    return QuestionTemplate(
        template_id="ra.n_components",
        qtype="regimen_aggregation",
        question="How many distinct medication components are in this patient's regimen?",
        paraphrases=(
            "Count the number of medication components in the regimen.",
            "How many separate components make up this regimen?",
        ),
        answer_fn=ans,
        provenance="len(CarePlan.activity)",
    )


def _horizon_days_template() -> QuestionTemplate:
    def ans(meta: dict[str, Any], ref: date) -> Any:
        return int(meta["horizon_days"])

    return QuestionTemplate(
        template_id="ra.horizon_days",
        qtype="regimen_aggregation",
        question="How many days does the projected regimen horizon span?",
        paraphrases=(
            "What is the length (in days) of the regimen observation window?",
            "Give the horizon duration in days.",
        ),
        answer_fn=ans,
        provenance="CarePlan.period.end − CarePlan.period.start",
    )


def _trailing_total_template(window: int) -> QuestionTemplate:
    def ans(meta: dict[str, Any], ref: date) -> Any:
        start = ref - timedelta(days=window)
        total = 0
        for c in meta["components"]:
            total += len(doses_in_window(c, start, ref))
        return total

    return QuestionTemplate(
        template_id=f"ra.total_last_{window}d.all",
        qtype="regimen_aggregation",
        question=f"Across all regimen components, how many administrations were recorded in the {window} days up to the reference date?",
        paraphrases=(
            f"Sum administrations over all components in the trailing {window}-day window.",
            f"What is the total number of doses given in the past {window} days across every component?",
        ),
        answer_fn=ans,
        provenance=f"sum_c count(MedicationAdministration[c] in [ref-{window}d, ref])",
    )


def templates() -> list[QuestionTemplate]:
    out: list[QuestionTemplate] = []
    for comp_id, descr in [
        ("primary", "primary regimen"),
        ("adjunct", "oral adjunct"),
        ("rescue", "PRN rescue"),
    ]:
        out.append(_total_template(comp_id, descr))
        out.append(_avg_gap_template(comp_id, descr))
    out.append(_n_components_template())
    out.append(_horizon_days_template())
    for window in (30, 60, 90, 180):
        out.append(_trailing_total_template(window))
    return out  # 3*2 + 2 + 4 = 12
