"""Compare 512-token vs 1024-token accuracy on the stratified 495-question sample.

Reads:
  results_1024/scored.csv   (output of: eval.score --raw-dir results/raw_1024
                                              --output-dir results_1024)
  results/scored.csv        (the production 512-token results)

Computes for each system:
  - 512-token accuracy on the 495 sampled question_ids (paired subset)
  - 1024-token accuracy on the same 495 question_ids
  - Paired delta (1024 - 512) with paired-bootstrap 95% CI (10,000 resamples)

Then prints overall, per-tier, and per-family deltas.

Usage::

    C:/ProgramData/miniconda3/envs/ml/python.exe analysis/run_token_sweep_compare.py
"""
from __future__ import annotations

from math import sqrt
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SCORED_512 = ROOT / "results" / "scored.csv"
SCORED_1024 = ROOT / "results_1024" / "scored.csv"
OUT_MD = ROOT / "analysis" / "token_sweep_compare.md"


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (centre - half, centre + half)


def paired_bootstrap_ci(
    diffs: np.ndarray, n_resamples: int = 10_000, seed: int = 42
) -> tuple[float, float, float]:
    """Return (mean diff, lo, hi) for a paired bootstrap on diffs."""
    rng = np.random.default_rng(seed)
    n = len(diffs)
    means = np.empty(n_resamples)
    for i in range(n_resamples):
        idx = rng.integers(0, n, size=n)
        means[i] = diffs[idx].mean()
    lo, hi = np.percentile(means, [2.5, 97.5])
    return float(diffs.mean()), float(lo), float(hi)


def main() -> None:
    df_512 = pd.read_csv(SCORED_512, low_memory=False)
    df_1024 = pd.read_csv(SCORED_1024, low_memory=False)

    sample_qids = set(df_1024["question_id"].astype(str))
    print(f"1024-token sample size: {len(sample_qids)} unique question_ids")

    df_512_sub = df_512[df_512["question_id"].astype(str).isin(sample_qids)].copy()
    df_512_sub["budget"] = 512
    df_1024 = df_1024.copy()
    df_1024["budget"] = 1024

    lines: list[str] = ["# 512 vs 1024 Token Sweep Comparison\n"]
    lines.append(
        f"Stratified sample: {len(sample_qids)} question_ids "
        f"(33 per tier x family cell, seed 42).\n"
    )
    lines.append("Same question_ids used at 512 and 1024 tokens for paired comparison.\n")

    for sys in ("a", "b", "c"):
        print(f"\n=== System {sys} ===")
        lines.append(f"\n## System {sys}\n")
        s512 = df_512_sub[df_512_sub["system"] == sys].copy()
        s1024 = df_1024[df_1024["system"] == sys].copy()
        if s512.empty or s1024.empty:
            lines.append(f"_System {sys}: missing data (512 n={len(s512)}, 1024 n={len(s1024)})_\n")
            continue
        merged = s512.merge(
            s1024[["question_id", "exact_match", "tier", "family"]],
            on="question_id",
            suffixes=("_512", "_1024"),
        )
        n = len(merged)
        a512 = merged["exact_match_512"].astype(int)
        a1024 = merged["exact_match_1024"].astype(int)
        k512, k1024 = int(a512.sum()), int(a1024.sum())
        acc512, acc1024 = k512 / n, k1024 / n
        lo512, hi512 = wilson_ci(k512, n)
        lo1024, hi1024 = wilson_ci(k1024, n)

        diffs = (a1024 - a512).to_numpy()
        d_mean, d_lo, d_hi = paired_bootstrap_ci(diffs)

        print(f"  n={n}, 512 acc={acc512:.4f} [{lo512:.3f},{hi512:.3f}], "
              f"1024 acc={acc1024:.4f} [{lo1024:.3f},{hi1024:.3f}]")
        print(f"  paired delta = {d_mean:+.4f} [{d_lo:+.4f}, {d_hi:+.4f}] "
              f"(bootstrap 10k, seed 42)")

        lines.append(
            f"- 512-token: {k512}/{n} = {acc512:.4f} "
            f"[Wilson 95% CI {lo512:.3f}, {hi512:.3f}]\n"
            f"- 1024-token: {k1024}/{n} = {acc1024:.4f} "
            f"[Wilson 95% CI {lo1024:.3f}, {hi1024:.3f}]\n"
            f"- Paired delta (1024 - 512): {d_mean:+.4f} "
            f"[bootstrap 95% CI {d_lo:+.4f}, {d_hi:+.4f}]\n"
        )

        lines.append("\n### By tier\n")
        lines.append("| Tier | n | 512 acc | 1024 acc | delta | bootstrap 95% CI |\n")
        lines.append("|---|---|---|---|---|---|\n")
        for tier, sub in merged.groupby("tier_512"):
            sn = len(sub)
            sa512 = sub["exact_match_512"].astype(int)
            sa1024 = sub["exact_match_1024"].astype(int)
            sd = (sa1024 - sa512).to_numpy()
            dm, dlo, dhi = paired_bootstrap_ci(sd)
            print(f"  Tier {tier}: n={sn}, 512={sa512.mean():.4f}, 1024={sa1024.mean():.4f}, "
                  f"delta={dm:+.4f} [{dlo:+.4f}, {dhi:+.4f}]")
            lines.append(
                f"| {tier} | {sn} | {sa512.mean():.4f} | {sa1024.mean():.4f} | "
                f"{dm:+.4f} | [{dlo:+.4f}, {dhi:+.4f}] |\n"
            )

        lines.append("\n### By family\n")
        lines.append("| Family | n | 512 acc | 1024 acc | delta | bootstrap 95% CI |\n")
        lines.append("|---|---|---|---|---|---|\n")
        for fam, sub in merged.groupby("family_512"):
            sn = len(sub)
            sa512 = sub["exact_match_512"].astype(int)
            sa1024 = sub["exact_match_1024"].astype(int)
            sd = (sa1024 - sa512).to_numpy()
            dm, dlo, dhi = paired_bootstrap_ci(sd)
            print(f"  {fam:<22} n={sn}: 512={sa512.mean():.4f}, 1024={sa1024.mean():.4f}, "
                  f"delta={dm:+.4f} [{dlo:+.4f}, {dhi:+.4f}]")
            lines.append(
                f"| {fam} | {sn} | {sa512.mean():.4f} | {sa1024.mean():.4f} | "
                f"{dm:+.4f} | [{dlo:+.4f}, {dhi:+.4f}] |\n"
            )

    OUT_MD.write_text("".join(lines), encoding="utf-8")
    print(f"\nWrote {OUT_MD}")


if __name__ == "__main__":
    main()
