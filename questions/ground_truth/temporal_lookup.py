"""Temporal lookup questions — "When is X?" and "What is date Y?"."""
from __future__ import annotations

from datetime import date
from typing import Any

from .common import (
    NA,
    QuestionTemplate,
    days_since_last,
    days_until_next,
    get_component,
    last_administered,
    next_scheduled,
    parse_date,
)


def _component_question(
    component_id: str, descriptor_noun: str
) -> list[QuestionTemplate]:
    out: list[QuestionTemplate] = []

    def ans_next(meta: dict[str, Any], ref: date) -> Any:
        c = get_component(meta, component_id)
        if c is None:
            return NA
        return next_scheduled(c, ref)

    def ans_last(meta: dict[str, Any], ref: date) -> Any:
        c = get_component(meta, component_id)
        if c is None:
            return NA
        return last_administered(c, ref)

    def ans_days_to_next(meta: dict[str, Any], ref: date) -> Any:
        c = get_component(meta, component_id)
        if c is None:
            return NA
        return days_until_next(c, ref)

    def ans_days_since_last(meta: dict[str, Any], ref: date) -> Any:
        c = get_component(meta, component_id)
        if c is None:
            return NA
        return days_since_last(c, ref)

    out.extend(
        [
            QuestionTemplate(
                template_id=f"tl.next_scheduled.{component_id}",
                qtype="temporal_lookup",
                question=f"On the reference date, when is the next scheduled {descriptor_noun} dose?",
                paraphrases=(
                    f"What is the next scheduled administration date for the {descriptor_noun}?",
                    f"Give the next upcoming {descriptor_noun} dose date on or after the reference date.",
                ),
                answer_fn=ans_next,
                provenance=f"MedicationAdministration[component={component_id}].effectiveDateTime",
            ),
            QuestionTemplate(
                template_id=f"tl.last_administered.{component_id}",
                qtype="temporal_lookup",
                question=f"What is the most recent {descriptor_noun} administration on or before the reference date?",
                paraphrases=(
                    f"On the reference date, when was the last {descriptor_noun} administered?",
                    f"Give the most recent administration date of the {descriptor_noun} prior to (or on) the reference date.",
                ),
                answer_fn=ans_last,
                provenance=f"MedicationAdministration[component={component_id}].effectiveDateTime",
            ),
            QuestionTemplate(
                template_id=f"tl.days_to_next.{component_id}",
                qtype="temporal_lookup",
                question=f"How many days from the reference date until the next scheduled {descriptor_noun} dose?",
                paraphrases=(
                    f"Count the number of days until the upcoming {descriptor_noun} administration.",
                    f"How many days remain before the next {descriptor_noun} dose?",
                ),
                answer_fn=ans_days_to_next,
                provenance=f"MedicationAdministration[component={component_id}].effectiveDateTime",
            ),
            QuestionTemplate(
                template_id=f"tl.days_since_last.{component_id}",
                qtype="temporal_lookup",
                question=f"How many days have elapsed since the most recent {descriptor_noun} administration?",
                paraphrases=(
                    f"Count the days since the last {descriptor_noun} dose.",
                    f"On the reference date, how long ago (in days) was the most recent {descriptor_noun} administration?",
                ),
                answer_fn=ans_days_since_last,
                provenance=f"MedicationAdministration[component={component_id}].effectiveDateTime",
            ),
        ]
    )
    return out


def _regimen_dates_questions() -> list[QuestionTemplate]:
    def ans_start(meta: dict[str, Any], ref: date) -> Any:
        return parse_date(meta["regimen_start"])

    def ans_end(meta: dict[str, Any], ref: date) -> Any:
        return parse_date(meta["regimen_end"])

    def ans_first_admin_any(meta: dict[str, Any], ref: date) -> Any:
        firsts = [
            parse_date(c["dose_event_dates"][0])
            for c in meta["components"]
            if c.get("dose_event_dates")
        ]
        return min(firsts) if firsts else NA

    def ans_last_admin_any(meta: dict[str, Any], ref: date) -> Any:
        lasts = [
            parse_date(c["dose_event_dates"][-1])
            for c in meta["components"]
            if c.get("dose_event_dates")
        ]
        return max(lasts) if lasts else NA

    return [
        QuestionTemplate(
            template_id="tl.regimen_start",
            qtype="temporal_lookup",
            question="What is the start date of the specialty regimen?",
            paraphrases=(
                "When did this specialty regimen begin?",
                "Give the regimen's start date.",
            ),
            answer_fn=ans_start,
            provenance="CarePlan.period.start",
        ),
        QuestionTemplate(
            template_id="tl.regimen_end",
            qtype="temporal_lookup",
            question="What is the end date of the projected regimen horizon?",
            paraphrases=(
                "When does the regimen horizon end?",
                "Give the last date of the projected regimen window.",
            ),
            answer_fn=ans_end,
            provenance="CarePlan.period.end",
        ),
        QuestionTemplate(
            template_id="tl.first_admin_any",
            qtype="temporal_lookup",
            question="What is the earliest administration date across all regimen components?",
            paraphrases=(
                "Across all components, when did the first administration occur?",
                "Give the earliest dose-event date in the regimen.",
            ),
            answer_fn=ans_first_admin_any,
            provenance="min(MedicationAdministration.effectiveDateTime)",
        ),
        QuestionTemplate(
            template_id="tl.last_admin_any",
            qtype="temporal_lookup",
            question="What is the latest administration date across all regimen components?",
            paraphrases=(
                "Across all components, when did the most recent administration occur?",
                "Give the latest dose-event date in the regimen.",
            ),
            answer_fn=ans_last_admin_any,
            provenance="max(MedicationAdministration.effectiveDateTime)",
        ),
    ]


def templates() -> list[QuestionTemplate]:
    out: list[QuestionTemplate] = []
    out.extend(_component_question("primary", "primary regimen"))
    out.extend(_component_question("adjunct", "oral adjunct"))
    out.extend(_component_question("rescue", "PRN rescue"))
    out.extend(_regimen_dates_questions())
    return out  # 4*3 + 4 = 16; short of 24 but the other types pick up slack.
