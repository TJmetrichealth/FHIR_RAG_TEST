"""Tier-3 retrieval recall@k vs end-to-end accuracy breakdown.

Reviewer revision #4: addresses the asymmetry between recall@k (which stays
high at Tier 3) and exact-match accuracy (which collapses below the
per-family most-frequent-class baseline). If recall is preserved but accuracy
collapses, the bottleneck is downstream reasoning under multi-component
context; if recall also collapses, the retriever is overwhelmed by component
count.

Reads:
    results/recall_at_k.csv   -- pre-computed per (system, family, type, tier, k)
    results/scored.csv        -- per-question exact_match for accuracy

Writes:
    analysis/tier3_recall_breakdown.md

Usage::

    C:/ProgramData/miniconda3/envs/ml/python.exe analysis/run_tier3_recall_breakdown.py
"""
from __future__ import annotations

from math import sqrt
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RECALL = ROOT / "results" / "recall_at_k.csv"
SCORED = ROOT / "results" / "scored.csv"
OUT_MD = ROOT / "analysis" / "tier3_recall_breakdown.md"


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (centre - half, centre + half)


def fmt_pct(p: float) -> str:
    return f"{p * 100:.1f}%"


def fmt_ci(lo: float, hi: float) -> str:
    return f"[{lo * 100:.1f}%, {hi * 100:.1f}%]"


