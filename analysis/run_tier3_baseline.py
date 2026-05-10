"""Compute Tier-3 most-frequent-class baseline against the three retrieval systems.

For each question family, the modal ground-truth string is identified within
Tier 3 and scored against the actual ground truth (exact match). Wilson 95%
CIs are reported per cell and overall, alongside the system accuracies at
Tier 3 from results/scored.csv.

Usage::

    C:/ProgramData/miniconda3/envs/ml/python.exe analysis/run_tier3_baseline.py

Output: analysis/tier3_baseline.md (rewritten in place).
"""
from __future__ import annotations

from math import sqrt
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SCORED = ROOT / "results" / "scored.csv"
OUT_MD = ROOT / "analysis" / "tier3_baseline.md"


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (centre - half, centre + half)


def main() -> None:
    df = pd.read_csv(SCORED, low_memory=False)
    a = df[df["system"] == "a"].copy()
    a["ground_truth_str"] = a["ground_truth"].astype(str)
    tier3 = a[a["tier"] == 3]

    rows = []
    overall_correct = 0
    overall_n = 0
    for fam, sub in tier3.groupby("family"):
        n = len(sub)
        counts = sub["ground_truth_str"].value_counts()
        modal_val = counts.index[0]
        modal_freq = int(counts.iloc[0])
        acc = modal_freq / n
        lo, hi = wilson_ci(modal_freq, n)
        rows.append((fam, n, modal_val, modal_freq, acc, lo, hi))
        overall_correct += modal_freq
        overall_n += n

    overall_acc = overall_correct / overall_n
    overall_lo, overall_hi = wilson_ci(overall_correct, overall_n)

    counts = tier3["ground_truth_str"].value_counts()
    global_modal = counts.index[0]
    global_freq = int(counts.iloc[0])
    global_n = len(tier3)
    global_lo, global_hi = wilson_ci(global_freq, global_n)

    print("Tier 3 per-family most-frequent-class baseline:")
    for fam, n, mv, mf, acc, lo, hi in rows:
        print(f"  {fam:<25}  n={n:<5} modal={mv!r:<25} acc={acc:.4f}  [{lo:.3f},{hi:.3f}]")
    print(
        f"\nOverall per-family baseline: {overall_correct}/{overall_n} = "
        f"{overall_acc:.4f} [{overall_lo:.4f}, {overall_hi:.4f}]"
    )
    print(
        f"\nGlobal modal baseline ('{global_modal}'): {global_freq}/{global_n} = "
        f"{global_freq / global_n:.4f} [{global_lo:.4f}, {global_hi:.4f}]"
    )

    print("\nSystem accuracies at Tier 3:")
    for sys in ("a", "b", "c"):
        sub = df[(df["system"] == sys) & (df["tier"] == 3)]
        n = len(sub)
        k = int(sub["exact_match"].sum())
        lo, hi = wilson_ci(k, n)
        print(f"  System {sys}: {k}/{n} = {k / n:.4f} [{lo:.4f}, {hi:.4f}]")


if __name__ == "__main__":
    main()
