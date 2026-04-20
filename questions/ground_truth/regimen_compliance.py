"""Regimen-compliance questions — doses in a window, cycle position, PRN use,
and PSP adherence indicators (PDC, MPR, persistence, missed-dose detection)."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from features.adherence_metrics import (
    compute_mpr,
    compute_pdc,
    consecutive_missed_doses,
    is_persistent,
)

from .common import (
    NA,
    QuestionTemplate,
    cycle_position,
    doses,
    doses_in_window,
    get_component,
    parse_date,
)


def _window_template(component_id: str, descriptor: str, days: int) -> QuestionTemplate:
    def ans(meta: dict[str, Any], ref: date) -> Any:
        c = get_component(meta, component_id)
        if not c:
            return NA
        start = ref - timedelta(days=days)
        return len(doses_in_window(c, start, ref))

    return QuestionTemplate(
        template_id=f"rc.doses_last_{days}d.{component_id}",
        qtype="regimen_compliance",
        question=f"How many {descriptor} administrations were recorded in the {days} days up to and including the reference date?",
        paraphrases=(
            f"In the past {days} days, how many times was the {descriptor} administered?",
            f"Count the {descriptor} administrations over the trailing {days}-day window ending on the reference date.",
        ),
        answer_fn=ans,
        provenance=f"count(MedicationAdministration[{component_id}] in [ref-{days}d, ref])",
    )


def _upcoming_window_template(component_id: str, descriptor: str, days: int) -> QuestionTemplate:
    def ans(meta: dict[str, Any], ref: date) -> Any:
        c = get_component(meta, component_id)
        if not c:
            return NA
        end = ref + timedelta(days=days)
        return len(doses_in_window(c, ref, end))

    return QuestionTemplate(
        template_id=f"rc.doses_next_{days}d.{component_id}",
        qtype="regimen_compliance",
        question=f"How many {descriptor} administrations are scheduled in the {days} days starting from the reference date (inclusive)?",
        paraphrases=(
            f"How many upcoming {descriptor} doses are there in the next {days} days?",
            f"Count the scheduled {descriptor} administrations from the reference date through the next {days} days.",
        ),
        answer_fn=ans,
        provenance=f"count(MedicationAdministration[{component_id}] in [ref, ref+{days}d])",
    )


def _cycle_templates() -> list[QuestionTemplate]:
    def ans_pos(meta: dict[str, Any], ref: date) -> Any:
        c = get_component(meta, "primary")
        if not c:
            return NA
        return cycle_position(c, ref, parse_date(meta["regimen_start"]))

    return [
        QuestionTemplate(
            template_id="rc.cycle_position.primary",
            qtype="regimen_compliance",
            question="On the reference date, is the primary component in an on-week or an off-week of its cycle?",
            paraphrases=(
                "Is the patient in the on-week or off-week of the primary regimen on the reference date?",
                "Describe the current cycle-position of the primary regimen: on-week or off-week.",
            ),
            answer_fn=ans_pos,
            provenance="(reference_date - regimen_start) mod (on_weeks+off_weeks)",
        ),
    ]


def _prn_used_template() -> QuestionTemplate:
    def ans(meta: dict[str, Any], ref: date) -> Any:
        c = get_component(meta, "rescue")
        if not c:
            return NA
        events = c.get("dose_event_dates") or []
        return "yes" if events else "no"

    return QuestionTemplate(
        template_id="rc.prn_used",
        qtype="regimen_compliance",
        question="Has the PRN rescue medication been administered at any point in the regimen?",
        paraphrases=(
            "Is there any recorded use of the PRN rescue inhaler?",
            "Was the as-needed rescue medication ever administered in the observation window?",
        ),
        answer_fn=ans,
        provenance="len(MedicationAdministration[rescue]) > 0",
    )


def _pdc_template() -> QuestionTemplate:
    """Coverage-window reasoning: PDC for the primary fixed-interval component."""

    def ans(meta: dict[str, Any], ref: date) -> Any:
        c = get_component(meta, "primary")
        if not c or c.get("schedule_kind") != "fixed_interval":
            return NA
        interval = c.get("interval_days")
        if not interval:
            return NA
        admin_dates = doses(c)
        if not admin_dates:
            return 0.0
        w_start = ref - timedelta(days=90)
        return round(compute_pdc(admin_dates, interval, w_start, ref), 4)

    return QuestionTemplate(
        template_id="rc.pdc_90d.primary",
        qtype="regimen_compliance",
        question="What is the Proportion of Days Covered (PDC) for the primary regimen component over the 90 days ending on the reference date? (Round to 4 decimal places.)",
        paraphrases=(
            "Calculate the PDC for the primary regimen in the trailing 90-day window.",
            "Over the 90 days up to and including the reference date, what fraction of days was the primary medication supply active?",
        ),
        answer_fn=ans,
        provenance="compute_pdc(MedicationAdministration[primary], interval_days, ref-90d, ref)",
    )


def _mpr_template() -> QuestionTemplate:
    """Coverage-window reasoning: MPR for the primary fixed-interval component."""

    def ans(meta: dict[str, Any], ref: date) -> Any:
        c = get_component(meta, "primary")
        if not c or c.get("schedule_kind") != "fixed_interval":
            return NA
        interval = c.get("interval_days")
        if not interval:
            return NA
        admin_dates = doses(c)
        window_doses = [d for d in admin_dates if d <= ref]
        return round(compute_mpr(window_doses, interval, 90), 4)

    return QuestionTemplate(
        template_id="rc.mpr_90d.primary",
        qtype="regimen_compliance",
        question="What is the Medication Possession Ratio (MPR) for the primary regimen component over the 90 days ending on the reference date? (Round to 4 decimal places.)",
        paraphrases=(
            "Compute the MPR for the primary component in the 90-day trailing window.",
            "Over the trailing 90-day period, what is the ratio of days of primary medication supply to total days?",
        ),
        answer_fn=ans,
        provenance="compute_mpr(doses_in_window[primary, ref-90d, ref], interval_days, 90)",
    )


def _persistence_template() -> QuestionTemplate:
    """Persistence: is the primary fixed-interval component gap-free?"""

    def ans(meta: dict[str, Any], ref: date) -> Any:
        c = get_component(meta, "primary")
        if not c or c.get("schedule_kind") != "fixed_interval":
            return NA
        interval = c.get("interval_days")
        if not interval:
            return NA
        admin_dates = [d for d in doses(c) if d <= ref]
        return "yes" if is_persistent(admin_dates, interval) else "no"

    return QuestionTemplate(
        template_id="rc.persistent.primary",
        qtype="regimen_compliance",
        question="Has the patient been persistent on the primary regimen up to the reference date? (No gap between consecutive doses exceeds 1.5 times the prescribed interval.)",
        paraphrases=(
            "Is the patient persistent on the primary regimen? Answer yes or no.",
            "Up to the reference date, has any gap between primary regimen doses exceeded 1.5 times the prescribed dosing interval?",
        ),
        answer_fn=ans,
        provenance="is_persistent(MedicationAdministration[primary], interval_days, multiplier=1.5)",
    )


def _missed_doses_template() -> QuestionTemplate:
    """Missed-dose detection: max consecutive missed doses in trailing 60 days."""

    def ans(meta: dict[str, Any], ref: date) -> Any:
        c = get_component(meta, "primary")
        if not c or c.get("schedule_kind") != "fixed_interval":
            return NA
        interval = c.get("interval_days")
        if not interval:
            return NA
        admin_dates = doses(c)
        return consecutive_missed_doses(admin_dates, interval, ref, lookback_days=60)

    return QuestionTemplate(
        template_id="rc.consecutive_missed.primary",
        qtype="regimen_compliance",
        question="In the 60 days leading up to the reference date, what is the maximum number of consecutive missed primary regimen doses?",
        paraphrases=(
            "How many consecutive primary regimen doses in a row were missed in the 60-day lookback window?",
            "What is the longest consecutive run of missed primary regimen doses in the trailing 60 days?",
        ),
        answer_fn=ans,
        provenance="consecutive_missed_doses(MedicationAdministration[primary], interval_days, ref, 60)",
    )


def templates() -> list[QuestionTemplate]:
    out: list[QuestionTemplate] = []
    for comp_id, descr in [
        ("primary", "primary regimen"),
        ("adjunct", "oral adjunct"),
        ("rescue", "PRN rescue"),
    ]:
        for d in (30, 60, 90):
            out.append(_window_template(comp_id, descr, d))
        for d in (30, 90):
            out.append(_upcoming_window_template(comp_id, descr, d))
    out.extend(_cycle_templates())
    out.append(_prn_used_template())
    # PSP adherence indicators (coverage-window, persistence, missed-dose)
    out.append(_pdc_template())
    out.append(_mpr_template())
    out.append(_persistence_template())
    out.append(_missed_doses_template())
    return out  # 3*(3+2) + 1 + 1 + 4 = 21
