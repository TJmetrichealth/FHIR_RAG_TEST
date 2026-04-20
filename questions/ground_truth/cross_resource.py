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


def _med_request_linked(component_id: str, descriptor: str) -> QuestionTemplate:
    def ans(meta: dict[str, Any], ref: date) -> Any:
        c = get_component(meta, component_id)
        if not c:
            return NA
        has_req = bool(c.get("request_ref"))
        has_med = bool(c.get("medication_ref"))
        return "yes" if has_req and has_med else "no"

    return QuestionTemplate(
        template_id=f"cr.medreq_linked.{component_id}",
        qtype="cross_resource",
        question=f"Is the {descriptor} MedicationAdministration linked to a MedicationRequest and a Medication resource?",
        paraphrases=(
            f"For the {descriptor}, do the administration events reference both a MedicationRequest and a Medication?",
            f"Does the {descriptor} have a complete reference chain (MedicationAdministration → MedicationRequest → Medication)?",
        ),
        answer_fn=ans,
        provenance=f"MedicationAdministration[{component_id}].request and .medicationReference",
    )


def _careplan_references_all() -> QuestionTemplate:
    def ans(meta: dict[str, Any], ref: date) -> Any:
        n_components = len(meta["components"])
        careplan_id = meta.get("careplan_ref")
        if not careplan_id:
            return NA
        # The overlay always puts every component's MedicationRequest in CarePlan.activity
        return "yes" if n_components > 0 else "no"

    return QuestionTemplate(
        template_id="cr.careplan_covers_all",
        qtype="cross_resource",
        question="Does the CarePlan reference a MedicationRequest for every component in the regimen?",
        paraphrases=(
            "Are all regimen components covered by the CarePlan's activity list?",
            "For each medication component, is there a corresponding CarePlan.activity entry?",
        ),
        answer_fn=ans,
        provenance="len(CarePlan.activity) == len(components)",
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
        out.append(_med_request_linked(comp_id, descr))
        out.append(_schedule_kind_template(comp_id, descr))
    out.append(_careplan_references_all())
    out.append(_tier_label_template())
    out.append(_tier_number_template())
    return out  # 3*3 + 3 = 12
