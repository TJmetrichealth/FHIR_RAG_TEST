"""Revision re-analysis (paper v2).

Computes, from the frozen scored CSVs and without any API calls:
  1. Patient-level cluster bootstrap for every pairwise accuracy difference
     (200 patients resampled with replacement, 10,000 resamples, seed 42),
     alongside the question-level paired bootstrap for comparison.
  2. Accuracy stratified by whether the ground truth is N/A, by tier and family,
     plus the constant "always N/A" predictor and the per-family modal baseline
     with N/A admitted as a candidate label.
  3. Output-budget audit from billed completion tokens (tokens_out >= 512).
  4. Pooled recall@k for B and C with Wilson CIs over all 13,800 questions.
  5. 1024-token sweep deltas split by N/A status.

Inputs (read-only):
  results/scored.csv, results/scored_templated/scored.csv,
  results/scored_noretrieval/scored.csv, results_1024/scored.csv
Output:
  analysis/revision_reanalysis.md

Reproduce: python analysis/run_revision_reanalysis.py
"""
from __future__ import annotations

import contextlib
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import fisher_exact

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / "analysis" / "revision_reanalysis.md"
B = 10_000
SEED = 42
ARMS = ["A", "B", "C", "AT", "N"]
PAIRS = [("A", "B"), ("A", "C"), ("B", "C"), ("AT", "A"), ("A", "N"), ("B", "N"), ("C", "N")]


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - h) / d, (c + h) / d


def load_wide() -> pd.DataFrame:
    main = pd.read_csv(ROOT / "results/scored.csv", low_memory=False)
    tpl = pd.read_csv(ROOT / "results/scored_templated/scored.csv", low_memory=False)
    nr = pd.read_csv(ROOT / "results/scored_noretrieval/scored.csv", low_memory=False)

    def pivot(df: pd.DataFrame, label: str) -> pd.Series:
        return df.set_index("question_id")["exact_match"].astype(int).rename(label)

    wide = pd.concat(
        [
            pivot(main[main.system == "a"], "A"),
            pivot(main[main.system == "b"], "B"),
            pivot(main[main.system == "c"], "C"),
            pivot(tpl, "AT"),
            pivot(nr, "N"),
        ],
        axis=1,
    )
    meta = main[main.system == "a"].set_index("question_id")[
        ["patient_id", "tier", "family", "ground_truth"]
    ]
    wide = wide.join(meta)
    assert wide[ARMS + ["patient_id", "tier", "family"]].isna().sum().sum() == 0
    # pandas reads the literal string "N/A" as NaN by default.
    wide["is_na"] = wide["ground_truth"].isna() | (
        wide["ground_truth"].astype(str).str.strip().str.upper() == "N/A"
    )
    return wide, main


def cluster_boot(sub: pd.DataFrame, rng: np.random.Generator, pairs=PAIRS) -> None:
    per_pat = sub.groupby("patient_id")[ARMS].sum()
    npn = sub.groupby("patient_id").size().values.astype(float)
    M = per_pat.values.astype(float)
    idx = rng.integers(0, M.shape[0], size=(B, M.shape[0]))
    for x, y in pairs:
        xi, yi = ARMS.index(x), ARMS.index(y)
        d = (M[idx, xi].sum(1) - M[idx, yi].sum(1)) / npn[idx].sum(1) * 100
        obs = (M[:, xi].sum() - M[:, yi].sum()) / npn.sum() * 100
        lo, hi = np.percentile(d, [2.5, 97.5])
        print(f"- {x} minus {y}: {obs:+.2f} pp, cluster 95% CI [{lo:+.2f}, {hi:+.2f}] "
              f"({M.shape[0]} patients, {int(npn.sum())} questions)")


def question_boot(sub: pd.DataFrame, rng: np.random.Generator) -> None:
    Q = sub[ARMS].values.astype(float)
    idx = rng.integers(0, Q.shape[0], size=(B, Q.shape[0]))
    for x, y in PAIRS:
        xi, yi = ARMS.index(x), ARMS.index(y)
        d = (Q[idx, xi] - Q[idx, yi]).mean(1) * 100
        obs = (Q[:, xi] - Q[:, yi]).mean() * 100
        print(f"- {x} minus {y}: {obs:+.2f} pp, question-level 95% CI "
              f"[{np.percentile(d, 2.5):+.2f}, {np.percentile(d, 97.5):+.2f}]")


def modal_baseline(sub: pd.DataFrame) -> float:
    hits = 0
    for _, g in sub.groupby("family"):
        hits += g.ground_truth.fillna("N/A").value_counts().iloc[0]
    return hits / len(sub) * 100