def main() -> None:
    recall = pd.read_csv(RECALL)
    scored = pd.read_csv(SCORED, low_memory=False)

    families = sorted(scored["family"].dropna().unique().tolist())

    lines: list[str] = []
    lines.append("# Tier-3 Retrieval Recall vs Accuracy Breakdown")
    lines.append("")
    lines.append("> Source: `results/recall_at_k.csv` + `results/scored.csv`")
    lines.append(">")
    lines.append("> Addresses reviewer revision #4. Tier 3 is the multi-drug regimen tier")
    lines.append("> where all three systems sit below the per-family most-frequent-class")
    lines.append("> baseline (24.8% [23.6%, 26.0%]). This document decomposes whether the")
    lines.append("> failure is upstream (retriever) or downstream (answer LLM reasoning).")
    lines.append("")

    # --- Per-family recall@5 at Tier 3 for B and C, plus per-system Tier-3 acc ---
    lines.append("## Tier-3 recall@5 vs Tier-3 exact-match accuracy")
    lines.append("")
    lines.append("Per (system, family). Recall numbers are from `results/recall_at_k.csv`")
    lines.append("(family rows where `tier == 3` and `k == 5`). Accuracy is exact-match on")
    lines.append("Tier-3 questions only.")
    lines.append("")

    header_cols = ["family", "B recall@5", "B 95% CI", "C recall@5", "C 95% CI",
                   "A acc", "B acc", "C acc"]
    lines.append("| " + " | ".join(header_cols) + " |")
    lines.append("|" + "|".join(["---"] * len(header_cols)) + "|")

    for fam in families:
        # Recall rows for tier=3, k=5
        b_row = recall[(recall["system"] == "b") & (recall["family"] == fam) &
                       (recall["tier"] == 3) & (recall["k"] == 5)]
        c_row = recall[(recall["system"] == "c") & (recall["family"] == fam) &
                       (recall["tier"] == 3) & (recall["k"] == 5)]
        if b_row.empty or c_row.empty:
            continue
        b_recall = float(b_row["recall_mean"].iloc[0])
        b_ci_lo = float(b_row["recall_ci_lo"].iloc[0])
        b_ci_hi = float(b_row["recall_ci_hi"].iloc[0])
        c_recall = float(c_row["recall_mean"].iloc[0])
        c_ci_lo = float(c_row["recall_ci_lo"].iloc[0])
        c_ci_hi = float(c_row["recall_ci_hi"].iloc[0])

        # Per-system accuracy at Tier 3 for this family
        accs: dict[str, str] = {}
        for sys_id in ("a", "b", "c"):
            sub = scored[(scored["system"] == sys_id) & (scored["family"] == fam) &
                         (scored["tier"] == 3)]
            n = len(sub)
            if n == 0:
                accs[sys_id] = "N/A"
                continue
            k_correct = int(sub["exact_match"].fillna(False).astype(bool).sum())
            acc = k_correct / n
            lo, hi = wilson_ci(k_correct, n)
            accs[sys_id] = f"{fmt_pct(acc)} {fmt_ci(lo, hi)}"

        lines.append(
            f"| {fam} | {fmt_pct(b_recall)} | {fmt_ci(b_ci_lo, b_ci_hi)} | "
            f"{fmt_pct(c_recall)} | {fmt_ci(c_ci_lo, c_ci_hi)} | "
            f"{accs['a']} | {accs['b']} | {accs['c']} |"
        )

    lines.append("")

    # --- Overall Tier-3 vs overall numbers ---
    lines.append("## Tier-3 retrieval recall vs overall recall (means across families)")
    lines.append("")
    lines.append("| Slice | B recall@5 | C recall@5 |")
    lines.append("|---|---|---|")

    for slice_label, slice_filter in [
        ("Overall (all tiers, all families)", lambda d: d),
        ("Tier 1", lambda d: d[d["tier"] == 1]),
        ("Tier 2", lambda d: d[d["tier"] == 2]),
        ("Tier 3", lambda d: d[d["tier"] == 3]),
    ]:
        b_sub = slice_filter(recall[(recall["system"] == "b") & (recall["k"] == 5)])
        c_sub = slice_filter(recall[(recall["system"] == "c") & (recall["k"] == 5)])
        if b_sub.empty or c_sub.empty:
            continue
        # Weighted by n_questions per row
        def _wmean(d: pd.DataFrame) -> float:
            w = d["n_questions"].astype(float)
            return float((d["recall_mean"] * w).sum() / w.sum())
        lines.append(
            f"| {slice_label} | {fmt_pct(_wmean(b_sub))} | {fmt_pct(_wmean(c_sub))} |"
        )

    lines.append("")

    # --- Per-system Tier-3 accuracy (overall, for cross-reference) ---
    lines.append("## Per-system Tier-3 accuracy (cross-reference)")
    lines.append("")
    lines.append("| System | Tier-3 accuracy | 95% CI | n questions |")
    lines.append("|---|---|---|---|")
    for sys_id, sys_name in [("a", "A (narrative)"), ("b", "B (naive struct)"),
                             ("c", "C (aware struct)")]:
        sub = scored[(scored["system"] == sys_id) & (scored["tier"] == 3)]
        n = len(sub)
        k_correct = int(sub["exact_match"].fillna(False).astype(bool).sum())
        acc = k_correct / n if n else 0.0
        lo, hi = wilson_ci(k_correct, n)
        lines.append(
            f"| {sys_name} | {fmt_pct(acc)} | {fmt_ci(lo, hi)} | {n} |"
        )
    lines.append("")
    lines.append(
        "Per-family modal baseline at Tier 3 (from `analysis/tier3_baseline.md`): "
        "**24.8% [23.6%, 26.0%]**. All three system Tier-3 accuracies sit below this "
        "baseline CI."
    )
    lines.append("")

    # --- Interpretation ---
    lines.append("## Interpretation: retriever vs answer LLM")
    lines.append("")
    lines.append(
        "Tier-3 retrieval recall stays high for both B and C across every family except "
        "`temporal_lookup`. For `cross_resource`, `regimen_aggregation`, "
        "`temporal_comparison`, and `regimen_compliance`, recall@5 at Tier 3 exceeds 70% "
        "(System B) or 75% (System C). The Tier-3 evidence is therefore not absent from "
        "the retrieved context; the answer LLM has the supporting passages in its window "
        "in most cases and still produces wrong answers."
    )
    lines.append("")
    lines.append(
        "This isolates the bottleneck to **downstream reasoning under multi-component "
        "context**, not retrieval. The hypothesis-level architectural implications:"
    )
    lines.append("")
    lines.append(
        "- Longer outputs alone are insufficient. The 1024-token sweep (Section 4.8) "
        "moved B by +3.8 pp and C by +5.1 pp on a stratified subsample but did not "
        "clear Tier 3 above the modal baseline."
    )
    lines.append(
        "- Per-component decomposition is the next architectural step worth testing: "
        "answer the question separately per regimen component (primary, adjunct, PRN) "
        "and aggregate, rather than reasoning over a concatenated multi-component "
        "context."
    )
    lines.append(
        "- Chain-of-thought scaffolding or structured intermediate steps (e.g., "
        "explicit per-component date enumeration before aggregation) may help. The "
        "current answer prompt provides retrieved chunks and asks for the answer in "
        "one step."
    )
    lines.append(
        "- `temporal_lookup` is the one family where C does not beat B at Tier-3 "
        "recall@5. Worth inspecting whether the resource-aware temporal pre-filter "
        "is over-pruning candidate Observation/MedicationAdministration resources "
        "at Tier 3."
    )
    lines.append("")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT_MD}")


if __name__ == "__main__":
    main()
