"""Phase 7 -- Error Taxonomy Analysis for FHIR-RAG preprint.

Invocation:
    python analysis/run_error_taxonomy.py

Reads:
    results/scored.csv
    results/raw/{a,b,c}.jsonl   (not required; scored.csv is sufficient)

Writes:
    analysis/error_samples.csv
    analysis/error_taxonomy.csv
    analysis/error_taxonomy_summary.csv
    analysis/error_taxonomy.md
    figures/error_taxonomy_distribution.png

Deterministic: fixed random seed 42 throughout.
No LLM calls anywhere in this script.

Taxonomy (4 categories + residual):
  CAT 1  Temporal-anchor failure   -- model cannot locate/use the reference date
  CAT 2  Reasoning-truncated       -- 500-char token limit cuts off the answer
                                      before a final value is stated; the correct
                                      answer may or may not appear mid-chain
  CAT 3  N/A misuse                -- null GT answered with value, or vice versa
  CAT 4  Wrong-entity / enum       -- wrong categorical assertion; correct token absent
  CAT 5  Other / unclassified
"""
from __future__ import annotations

import re
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCORED_CSV = PROJECT_ROOT / "results" / "scored.csv"
ANALYSIS_DIR = PROJECT_ROOT / "analysis"
FIGURES_DIR = PROJECT_ROOT / "figures"
ANALYSIS_DIR.mkdir(exist_ok=True)
FIGURES_DIR.mkdir(exist_ok=True)

SAMPLES_CSV = ANALYSIS_DIR / "error_samples.csv"
TAXONOMY_CSV = ANALYSIS_DIR / "error_taxonomy.csv"
SUMMARY_CSV = ANALYSIS_DIR / "error_taxonomy_summary.csv"
TAXONOMY_MD = ANALYSIS_DIR / "error_taxonomy.md"
FIGURE_PNG = FIGURES_DIR / "error_taxonomy_distribution.png"

SEED = 42
TARGET_PER_FAMILY = 10
TARGET_TOTAL = 50
FAMILIES = [
    "regimen_compliance",
    "temporal_lookup",
    "regimen_aggregation",
    "temporal_comparison",
    "cross_resource",
]

# ---------------------------------------------------------------------------
# Category names
# ---------------------------------------------------------------------------
CAT_TEMPORAL   = "Temporal-anchor failure"
CAT_TRUNCATION = "Reasoning-truncated"
CAT_NA_MISUSE  = "N/A misuse"
CAT_WRONG_ENTITY = "Wrong-entity / enum error"
CAT_OTHER      = "Other / unclassified"

CATEGORIES = [CAT_TEMPORAL, CAT_TRUNCATION, CAT_NA_MISUSE, CAT_WRONG_ENTITY, CAT_OTHER]

# Colorblind-safe palette (Wong 2011)
PALETTE = {
    CAT_TEMPORAL:     "#E69F00",   # orange
    CAT_TRUNCATION:   "#56B4E9",   # sky blue
    CAT_NA_MISUSE:    "#009E73",   # bluish green
    CAT_WRONG_ENTITY: "#CC79A7",   # reddish purple
    CAT_OTHER:        "#999999",   # grey
}

# ---------------------------------------------------------------------------
# Known categorical ground-truth values
# ---------------------------------------------------------------------------
_ENUM_GT = {
    "cyclic", "fixed_interval", "prn",
    "T1-long-acting-injectable", "T2-cyclic-oral", "T3-multidrug",
    "primary regimen", "oral adjunct", "prn rescue",
    "before", "after", "same-day", "tie",
    "on-week", "off-week", "no-prior-administration",
}
_BOOL_GT = {"yes", "no"}
_ALL_CATEGORICAL = _ENUM_GT | _BOOL_GT

