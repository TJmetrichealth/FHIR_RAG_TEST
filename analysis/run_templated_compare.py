"""Score the templated-narrative arm and compute paired delta vs canonical System A.

Reads:
    results/raw_templated/a_templated.jsonl  -- templated arm raw outputs
    results/scored.csv                       -- canonical scored CSV (for A)
    questions/questions.jsonl                -- for metadata fill

Writes:
    results/scored_templated/scored.csv      -- scored templated results
    results/scored_templated/recall_at_k.csv
    results/scored_templated/latency_tokens.csv
    analysis/templated_compare.md            -- markdown comparison

Usage::

    C:/ProgramData/miniconda3/envs/ml/python.exe analysis/run_templated_compare.py
"""
from __future__ import annotations

import json
import sys
from math import sqrt
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from eval.score import run_scoring

RAW_DIR = ROOT / "results" / "raw_templated"
SCORED_DIR = ROOT / "results" / "scored_templated"
CANONICAL_SCORED = ROOT / "results" / "scored.csv"
QUESTIONS_PATH = ROOT / "questions" / "questions.jsonl"
BUNDLES_DIR = ROOT / "data" / "fhir_bundles"
OUT_MD = ROOT / "analysis" / "templated_compare.md"


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


def main() -> None:
    # 1. Score templated raw output if not already done
    SCORED_DIR.mkdir(parents=True, exist_ok=True)
    scored_path = SCORED_DIR / "scored.csv"
    if not scored_path.exists():
        print(f"[compare] scoring {RAW_DIR}/a_templated.jsonl ...")
        # The scorer expects files named <system>.jsonl. Rename or symlink? Simpler:
        # copy and read as system_a_templated.
        raw_target = RAW_DIR / "system_a_templated.jsonl"
        if not raw_target.exists():
            src = RAW_DIR / "a_templated.jsonl"
            raw_target.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        run_scoring(
            raw_dir=RAW_DIR,
            questions_path=QUESTIONS_PATH,
            output_dir=SCORED_DIR,
            bundles_dir=BUNDLES_DIR,
            system_names=["system_a_templated"],
        )
    else:
        print(f"[compare] templated already scored at {scored_path}")

    # 2. Load both scored CSVs
    t = pd.read_csv(scored_path, low_memory=False)
    canonical = pd.read_csv(CANONICAL_SCORED, low_memory=False)
    a = canonical[canonical["system"] == "a"].copy()

    # 3. Align by question_id
    t_em = t.set_index("question_id")["exact_match"].fillna(False).astype(bool)
    a_em = a.set_index("question_id")["exact_match"].fillna(False).astype(bool)
    a_tier = a.set_index("question_id")["tier"]
    a_family = a.set_index("question_id")["family"]
    common = t_em.index.intersection(a_em.index)
    print(f"[compare] common question_ids: {len(common)} (templated={len(t_em)}, "
          f"canonical_A={len(a_em)})")

    # 4. Overall stats
    t_k = int(t_em.loc[common].sum())
    a_k = int(a_em.loc[common].sum())
    n_total = len(common)
    t_acc = t_k / n_total
    a_acc = a_k / n_total
    t_lo, t_hi = wilson_ci(t_k, n_total)
    a_lo, a_hi = wilson_ci(a_k, n_total)

    # 5. Paired bootstrap delta (templated - canonical)
    diffs = (t_em.loc[common].astype(int) - a_em.loc[common].astype(int)).values
    obs = diffs.mean()
    rng = np.random.default_rng(42)
    B = 10000
    boots = np.empty(B)
    idx = rng.integers(0, len(diffs), size=(B, len(diffs)))
    for i in range(B):
        boots[i] = diffs[idx[i]].mean()
    lo, hi = np.percentile(boots, [2.5, 97.5])

    # 6. Per-tier and per-family deltas
    tier_rows = []
    for tier in [1, 2, 3]:
        qids = a_tier[a_tier == tier].index
        qids_c = qids.intersection(common)
        if len(qids_c) == 0:
            continue
        t_t = int(t_em.loc[qids_c].sum())
        a_t = int(a_em.loc[qids_c].sum())
        n_t = len(qids_c)
        diffs_t = (t_em.loc[qids_c].astype(int) - a_em.loc[qids_c].astype(int)).values
        boots_t = np.empty(B)
        idx_t = rng.integers(0, len(diffs_t), size=(B, len(diffs_t)))
        for i in range(B):
            boots_t[i] = diffs_t[idx_t[i]].mean()
        lo_t, hi_t = np.percentile(boots_t, [2.5, 97.5])
        tier_rows.append({
            "tier": tier,
            "n": n_t,
            "templated_acc": t_t / n_t,
            "canonical_a_acc": a_t / n_t,
            "delta": diffs_t.mean(),
            "ci_lo": lo_t,
            "ci_hi": hi_t,
        })

    fam_rows = []
    for fam in sorted(a_family.dropna().unique()):
        qids = a_family[a_family == fam].index
        qids_c = qids.intersection(common)
        if len(qids_c) == 0:
            continue
        t_f = int(t_em.loc[qids_c].sum())
        a_f = int(a_em.loc[qids_c].sum())
        n_f = len(qids_c)
        diffs_f = (t_em.loc[qids_c].astype(int) - a_em.loc[qids_c].astype(int)).values
        boots_f = np.empty(B)
        idx_f = rng.integers(0, len(diffs_f), size=(B, len(diffs_f)))
        for i in range(B):
            boots_f[i] = diffs_f[idx_f[i]].mean()
        lo_f, hi_f = np.percentile(boots_f, [2.5, 97.5])
        fam_rows.append({
            "family": fam,
            "n": n_f,
            "templated_acc": t_f / n_f,
            "canonical_a_acc": a_f / n_f,
            "delta": diffs_f.mean(),
            "ci_lo": lo_f,
            "ci_hi": hi_f,
        })

    # 7. Decision rule
    if hi <= -0.03:
        outcome = "H2 (templated significantly worse; soften framing)"
    elif lo >= -0.02 and hi <= 0.02:
        outcome = "H1 (templated matches LLM-narrative within +/-2pp)"
    elif lo >= -0.03:
        outcome = "H1-mild (CI straddles zero or only slightly negative; format-level claim holds)"
    else:
        outcome = "H2-mild (CI lower bound between -3pp and -2pp; soften with care)"

    # 8. Write markdown
    lines: list[str] = []
    lines.append("# Templated-Narrative QA Arm: Comparison vs Canonical System A")
    lines.append("")
    lines.append("> Source: `results/scored_templated/scored.csv` and `results/scored.csv` (A only)")
    lines.append(">")
    lines.append("> Addresses reviewer revision #1. The templated-narrative arm runs the same")
    lines.append("> System A pipeline against deterministic templated narratives (no LLM) to")
    lines.append("> disambiguate 'narrative format wins' from 'LLM-generated narratives win.'")
    lines.append("")
    lines.append("## Headline")
    lines.append("")
    lines.append(f"- **Templated A-T accuracy**: {fmt_pct(t_acc)} [{fmt_pct(t_lo)}, {fmt_pct(t_hi)}]")
    lines.append(f"- **Canonical A accuracy**: {fmt_pct(a_acc)} [{fmt_pct(a_lo)}, {fmt_pct(a_hi)}]")
    lines.append(f"- **Paired delta (A-T - A)**: {obs * 100:+.2f}pp 95%CI=[{lo * 100:+.2f}pp, {hi * 100:+.2f}pp]")
    lines.append(f"- **Decision rule outcome**: {outcome}")
    lines.append("")
    lines.append("## Per-tier breakdown")
    lines.append("")
    lines.append("| Tier | n | A-T acc | A acc | Delta | 95% CI |")
    lines.append("|---|---|---|---|---|---|")
    for r in tier_rows:
        lines.append(
            f"| {r['tier']} | {r['n']} | {fmt_pct(r['templated_acc'])} | "
            f"{fmt_pct(r['canonical_a_acc'])} | {r['delta'] * 100:+.2f}pp | "
            f"[{r['ci_lo'] * 100:+.2f}pp, {r['ci_hi'] * 100:+.2f}pp] |"
        )
    lines.append("")
    lines.append("## Per-family breakdown")
    lines.append("")
    lines.append("| Family | n | A-T acc | A acc | Delta | 95% CI |")
    lines.append("|---|---|---|---|---|---|")
    for r in fam_rows:
        lines.append(
            f"| {r['family']} | {r['n']} | {fmt_pct(r['templated_acc'])} | "
            f"{fmt_pct(r['canonical_a_acc'])} | {r['delta'] * 100:+.2f}pp | "
            f"[{r['ci_lo'] * 100:+.2f}pp, {r['ci_hi'] * 100:+.2f}pp] |"
        )
    lines.append("")
    lines.append("## Interpretation rule used")
    lines.append("")
    lines.append("- **H1 (narrative format wins, no LLM-specific advantage):** "
                 "Paired-delta CI straddles zero, or both endpoints within +/-2pp. "
                 "Implication: 'narrative format wins' is supported; LLM-narrative-specific "
                 "lexical regularity is not the driver.")
    lines.append("- **H2 (LLM-narrative specific advantage):** Paired-delta CI lower bound "
                 "below -3pp. Implication: LLM narratives are doing more than the format alone; "
                 "framing should soften to 'LLM-generated narratives win, beyond format.'")
    lines.append("")
    lines.append(f"**This run:** {outcome}")
    lines.append("")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"[compare] wrote {OUT_MD}")
    print(f"[compare] outcome: {outcome}")


if __name__ == "__main__":
    main()
