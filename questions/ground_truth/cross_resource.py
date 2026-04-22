"""Cross-resource reasoning questions — references, consistency, tier metadata."""
from __future__ import annotations

from datetime import date
from typing import Any

from .common import NA, QuestionTemplate, get_component


def _has_component_template(component_id: str, descriptor: str) -> QuestionTemplate:
    def ans(meta: dict[str, Any], ref: date) -> Any:
        return "yes" if get_component(meta, component_id) else "no"

    return QuestionTemplate(
        template_id=f"cr.has.{component_id}",
        qtype="cross_resource",
        question=f"Does this patient's regimen include a {descriptor} component?",
        paraphrases=(
            f"Is a {descriptor} part of the regimen?",
            f"Does the regimen contain a {descriptor} medication?",
        ),
        answer_fn=ans,
        provenance=f"any(component.id == '{component_id}')",
    )


def _tier_label_template() -> QuestionTemplate:
    def ans(meta: dict[str, Any], ref: date) -> Any:
        return meta["tier_label"]

    return QuestionTemplate(
        template_id="cr.tier_label",
        qtype="cross_resource",
        question="What is the tier label assigned to this patient's specialty regimen?",
        paraphrases=(
            "Give the regimen's tier label.",
            "Report the tier-label string for this patient.",
        ),
        answer_fn=ans,
        provenance="CarePlan.note → regimen_index.tier_label",
    )


def _tier_number_template() -> QuestionTemplate:
    def ans(meta: dict[str, Any], ref: date) -> Any:
        return int(meta["tier"])

    return QuestionTemplate(
        template_id="cr.tier_number",
        qtype="cross_resource",
        question="What is the complexity tier (1, 2, or 3) of this patient's regimen?",
        paraphrases=(
            "Which complexity tier is this regimen in?",
            "Give the regimen's complexity tier as an integer from 1 to 3.",
        ),
        answer_fn=ans,
        provenance="regimen_index.tier",
    )


def _schedule_kind_template(component_id: str, descriptor: str) -> QuestionTemplate:
    def ans(meta: dict[str, Any], ref: date) -> Any:
        c = get_component(meta, component_id)
        if not c:
            return NA
        kind = c.get("schedule_kind")
        # Return the three valid schedule kinds used in the dataset
        return kind if kind in {"fixed_interval", "cyclic", "prn"} else NA

    return QuestionTemplate(
        template_id=f"cr.schedule_kind.{component_id}",
        qtype="cross_resource",
        question=f"What schedule kind (fixed_interval, cyclic, or prn) applies to the {descriptor} component?",
        paraphrases=(
            f"How is the {descriptor} scheduled: fixed_interval, cyclic, or prn?",
            f"Report the schedule classification of the {descriptor}.",
        ),
        answer_fn=ans,
        provenance=f"MedicationRequest[{component_id}].dosageInstruction.timing",
    )


def templates() -> list[QuestionTemplate]:
    out: list[QuestionTemplate] = []
    for comp_id, descr in [
        ("primary", "primary regimen"),
        ("adjunct", "oral adjunct"),
        ("rescue", "PRN rescue"),
    ]:
        out.append(_has_component_template(comp_id, descr))
        out.append(_schedule_kind_template(comp_id, descr))
    out.append(_tier_label_template())
    out.append(_tier_number_template())
    return out  # 3*2 + 2 = 8
