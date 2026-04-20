"""Temporal comparison questions — "which is earlier/later?", "before/after?"."""
from __future__ import annotations

from datetime import date
from typing import Any

from .common import (
    NA,
    QuestionTemplate,
    get_component,
    last_administered,
    next_scheduled,
    parse_date,
)


def _pair_templates(a: str, b: str, a_noun: str, b_noun: str) -> list[QuestionTemplate]:
    out: list[QuestionTemplate] = []

    def ans_earlier_start(meta: dict[str, Any], ref: date) -> Any:
        ca = get_component(meta, a)
        cb = get_component(meta, b)
        if not ca or not cb:
            return NA
        da = ca.get("dose_event_dates") or []
        db = cb.get("dose_event_dates") or []
        if not da or not db:
            return NA
        start_a = parse_date(da[0])
        start_b = parse_date(db[0])
        if start_a == start_b:
            return "same-day"
        return a_noun if start_a < start_b else b_noun

    def ans_latest_admin(meta: dict[str, Any], ref: date) -> Any:
        ca = get_component(meta, a)
        cb = get_component(meta, b)
        if not ca or not cb:
            return NA
        la = last_administered(ca, ref)
        lb = last_administered(cb, ref)
        if la == NA and lb == NA:
            return NA
        if la == NA:
            return b_noun
        if lb == NA:
            return a_noun
        if la == lb:
            return "same-day"
        return a_noun if la > lb else b_noun

    def ans_next_first(meta: dict[str, Any], ref: date) -> Any:
        ca = get_component(meta, a)
        cb = get_component(meta, b)
        if not ca or not cb:
            return NA
        na_ = next_scheduled(ca, ref)
        nb_ = next_scheduled(cb, ref)
        if na_ == NA and nb_ == NA:
            return NA
        if na_ == NA:
            return b_noun
        if nb_ == NA:
            return a_noun
        if na_ == nb_:
            return "same-day"
        return a_noun if na_ < nb_ else b_noun

    out.extend(
        [
            QuestionTemplate(
                template_id=f"tc.earlier_start.{a}_vs_{b}",
                qtype="temporal_comparison",
                question=f"Between the {a_noun} and the {b_noun}, which component started first?",
                paraphrases=(
                    f"Which started earlier: the {a_noun} or the {b_noun}?",
                    f"Compare the first administration dates of the {a_noun} and the {b_noun}.",
                ),
                answer_fn=ans_earlier_start,
                provenance=f"min(MedicationAdministration[{a}].effectiveDateTime) vs {b}",
            ),
            QuestionTemplate(
                template_id=f"tc.latest_admin.{a}_vs_{b}",
                qtype="temporal_comparison",
                question=f"Which component was administered most recently — the {a_noun} or the {b_noun}?",
                paraphrases=(
                    f"Between the {a_noun} and the {b_noun}, which had the latest administration on or before the reference date?",
                    f"On the reference date, which was administered more recently: the {a_noun} or the {b_noun}?",
                ),
                answer_fn=ans_latest_admin,
                provenance="compare last_administered per component",
            ),
            QuestionTemplate(
                template_id=f"tc.next_first.{a}_vs_{b}",
                qtype="temporal_comparison",
                question=f"Which component is next due first on or after the reference date — the {a_noun} or the {b_noun}?",
                paraphrases=(
                    f"Which comes up sooner: the next {a_noun} dose or the next {b_noun} dose?",
                    f"Between the {a_noun} and the {b_noun}, whose next scheduled administration is earlier?",
                ),
                answer_fn=ans_next_first,
                provenance="compare next_scheduled per component",
            ),
        ]
    )
    return out


def _ref_vs_last_admin(component_id: str, descriptor: str) -> list[QuestionTemplate]:
    def ans(meta: dict[str, Any], ref: date) -> Any:
        c = get_component(meta, component_id)
        if not c:
            return NA
        la = last_administered(c, ref)
        if la == NA:
            return "no-prior-administration"
        if la == ref:
            return "same-day"
        return "before" if la < ref else "after"

    return [
        QuestionTemplate(
            template_id=f"tc.ref_vs_last.{component_id}",
            qtype="temporal_comparison",
            question=f"Is the most recent {descriptor} administration before, on, or after the reference date?",
            paraphrases=(
                f"Relative to the reference date, when did the last {descriptor} dose occur?",
                f"Was the previous {descriptor} administration earlier than, on, or later than the reference date?",
            ),
            answer_fn=ans,
            provenance=f"last MedicationAdministration[{component_id}] vs reference_date",
        ),
    ]


def templates() -> list[QuestionTemplate]:
    out: list[QuestionTemplate] = []
    out.extend(_pair_templates("primary", "adjunct", "primary regimen", "oral adjunct"))
    out.extend(_pair_templates("primary", "rescue", "primary regimen", "PRN rescue"))
    out.extend(_pair_templates("adjunct", "rescue", "oral adjunct", "PRN rescue"))
    out.extend(_ref_vs_last_admin("primary", "primary regimen"))
    out.extend(_ref_vs_last_admin("adjunct", "oral adjunct"))
    out.extend(_ref_vs_last_admin("rescue", "PRN rescue"))
    return out  # 3*3 + 3 = 12
