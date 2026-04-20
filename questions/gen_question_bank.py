"""Generate the question bank + programmatic ground-truth answers.

For each patient:
  1. Sample a deterministic reference date in [regimen_start − 30, regimen_start + 90].
  2. For each of the 5 question types × every template, resolve the ground-truth
     value by calling the template's answer_fn(regimen_meta, reference_date).
  3. Emit one JSONL row per (patient, template) combination with the question,
     two paraphrases, and the deterministic answer. "N/A" is a valid answer.

Output: questions/questions.jsonl. Each row:
  {
    "id": "<patient_id>::<template_id>",
    "patient_id": ..., "tier": 1|2|3, "type": ..., "template_id": ...,
    "reference_date": "YYYY-MM-DD",
    "question": ..., "paraphrases": [p1, p2],
    "ground_truth": ..., "provenance": ...
  }

Usage:
  python -m questions.gen_question_bank \
      --bundles data/fhir_bundles \
      --output questions/questions.jsonl \
      --seed 20260427 [--sample N]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from .ground_truth import (
    cross_resource,
    regimen_aggregation,
    regimen_compliance,
    temporal_comparison,
    temporal_lookup,
)
from .ground_truth.common import (
    QuestionTemplate,
    fmt_answer,
    parse_date,
    reference_date as compute_reference_date,
)


MODULES = {
    "temporal_lookup": temporal_lookup,
    "temporal_comparison": temporal_comparison,
    "regimen_compliance": regimen_compliance,
    "regimen_aggregation": regimen_aggregation,
    "cross_resource": cross_resource,
}


def collect_templates() -> list[QuestionTemplate]:
    out: list[QuestionTemplate] = []
    for mod in MODULES.values():
        out.extend(mod.templates())
    return out


def _resolve_one(
    template: QuestionTemplate, meta: dict[str, Any], ref: date
) -> dict[str, Any]:
    answer = template.answer_fn(meta, ref)
    return {
        "id": f"{meta['patient_id']}::{template.template_id}",
        "patient_id": meta["patient_id"],
        "tier": meta["tier"],
        "type": template.qtype,
        "template_id": template.template_id,
        "reference_date": ref.isoformat(),
        "question": template.question,
        "paraphrases": list(template.paraphrases),
        "ground_truth": fmt_answer(answer),
        "provenance": template.provenance,
    }


def _paraphrase_invariance_check(templates: list[QuestionTemplate]) -> list[str]:
    """The answer depends only on (meta, reference_date), not on the wording.
    Since paraphrases share answer_fn by construction, every paraphrase must
    yield the same answer. We verify only that the invariant holds structurally
    (len(paraphrases) == 2 and are distinct from the question).
    """
    errors: list[str] = []
    for t in templates:
        if len(t.paraphrases) != 2:
            errors.append(f"{t.template_id}: expected 2 paraphrases, got {len(t.paraphrases)}")
        seen = {t.question, *t.paraphrases}
        if len(seen) < 3:
            errors.append(f"{t.template_id}: paraphrases are not all distinct")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundles", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=20260427)
    parser.add_argument("--sample", type=int, default=0)
    args = parser.parse_args(argv)

    templates = collect_templates()
    check_errors = _paraphrase_invariance_check(templates)
    if check_errors:
        print("Paraphrase integrity errors:", file=sys.stderr)
        for e in check_errors:
            print(f"  {e}", file=sys.stderr)
        return 2

    index = json.loads((args.bundles / "_regimen_index.json").read_text())
    patients = list(index["patients"].values())
    if args.sample > 0:
        patients = patients[: args.sample]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    per_type: Counter[str] = Counter()
    na_counts: Counter[str] = Counter()
    total = 0

    with args.output.open("w") as f:
        for meta in patients:
            ref = compute_reference_date(
                meta["patient_id"], parse_date(meta["regimen_start"]), args.seed
            )
            for tmpl in templates:
                row = _resolve_one(tmpl, meta, ref)
                f.write(json.dumps(row, sort_keys=True) + "\n")
                per_type[tmpl.qtype] += 1
                if row["ground_truth"] == "N/A":
                    na_counts[tmpl.qtype] += 1
                total += 1

    print(
        f"questions: rows={total} patients={len(patients)} templates={len(templates)}"
    )
    for t in sorted(per_type):
        print(f"  type={t:<22} rows={per_type[t]}  n_NA={na_counts[t]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