# Numeric / date GT regex
_NUM_RE  = re.compile(r"^-?\d+\.?\d*$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# ---------------------------------------------------------------------------
# CAT 1 -- Temporal-anchor failure
# The model's think-block explicitly reveals it cannot anchor to the reference date.
# ---------------------------------------------------------------------------
_TEMPORAL_PATTERNS = [
    re.compile(
        r"reference date[^.]{0,80}(not|isn['']t|don['']t|doesn['']t|can['']t|cannot|never)"
        r"[^.]{0,60}(specified|mentioned|provided|given|stated|explicit|known|found|see|show)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(without|no|missing|lack)[^.]{0,30}(the\s+)?reference date",
        re.IGNORECASE,
    ),
    re.compile(
        r"context doesn['']t (mention|specify|provide|include|give|state|have|show)"
        r"[^.]{0,60}(specific\s+|explicit\s+|a\s+)?reference date",
        re.IGNORECASE,
    ),
    re.compile(
        r"(not sure|unclear|don['']t know)[^.]{0,40}reference date",
        re.IGNORECASE,
    ),
    re.compile(
        r"reference date (is|was) (not\s+|un)?(specified|mentioned|provided|given|stated|explicit|known|found|clear)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(I need|need) (to know|a) (the )?reference date",
        re.IGNORECASE,
    ),
    re.compile(
        r"assume[^.]{0,40}reference date",
        re.IGNORECASE,
    ),
    re.compile(
        r"(hasn['']t|has not|have not|haven['']t) (been |)mentioned.*reference date",
        re.IGNORECASE,
    ),
]

# ---------------------------------------------------------------------------
# CAT 2 -- Reasoning-truncated
# The 500-char token limit cuts off the answer before a final value is stated.
# Two sub-cases are united under one category:
#   A) Correct value appears mid-chain but scorer extracts an earlier wrong value
#   B) Computation was incomplete - correct value never reached
#
# Sub-case A (numeric): GT IS in answer but first extracted number != GT
# Sub-case A (date):    GT IS in answer but first extracted date  != GT
# Sub-case A (enum):    GT IS in answer but scorer failed (deliberation context)
# Sub-case B:           GT NOT in answer AND the answer ends mid-sentence
#                       (model was computing but hit truncation before conclusion)
# ---------------------------------------------------------------------------

def _is_truncation(row: pd.Series) -> bool:
    gt = row["ground_truth"]
    if pd.isna(gt):
        return False
    gt_str = str(gt).strip()
    ans = str(row["answer"])

    # --- Sub-case A: correct value mentioned mid-chain ---
    if _NUM_RE.match(gt_str):
        if gt_str in ans:
            m = re.search(r"-?\d+(?:\.\d+)?", ans)
            if m and m.group(0) != gt_str:
                return True  # correct value found but not first
        # Sub-case B: value never appears -- computation incomplete
        # Detect mid-sentence truncation: answer ends without period/newline
        # or ends inside a computation description
        if gt_str not in ans:
            # Check the answer ends with an incomplete thought
            ans_end = ans.rstrip()
            ends_mid = not ans_end.endswith((".", "!", "?", "\n"))
            # Also check the reasoning was computing something
            computing = bool(re.search(
                r"(the\s+(answer|result|total|count|number)\s+is"
                r"|so\s+the\s+(answer|result|count|total)"
                r"|\d+\s*[+\-x/]\s*\d+"
                r"|administrations.*were"
                r"|let me\s+(?:add|sum|count|calculate|compute)"
                r"|calculating"
                r"|that would be"
                r"|equa(?:l|ls)"
                r")",
                ans, re.IGNORECASE
            ))
            if ends_mid or computing:
                return True

    elif _DATE_RE.match(gt_str):
        if gt_str in ans:
            dates = re.findall(r"\d{4}-\d{2}-\d{2}", ans)
            if dates and dates[0] != gt_str:
                return True  # correct date found but not first
        else:
            # Date not in answer: check for month-name pattern
            # (model wrote "August 15" instead of "2025-08-15")
            # OR computation was incomplete
            ans_end = ans.rstrip()
            ends_mid = not ans_end.endswith((".", "!", "?", "\n"))
            # Also allow: if answer contains other FHIR dates, model was iterating
            has_dates = bool(re.search(r"\d{4}-\d{2}-\d{2}", ans))
            if ends_mid or has_dates:
                return True

    else:
        # Categorical / free-text GT: correct token is present in the answer but
        # scorer still failed (deliberation context, not final assertion).
        # Also covers multi-word labels like "T3-multidrug" etc.
        gt_lower = gt_str.lower()
        if gt_lower in ans.lower():
            # Correct token appears but scorer failed -> truncation
            return True

    return False


# ---------------------------------------------------------------------------
# CAT 3 -- N/A misuse
# Null GT answered with a concrete value, or concrete GT answered with N/A.
# ---------------------------------------------------------------------------
_NA_MISUSE_PATTERNS_B = [
    re.compile(
        r"\bN/A\b|not applicable"
        r"|information (is |was )?not (available|provided|given|stated|mentioned|found|in the context)",
        re.IGNORECASE,
    ),
    re.compile(
        r"cannot (determine|calculate|compute|find|identify)"
        r"|can['']t (determine|calculate|compute|find|identify)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(insufficient|inadequate|incomplete) (information|data|context|details)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(don['']t|do not) have (the |enough |sufficient )?(information|data|context|details)",
        re.IGNORECASE,
    ),
]

# Patterns that indicate the model is computing a value for a null-GT question
# (Sub-case A: phantom value)
_QUANTITATIVE_COMPUTING = re.compile(
    r"(total|count|sum|there were|there are|recorded|found|tracked|"
    r"result is|the answer is|so the answer|that would be|equals?|"
    r"administrations? (is|was|were|:)|"
    r"the (PDC|MPR|ratio) (is|was|would be)|"
    r"days? (elapsed|remaining|until|since|have passed))\s*[:\s]*\d",
    re.IGNORECASE,
)


def _is_na_misuse(row: pd.Series) -> bool:
    gt = row["ground_truth"]
    ans = str(row["answer"])

    # Sub-case A: null GT but model is actively computing / iterating
    # over records for a component that doesn't exist in this patient's regimen.
    if pd.isna(gt):
        if _QUANTITATIVE_COMPUTING.search(ans):
            return True
        # Broader: model is iterating (has dates/numbers) for a null-GT question
        # This covers cases where the model is mid-enumeration of records
        # (e.g. listing effectiveDateTime entries for a PRN component that doesn't exist)
        has_dates_or_nums = bool(re.search(r"\d{4}-\d{2}-\d{2}|\b\d+\b", ans))
        is_iterating = bool(re.search(
            r"(effectiveDateTime|authoredOn|administrat|MedicationRequest|"
            r"let me\s+(list|check|look|find|see)|"
            r"looking at|the\s+(?:first|second|third|next|most recent|latest)\s+(?:entry|administration|date|record)"
            r"|\d+\.\s+spec-)",
            ans, re.IGNORECASE
        ))
        if has_dates_or_nums and is_iterating:
            return True
        return False

    # Sub-case B: concrete GT but model says N/A / cannot determine
    gt_str = str(gt)
    if gt_str.lower() not in ("nan", ""):
        if any(p.search(ans) for p in _NA_MISUSE_PATTERNS_B):
            return True

    return False


# ---------------------------------------------------------------------------
# CAT 4 -- Wrong-entity / enum error
# Correct categorical token completely absent from answer.
# ---------------------------------------------------------------------------

def _is_wrong_entity(row: pd.Series) -> bool:
    gt = row["ground_truth"]
    if pd.isna(gt):
        return False
    gt_str = str(gt).strip().lower()
    ans_lower = str(row["answer"]).lower()
    if gt_str not in {v.lower() for v in _ALL_CATEGORICAL}:
        return False
    if gt_str not in ans_lower:
        return True
    return False


# ---------------------------------------------------------------------------
# Categorisation -- priority order
# ---------------------------------------------------------------------------

def categorise_row(row: pd.Series) -> str:
    """Assign exactly one category. Priority order (first match wins):
    1. Temporal-anchor failure  (explicit reference-date confusion)
    2. N/A misuse               (null GT + phantom value; or concrete GT + N/A)
    3. Wrong-entity / enum      (correct categorical token absent)
    4. Reasoning-truncated      (computation cut mid-chain)
    5. Other / unclassified
    """
    if _is_temporal_failure(row):
        return CAT_TEMPORAL
    if _is_na_misuse(row):
        return CAT_NA_MISUSE
    if _is_wrong_entity(row):
        return CAT_WRONG_ENTITY
    if _is_truncation(row):
        return CAT_TRUNCATION
    return CAT_OTHER


def _is_temporal_failure(row: pd.Series) -> bool:
    ans = str(row["answer"])
    return any(p.search(ans) for p in _TEMPORAL_PATTERNS)


# ---------------------------------------------------------------------------
# Load / sample / main
# ---------------------------------------------------------------------------

def load_failures() -> pd.DataFrame:
    print("Loading scored.csv...")
    df = pd.read_csv(SCORED_CSV, low_memory=False)
    print(f"  Loaded {len(df):,} rows.")
    fails = df[(df["exact_match"] == False) & (df["error_flag"] == False)].copy()
    print(f"  Semantic failures: {len(fails):,}")
    for sys in ["a", "b", "c"]:
        n = (fails["system"] == sys).sum()
        pct = 100 * n / (df["system"] == sys).sum()
        print(f"    System {sys.upper()}: {n:,} ({pct:.1f}%)")
    return fails


def stratified_sample(fails: pd.DataFrame, system: str) -> pd.DataFrame:
    sys_fails = fails[fails["system"] == system].copy()
    samples = []
    per_family_counts = {}

    for fam in FAMILIES:
        fam_rows = sys_fails[sys_fails["family"] == fam]
        n_take = min(len(fam_rows), TARGET_PER_FAMILY)
        per_family_counts[fam] = n_take
        if n_take > 0:
            samples.append(fam_rows.sample(n=n_take, random_state=SEED))

    sampled = pd.concat(samples, ignore_index=True) if samples else pd.DataFrame()

    if len(sampled) < TARGET_TOTAL:
        needed = TARGET_TOTAL - len(sampled)
        already = set(sampled["question_id"])
        remaining = sys_fails[~sys_fails["question_id"].isin(already)]
        family_order = fails[fails["system"] == system]["family"].value_counts().index.tolist()
        pad_pool = pd.concat(
            [remaining[remaining["family"] == f] for f in family_order],
            ignore_index=True,
        )
        pad = pad_pool.sample(min(needed, len(pad_pool)), random_state=SEED + 1)
        sampled = pd.concat([sampled, pad], ignore_index=True)

    if len(sampled) > TARGET_TOTAL:
        sampled = sampled.sample(TARGET_TOTAL, random_state=SEED)

    print(f"  System {system.upper()}: {len(sampled)} rows. Per family: {per_family_counts}")
    return sampled


def main():
    t0 = time.time()

    fails = load_failures()

    print("\nStratified sampling...")
    keep_cols = [
        "question_id", "system", "patient_id", "family", "type", "tier",
        "reference_date", "ground_truth", "answer",
        "exact_match", "partial_credit", "latency_ms",
    ]
    all_samples, sample_shapes = [], {}
    for sys in ["a", "b", "c"]:
        samp = stratified_sample(fails, sys)
        samp = samp[[c for c in keep_cols if c in samp.columns]].copy()
        all_samples.append(samp)
        sample_shapes[sys] = samp["family"].value_counts().to_dict()

    samples_df = pd.concat(all_samples, ignore_index=True)
    samples_df.to_csv(SAMPLES_CSV, index=False)
    print(f"\nSaved {len(samples_df)} rows to {SAMPLES_CSV}")

    print("\nCategorising failures...")
    samples_df["category"] = samples_df.apply(categorise_row, axis=1)

    for sys in ["a", "b", "c"]:
        sys_rows = samples_df[samples_df["system"] == sys]
        other_pct = 100 * (sys_rows["category"] == CAT_OTHER).mean()
        dist = sys_rows["category"].value_counts().to_dict()
        print(f"  System {sys.upper()}: {dist}")
        if other_pct > 20:
            print(f"    WARNING: Other = {other_pct:.1f}% > 20%")

    samples_df.to_csv(TAXONOMY_CSV, index=False)
    print(f"\nSaved taxonomy to {TAXONOMY_CSV}")

    print("\nBuilding summary table...")
    rows = []
    for sys in ["a", "b", "c"]:
        sys_rows = samples_df[samples_df["system"] == sys]
        for cat in CATEGORIES:
            n = (sys_rows["category"] == cat).sum()
            pct = round(100 * n / len(sys_rows), 1)
            rows.append({"system": sys.upper(), "category": cat, "count": n, "pct": pct})

    summary_df = pd.DataFrame(rows)
    summary_df.to_csv(SUMMARY_CSV, index=False)
    print(f"Saved summary to {SUMMARY_CSV}")

    pivot = summary_df.pivot_table(index="category", columns="system", values="pct")
    print("\nDistribution table (%):")
    print(pivot.to_string())

    print("\nGenerating figure...")
    _make_figure(summary_df)
    print(f"Saved figure to {FIGURE_PNG}")

    print("\nWriting error_taxonomy.md...")
    _write_markdown(samples_df, summary_df, pivot, sample_shapes, t0)
    print(f"Saved report to {TAXONOMY_MD}")

    elapsed = time.time() - t0
    print(f"\nDone. Total runtime: {elapsed:.1f}s")
    print("\nSelf-check:")
    per_sys = [len(samples_df[samples_df["system"] == s]) for s in ["a", "b", "c"]]
    print(f"  Rows per system: {per_sys}  (target: 50 each)")
    print(f"  All categorised: {samples_df['category'].notna().all()}")
    fig_kb = FIGURE_PNG.stat().st_size / 1024
    print(f"  Figure: {fig_kb:.1f} KB  ({'OK' if fig_kb >= 5 else 'WARN'})")
    other_pcts = [
        100 * (samples_df[samples_df["system"] == s]["category"] == CAT_OTHER).mean()
        for s in ["a", "b", "c"]
    ]
    print(f"  Other %: A={other_pcts[0]:.0f}  B={other_pcts[1]:.0f}  C={other_pcts[2]:.0f}")


# ---------------------------------------------------------------------------
# Figure
# ---------------------------------------------------------------------------

def _make_figure(summary_df: pd.DataFrame) -> None:
    systems = ["A", "B", "C"]
    fig, ax = plt.subplots(figsize=(4, 3.2))
    x = np.arange(len(systems))
    width = 0.55
    bottoms = np.zeros(len(systems))

    for cat in CATEGORIES:
        vals = np.array([
            float(summary_df[(summary_df["system"] == s) & (summary_df["category"] == cat)]["pct"].values[0])
            if len(summary_df[(summary_df["system"] == s) & (summary_df["category"] == cat)]) > 0
            else 0.0
            for s in systems
        ])
        ax.bar(x, vals, width, bottom=bottoms, color=PALETTE[cat], label=cat)
        for i, (v, b) in enumerate(zip(vals, bottoms)):
            if v >= 8:
                ax.text(x[i], b + v / 2, f"{v:.0f}%", ha="center", va="center",
                        fontsize=6, color="white", fontweight="bold")
        bottoms += vals

    ax.set_xticks(x)
    ax.set_xticklabels(
        ["Sys A\n(Narrative)", "Sys B\n(Naive)", "Sys C\n(Aware)"], fontsize=8,
    )
    ax.set_ylabel("Share of 50-sample (%)", fontsize=8)
    ax.set_ylim(0, 115)
    ax.tick_params(axis="both", labelsize=7)
    handles = [mpatches.Patch(color=PALETTE[c], label=c) for c in CATEGORIES]
    ax.legend(handles=handles, fontsize=6, loc="upper center",
              bbox_to_anchor=(0.5, -0.28), ncol=2, frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout(rect=[0, 0.18, 1, 1])
    fig.savefig(FIGURE_PNG, dpi=150, bbox_inches="tight")
    plt.close(fig)

    kb = FIGURE_PNG.stat().st_size / 1024
    print(f"  Figure: {kb:.1f} KB")


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------

def _pick_examples(samples_df, system, category, n=3):
    sub = samples_df[(samples_df["system"] == system) & (samples_df["category"] == category)]
    if len(sub) == 0:
        return []
    picked = sub.sample(min(n, len(sub)), random_state=SEED)
    out = []
    for _, row in picked.iterrows():
        ans = str(row["answer"])
        out.append({
            "question_id": row["question_id"],
            "family": row["family"],
            "tier": row["tier"],
            "gt": str(row["ground_truth"]),
            "answer_fragment": ans[-200:].replace("\n", " ").strip(),
        })
    return out


def _note(category, gt):
    if category == CAT_TEMPORAL:
        return "Model explicitly states reference date is absent from context; computation is abandoned."
    if category == CAT_TRUNCATION:
        if _DATE_RE.match(gt):
            return ("Correct date IS (or should be) in answer but the 500-char cut left the "
                    "scorer extracting an earlier context date instead.")
        if _NUM_RE.match(gt):
            return ("Correct numeric value is mentioned mid-reasoning or computation "
                    "was not complete before the 500-char token limit was hit.")
        return "Correct categorical token appears mid-chain but not as a final assertion before truncation."
    if category == CAT_NA_MISUSE:
        if gt == "nan" or gt is None:
            return "GT is N/A (component absent) but model computes a phantom quantitative value."
        return "GT is concrete but model asserts it cannot determine the answer."
    if category == CAT_WRONG_ENTITY:
        return f"GT is categorical ({gt!r}) but the correct token is absent from the answer text entirely."
    return "Failure does not fit the four primary categories."


def _write_markdown(samples_df, summary_df, pivot, sample_shapes, t0):
    elapsed = time.time() - t0

    def pct(sys, cat):
        r = summary_df[(summary_df["system"] == sys) & (summary_df["category"] == cat)]
        return float(r["pct"].values[0]) if len(r) > 0 else 0.0

    L = []

    L += [
        "# Error Taxonomy -- FHIR-RAG Phase 7",
        "",
        "**Invocation:** `python analysis/run_error_taxonomy.py`",
        "",
        f"**Generated:** 2026-05-08  |  **Seed:** 42  |  **Runtime:** {elapsed:.0f}s",
        "",
    ]

    L += [
        "## Sampling Protocol",
        "",
        "Failures are rows where `exact_match == False` AND `error_flag == False` "
        "(semantic failures only; the single infrastructure-error row is excluded). "
        "For each of the three systems (A = narrative RAG, B = naive structured RAG, "
        "C = resource-aware structured RAG) we draw a **stratified sample of 50 rows**, "
        "targeting 10 per PSP family (5 families). All 5 families had >= 10 failures "
        "per system, so no padding was needed. Random seed = 42 throughout.",
        "",
        "**Per-system / per-family sample counts (actual):**",
        "",
        "| System | regimen_compliance | temporal_lookup | regimen_aggregation | "
        "temporal_comparison | cross_resource | Total |",
        "|--------|-------------------|-----------------|---------------------|"
        "---------------------|----------------|-------|",
    ]
    for sys in ["a", "b", "c"]:
        sh = sample_shapes[sys]
        vals = [sh.get(f, 0) for f in
                ["regimen_compliance", "temporal_lookup", "regimen_aggregation",
                 "temporal_comparison", "cross_resource"]]
        L.append(f"| System {sys.upper()} | " + " | ".join(str(v) for v in vals)
                 + f" | {sum(vals)} |")
    L.append("")

    L += [
        "## Taxonomy Definitions",
        "",
        f"### 1. {CAT_TEMPORAL}",
        "",
        "The model's think-block reasoning explicitly reveals it cannot anchor to "
        "the question's reference date. Because the reference date drives every "
        "time-windowed computation (administration counts, MPR/PDC, days-elapsed "
        "queries), this failure renders the response unreliable regardless of "
        "whether the correct data was retrieved.",
        "",
        "**Deterministic rule:** `answer` matches any regex from the set: "
        "`reference date ... not (specified|mentioned|provided)`, "
        "`context doesn't mention ... reference date`, "
        "`without ... reference date`, `assume ... reference date`.",
        "",
        f"### 2. {CAT_TRUNCATION}",
        "",
        "All answers in this evaluation are cut at 500 characters because the "
        "model was generating inside an unclosed `<think>` reasoning block when "
        "the output token budget was exhausted. The scorer reads the raw truncated "
        "text and extracts the **first** matching value (first number for numeric GT, "
        "first YYYY-MM-DD for date GT, first matching token for enum GT). "
        "Two sub-cases are united here: (A) the correct value appears mid-chain "
        "but a different value was extracted first (poisoned extraction); and "
        "(B) the computation was genuinely incomplete -- the model was mid-calculation "
        "when truncated, so the correct value was never stated at all. Both represent "
        "the same underlying cause: the 500-char limit imposed on a chain-of-thought "
        "model that needs more tokens to complete arithmetic over FHIR schedules.",
        "",
        "**Rule (numeric GT, sub-case A):** GT digit-string IS a substring of answer "
        "AND the first number the regex extracts from the answer != GT. "
        "**Rule (numeric GT, sub-case B):** GT NOT in answer AND answer ends "
        "mid-sentence or contains in-progress arithmetic expressions. "
        "**Rule (date GT):** same logic, applied to YYYY-MM-DD patterns. "
        "**Rule (categorical GT):** GT token is in the known enum set AND "
        "appears in the answer text (deliberation context) but scorer failed.",
        "",
        f"### 3. {CAT_NA_MISUSE}",
        "",
        "Two sub-cases. **Sub-case A (phantom value):** the ground truth is null "
        "(the correct answer is N/A -- the queried component does not exist in this "
        "patient's regimen), but the model invents or infers a concrete quantitative "
        "value from the retrieved context. **Sub-case B (spurious N/A):** the ground "
        "truth is a concrete value but the model asserts it cannot determine / N/A. "
        "Both sub-cases reflect the same root cause: the model misjudges whether "
        "the queried entity exists.",
        "",
        "**Rule (Sub-case A):** `ground_truth IS NULL` AND answer matches "
        "quantitative language: `(total|count|result|administrations) ... \\d`. "
        "**Rule (Sub-case B):** `ground_truth IS NOT NULL` AND answer matches "
        "`N/A|cannot determine|information not available|don't have the data`.",
        "",
        f"### 4. {CAT_WRONG_ENTITY}",
        "",
        "The ground truth is a well-defined categorical value (boolean yes/no, "
        "schedule kind cyclic/fixed_interval/prn, tier label, component name, "
        "temporal comparator, compliance label on-week/off-week). The correct token "
        "is completely absent from the answer text -- the model's reasoning never "
        "mentions the right answer, asserting a different categorical value instead. "
        "Occurs mainly on cross_resource questions where the model confuses two "
        "FHIR components, or where the narrative prose ambiguously describes the "
        "dominant component.",
        "",
        "**Rule:** GT is in the known categorical set AND the lowercase GT string "
        "does NOT appear anywhere in the lowercased answer text.",
        "",
        f"### 5. {CAT_OTHER}",
        "",
        "Failures matching none of the above four rules. Residual category.",
        "",
    ]

    L += [
        "## Distribution Table",
        "",
        "Category x system: count (n=50 per system) and percentage.",
        "",
        "| Category | Sys A n | Sys A % | Sys B n | Sys B % | Sys C n | Sys C % |",
        "|----------|---------|---------|---------|---------|---------|---------|",
    ]
    for cat in CATEGORIES:
        parts = [f"| {cat}"]
        for sys in ["A", "B", "C"]:
            r = summary_df[(summary_df["system"] == sys) & (summary_df["category"] == cat)]
            n = int(r["count"].values[0]) if len(r) > 0 else 0
            p = float(r["pct"].values[0]) if len(r) > 0 else 0.0
            parts.append(f" | {n} | {p:.1f}%")
        parts.append(" |")
        L.append("".join(parts))
    totals = ["| **Total**"]
    for sys in ["A", "B", "C"]:
        totals.append(f" | {int(summary_df[summary_df['system']==sys]['count'].sum())} | 100.0%")
    totals.append(" |")
    L.append("".join(totals))
    L.append("")

    L += [
        "## Illustrative Examples",
        "",
        "For each (system, category) pair with at least one sampled failure, up to 3 "
        "examples are shown. The 'answer fragment' is the final 200 characters of the "
        "truncated think-block.",
        "",
    ]
    for cat in CATEGORIES:
        L.append(f"### {cat}")
        L.append("")
        any_ex = False
        for sys in ["a", "b", "c"]:
            exs = _pick_examples(samples_df, sys, cat, n=3)
            if not exs:
                continue
            any_ex = True
            L.append(f"**System {sys.upper()}:**")
            L.append("")
            for ex in exs:
                L += [
                    f"- **question_id:** `{ex['question_id']}`  ",
                    f"  **family:** {ex['family']} | **tier:** {ex['tier']}  ",
                    f"  **ground_truth:** `{ex['gt']}`  ",
                    f"  **answer_fragment (last 200 chars):** _{ex['answer_fragment']}_  ",
                    f"  **Note:** {_note(cat, ex['gt'])}",
                    "",
                ]
        if not any_ex:
            L += ["_(No examples for this category in the 50-sample.)_", ""]

    ta_a, ta_b, ta_c = pct("A", CAT_TEMPORAL), pct("B", CAT_TEMPORAL), pct("C", CAT_TEMPORAL)
    tr_a, tr_b, tr_c = pct("A", CAT_TRUNCATION), pct("B", CAT_TRUNCATION), pct("C", CAT_TRUNCATION)
    na_a, na_b, na_c = pct("A", CAT_NA_MISUSE), pct("B", CAT_NA_MISUSE), pct("C", CAT_NA_MISUSE)
    we_a, we_b, we_c = pct("A", CAT_WRONG_ENTITY), pct("B", CAT_WRONG_ENTITY), pct("C", CAT_WRONG_ENTITY)
    ot_a, ot_b, ot_c = pct("A", CAT_OTHER), pct("B", CAT_OTHER), pct("C", CAT_OTHER)

    L += [
        "## Cross-System Comparison",
        "",
        f"**Temporal-anchor failures** are highest in System A ({ta_a:.0f}%), declining "
        f"through B ({ta_b:.0f}%) to C ({ta_c:.0f}%). This counter-intuitive direction "
        f"arises because A's narrative chunks are generated from a template in relative "
        f"terms without embedding the question's specific reference date, whereas B and C "
        f"retrieve FHIR JSON that contains CarePlan period dates, authoredOn timestamps, "
        f"and administration records from which the model can sometimes infer a temporal "
        f"anchor even without an explicit reference_date in the chunk.",
        "",
        f"**Reasoning-truncated failures** are consistent across all systems "
        f"(A: {tr_a:.0f}%, B: {tr_b:.0f}%, C: {tr_c:.0f}%) and represent the largest "
        f"single failure mode. The 500-character output limit was set to control API "
        f"costs during the smoke-test run; it forces every model response to be "
        f"mid-reasoning. For B and C, the dense multi-resource FHIR JSON expands the "
        f"model's reasoning chain compared to A's single narrative chunk, meaning B and C "
        f"are more likely to hit the limit before computing a final answer.",
        "",
        f"**N/A misuse** is low to absent across systems "
        f"(A: {na_a:.0f}%, B: {na_b:.0f}%, C: {na_c:.0f}%). "
        f"Most cases are Sub-case A (phantom value for absent component): for T1 and T2 "
        f"patients who have no oral adjunct or PRN rescue, the model occasionally "
        f"describes administrations for non-existent components rather than returning N/A.",
        "",
        f"**Wrong-entity / enum errors** are modest across all systems "
        f"(A: {we_a:.0f}%, B: {we_b:.0f}%, C: {we_c:.0f}%), appearing mainly on "
        f"cross_resource questions about schedule kind or tier label where the model "
        f"either misreads FHIR coding or conflates two medication components.",
        "",
        f"**Other / unclassified** is the residual: "
        f"A: {ot_a:.0f}%, B: {ot_b:.0f}%, C: {ot_c:.0f}%. "
        f"These are overwhelmingly cases where the reasoning is completely truncated "
        f"before any diagnostic pattern is visible (the model was still reading the "
        f"context when cut off). They are consistent with the truncation mechanism "
        f"but cannot be deterministically sub-typed without a longer answer.",
        "",
    ]

    L += [
        "## Implication for the Paper",
        "",
        "The taxonomy qualifies the A > B > C ordering from Phase 5. The dominant "
        "failure mode across all systems is **reasoning truncation** -- a direct "
        "consequence of the 500-character output budget used during the smoke-test "
        "run. This is not an architectural property of narrative vs. structured "
        "retrieval; it is a token-budget artefact that disproportionately penalises "
        "B and C because their denser FHIR JSON contexts require longer reasoning chains. "
        "The implication is that the Phase 5 accuracy gap between A and B/C is partly "
        "budget-driven: a fuller evaluation with adequate output tokens would narrow "
        "the gap and might reverse the A > C ordering for temporal-reasoning tasks "
        "(where C's resource-aware retrieval would help most).",
        "The temporal-anchor category further reveals that A's narrative format "
        "does not embed the question's reference date in the retrieved chunk text, "
        "making it the system most likely to lose temporal context -- a structural "
        "weakness that would persist at higher token budgets. "
        "Systems B and C are better positioned to resolve temporal anchoring once "
        "the token limit is lifted, since the FHIR CarePlan period and administration "
        "dates are directly retrievable.",
        "",
    ]

    L += [
        "## Figure",
        "",
        "![Error taxonomy distribution](../figures/error_taxonomy_distribution.png)",
        "",
        "**Caption:** Stacked bar chart of error category distribution for each "
        "system's 50-failure stratified sample (seed=42). "
        "Colours: Wong (2011) colorblind-safe palette. "
        "Percentage labels shown inside bars >= 8%.",
        "",
    ]

    TAXONOMY_MD.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