def run() -> None:
    rng = np.random.default_rng(SEED)
    wide, main = load_wide()

    print("## 1. Aggregate accuracy (%)\n")
    for a in ARMS:
        k = int(wide[a].sum())
        lo, hi = wilson(k, len(wide))
        print(f"- {a}: {k}/{len(wide)} = {k/len(wide)*100:.2f}% [{lo*100:.1f}, {hi*100:.1f}]")
    k = int(wide.is_na.sum())
    lo, hi = wilson(k, len(wide))
    print(f"- Constant N/A predictor: {k}/{len(wide)} = {k/len(wide)*100:.2f}% [{lo*100:.1f}, {hi*100:.1f}]")

    print("\n## 2. Pairwise differences, all questions\n")
    print("Patient-level cluster bootstrap (primary):\n")
    cluster_boot(wide, rng)
    print("\nQuestion-level paired bootstrap (previous version):\n")
    question_boot(wide, rng)

    print("\n## 3. Per-tier cluster bootstrap\n")
    for t in [1, 2, 3]:
        print(f"\nTier {t}:\n")
        cluster_boot(wide[wide.tier == t], rng, pairs=[("A", "B"), ("A", "C"), ("B", "C"), ("AT", "A")])

    print("\n## 4. Per-family cluster bootstrap, A-T minus A\n")
    for fam, sub in wide.groupby("family"):
        print(f"\n{fam}:\n")
        cluster_boot(sub, rng, pairs=[("AT", "A")])

    print("\n## 5. N/A prevalence by tier\n")
    print(wide.groupby("tier")["is_na"].agg(["sum", "size", "mean"]).to_markdown())
    print(f"\nOverall N/A share: {wide.is_na.mean()*100:.2f}%")

    print("\n## 6. Accuracy by tier x N/A status (%)\n")
    tab = wide.groupby(["tier", "is_na"])[ARMS].mean() * 100
    cnt = wide.groupby(["tier", "is_na"]).size().rename("n")
    print(pd.concat([cnt, tab.round(1)], axis=1).to_markdown())
    print("\nOverall, substantive only (%):")
    print((wide[~wide.is_na][ARMS].mean() * 100).round(2).to_markdown())
    print("\nOverall, N/A only (%):")
    print((wide[wide.is_na][ARMS].mean() * 100).round(2).to_markdown())

    print("\n## 7. Accuracy by family x N/A status (%)\n")
    tab = wide.groupby(["family", "is_na"])[ARMS].mean() * 100
    cnt = wide.groupby(["family", "is_na"]).size().rename("n")
    print(pd.concat([cnt, tab.round(1)], axis=1).to_markdown())

    print("\n## 8. Share of each arm's correct answers that are N/A-truth questions\n")
    for t in [1, 2, 3]:
        for a in ["A", "B", "C", "N"]:
            corr = wide[(wide.tier == t) & (wide[a] == 1)]
            print(f"- Tier {t} {a}: {corr.is_na.mean()*100:.1f}% (n correct = {len(corr)})")

    print("\n## 9. Per-family modal baseline (N/A admitted as a label)\n")
    for t in [1, 2, 3]:
        sub = wide[wide.tier == t]
        print(f"- Tier {t}: all questions {modal_baseline(sub):.1f}%; "
              f"substantive only {modal_baseline(sub[~sub.is_na]):.1f}%")

    print("\n## 10. Cluster bootstrap, substantive questions only\n")
    cluster_boot(wide[~wide.is_na], rng)
    print("\n## 11. Cluster bootstrap, N/A questions only\n")
    cluster_boot(wide[wide.is_na], rng)

    print("\n## 12. Output-budget audit (billed tokens_out >= 512)\n")
    for s in ["a", "b", "c"]:
        sub = main[main.system == s]
        by_tier = (sub.groupby("tier").tokens_out.apply(lambda x: (x >= 512).mean() * 100)).round(1).to_dict()
        print(f"- {s}: {(sub.tokens_out >= 512).mean()*100:.1f}% overall; by tier {by_tier}")
    tpl = pd.read_csv(ROOT / "results/scored_templated/scored.csv", low_memory=False)
    nr = pd.read_csv(ROOT / "results/scored_noretrieval/scored.csv", low_memory=False)
    print(f"- templated: {(tpl.tokens_out >= 512).mean()*100:.1f}%")
    print(f"- no-retrieval: {(nr.tokens_out >= 512).mean()*100:.1f}%")
    print("\nPrompt tokens (billed):\n")
    print(main.groupby("system").tokens_in.describe().round(0).to_markdown())

    print("\n## 13. Pooled recall@k (Wilson CI over 13,800 questions)\n")
    for s in ["b", "c"]:
        g = main[main.system == s]
        for k in [1, 3, 5]:
            r = g[f"recall_at_{k}"].map(lambda v: str(v).lower() == "true")
            lo, hi = wilson(int(r.sum()), len(r))
            print(f"- {s} recall@{k}: {r.mean():.3f} [{lo:.3f}, {hi:.3f}]")
        print(f"- {s} recall@10 identical to recall@5: "
              f"{(g.recall_at_10.astype(str) == g.recall_at_5.astype(str)).all()}")

    print("\n## 14. 1024-token sweep split by N/A status\n")
    s1 = pd.read_csv(ROOT / "results_1024/scored.csv", low_memory=False)
    ids = set(s1.question_id)
    s5 = main[main.question_id.isin(ids)]
    for sy in ["a", "b", "c"]:
        x5 = s5[s5.system == sy].set_index("question_id").exact_match.rename("t512")
        x1 = s1[s1.system == sy].set_index("question_id").exact_match.rename("t1024")
        na = wide.loc[x5.index, "is_na"]
        j = pd.concat([x5, x1, na], axis=1).dropna()
        for flag, g in j.groupby("is_na"):
            print(f"- {sy} {'N/A' if flag else 'substantive'} (n={len(g)}): "
                  f"{g.t512.mean()*100:.1f}% -> {g.t1024.mean()*100:.1f}% "
                  f"(delta {(g.t1024.mean()-g.t512.mean())*100:+.1f} pp)")

    print("\n## 15. Fisher exact tests on the earlier 50-failure taxonomy counts\n")
    print(f"- temporal-anchor 15/50 (A) vs 9/50 (B): p = {fisher_exact([[15, 35], [9, 41]])[1]:.3f}")
    print(f"- temporal-anchor 15/50 (A) vs 5/50 (C): p = {fisher_exact([[15, 35], [5, 45]])[1]:.3f}")

    post_path = ROOT / "results/scored_postthink/scored.csv"
    if not post_path.exists():
        print("\n## 16. Post-think scoring: results/scored_postthink/scored.csv not found; "
              "run analysis/run_postthink_rescore.py first\n")
        return
    print("\n## 16. Post-think scoring (final answer only), N/A-stratified\n")
    post = pd.read_csv(post_path, low_memory=False)
    name_map = {"a": "A", "b": "B", "c": "C", "at": "AT", "n": "N"}
    pw = pd.concat(
        [post[post.system == s].set_index("question_id")["exact_match"].astype(int).rename(name_map[s])
         for s in name_map],
        axis=1,
    ).join(wide[["patient_id", "tier", "family", "is_na"]])
    assert pw[ARMS].isna().sum().sum() == 0
    print("Accuracy (%) by tier x N/A status:\n")
    tab = pw.groupby(["tier", "is_na"])[ARMS].mean() * 100
    cnt = pw.groupby(["tier", "is_na"]).size().rename("n")
    print(pd.concat([cnt, tab.round(1)], axis=1).to_markdown())
    print("\nOverall (%):")
    print((pw[ARMS].mean() * 100).round(2).to_markdown())
    print("\nSubstantive only (%):")
    print((pw[~pw.is_na][ARMS].mean() * 100).round(2).to_markdown())
    print("\nN/A only (%):")
    print((pw[pw.is_na][ARMS].mean() * 100).round(2).to_markdown())
    print("\nCluster bootstrap, all questions, post-think scoring:\n")
    cluster_boot(pw, rng)
    print("\nCluster bootstrap, substantive only, post-think scoring:\n")
    cluster_boot(pw[~pw.is_na], rng)
    print("\nCluster bootstrap, N/A only, post-think scoring:\n")
    cluster_boot(pw[pw.is_na], rng)
    print("\nPer-family substantive accuracy (%), post-think scoring:\n")
    tab = pw[~pw.is_na].groupby("family")[ARMS].mean() * 100
    cnt = pw[~pw.is_na].groupby("family").size().rename("n")
    print(pd.concat([cnt, tab.round(1)], axis=1).to_markdown())
    print("\nPer-tier modal baseline on substantive questions vs post-think accuracy:\n")
    for t in [1, 2, 3]:
        sub = pw[(pw.tier == t) & (~pw.is_na)]
        gt = wide.loc[sub.index]
        print(f"- Tier {t}: modal {modal_baseline(gt):.1f}%; "
              + "; ".join(f"{a} {sub[a].mean()*100:.1f}%" for a in ARMS))


def main() -> None:
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_MD, "w", encoding="utf-8") as fh, contextlib.redirect_stdout(fh):
        print("# Revision re-analysis (paper v2)\n")
        print("> Reproduce: `python analysis/run_revision_reanalysis.py`\n")
        run()
    print(f"wrote {OUT_MD}")


if __name__ == "__main__":
    main()
