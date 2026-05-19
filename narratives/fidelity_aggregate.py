"""Aggregate fidelity reports into a single markdown summary.

Emits a track-labelled markdown report (reports/fidelity_audit_llm.md for the
LLM-narrative track, reports/fidelity_audit_templated.md for the templated
track) with:
  * Headline fidelity % (weighted entity recall across all patients).
  * O1 success gate: >= 90% recoverable entities.  If < 85%, a loud warning
    is emitted to stderr and embedded in the report.
  * Score distribution histogram (ASCII).
  * Per-tier breakdown table (mean, median, pass-rate, weighted recall per tier).
  * Per-entity-class breakdown table (exact totals from checks_by_class field).
  * Top-10 missing-item categories across the corpus.
  * Top-10 worst-performing narratives (patient id + what was missed).
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

# Entity-class prefixes — preferred display order.
ENTITY_CLASS_ORDER = [
    "tier_description",
    "regimen_start",
    "regimen_end",
    "descriptor",
    "schedule",
    "admin_date",
    "admin_count",
    "prn_indication",
]


def _histogram(scores: list[float]) -> str:
    buckets = [0] * 10
    for s in scores:
        idx = min(9, int(s * 10))
        buckets[idx] += 1
    width = max(buckets) or 1
    lines = []
    for i, b in enumerate(buckets):
        bar = "#" * int(40 * b / width)
        lo, hi = i / 10, (i + 1) / 10
        lines.append(f"  [{lo:.1f}-{hi:.1f})  {bar} ({b})")
    return "\n".join(lines)


def _kind_prefix(kind: str) -> str:
    return (kind or "unknown").split(":", 1)[0]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    reports = sorted(args.reports.glob("*.json"))
    if not reports:
        print(f"No reports found in {args.reports}", file=sys.stderr)
        return 1

    records = [json.loads(p.read_text()) for p in reports]
    scores = [r["score"] for r in records]

    # ------------------------------------------------------------------ #
    # Aggregate-level stats                                                #
    # ------------------------------------------------------------------ #
    mean = statistics.fmean(scores)
    median = statistics.median(scores)
    stdev = statistics.pstdev(scores)
    pct_pass_90 = 100.0 * sum(1 for s in scores if s >= 0.90) / len(scores)

    total_checks = sum(r["n_checks"] for r in records)
    total_found = sum(r["n_found"] for r in records)
    weighted_recall = total_found / total_checks if total_checks else 0.0

    # ------------------------------------------------------------------ #
    # Per-tier breakdown                                                   #
    # ------------------------------------------------------------------ #
    by_tier: dict[int, list[dict]] = defaultdict(list)
    for r in records:
        by_tier[r["tier"]].append(r)

    tier_rows: list[tuple] = []
    for tier in sorted(by_tier):
        recs = by_tier[tier]
        ts = [r["score"] for r in recs]
        tc = sum(r["n_checks"] for r in recs)
        tf = sum(r["n_found"] for r in recs)
        tier_rows.append((
            tier,
            len(recs),
            statistics.fmean(ts),
            statistics.median(ts),
            100.0 * sum(1 for s in ts if s >= 0.90) / len(ts),
            tf / tc if tc else 0.0,
        ))

    # ------------------------------------------------------------------ #
    # Per-entity-class breakdown (exact, using checks_by_class field)     #
    # ------------------------------------------------------------------ #
    class_total: Counter[str] = Counter()
    class_found_cnt: Counter[str] = Counter()

    for r in records:
        for cls, counts in r.get("checks_by_class", {}).items():
            class_total[cls] += counts.get("total", 0)
            class_found_cnt[cls] += counts.get("found", 0)

    # Also collect misses per class for the top-missing-category table.
    per_class_misses: Counter[str] = Counter()
    for r in records:
        for m in r.get("missing_items", []):
            pfx = _kind_prefix(m.get("kind") or "unknown")
            per_class_misses[pfx] += 1

    # ------------------------------------------------------------------ #
    # Top-10 worst narratives                                              #
    # ------------------------------------------------------------------ #
    worst_10 = sorted(records, key=lambda r: r["score"])[:10]

    # ------------------------------------------------------------------ #
    # Gate status                                                          #
    # ------------------------------------------------------------------ #
    if weighted_recall >= 0.90:
        gate_status = "PASS"
    elif weighted_recall >= 0.85:
        gate_status = "WARN (below 90%, above 85%)"
    else:
        gate_status = "FAIL (below 85% — templated-narrative fallback triggered)"

    # ------------------------------------------------------------------ #
    # Build the markdown                                                   #
    # ------------------------------------------------------------------ #
    lines: list[str] = []
    lines.append("# Fidelity Audit - Aggregate")
    lines.append("")
    lines.append(f"**O1 gate (>=90% weighted entity recall): {gate_status}**")
    lines.append("")

    if weighted_recall < 0.85:
        lines.append(
            "> WARNING: Weighted entity recall is below 85%. "
            "This triggers the templated-narrative fallback risk. "
            "Manual review and prompt escalation required."
        )
        lines.append("")
        print(
            f"FIDELITY WARNING: weighted_recall={weighted_recall:.4f} is below 0.85. "
            "Templated-narrative fallback should be considered (risk R1).",
            file=sys.stderr,
        )
    elif weighted_recall < 0.90:
        lines.append(
            "> NOTE: Weighted entity recall is between 85% and 90% -- "
            "below the O1 target. Consider prompt iteration before proceeding."
        )
        lines.append("")

    lines.append("## Headline stats")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| --- | --- |")
    lines.append(f"| n (patients audited) | {len(scores)} |")
    lines.append(f"| Weighted entity recall | {weighted_recall:.4f} ({weighted_recall*100:.1f}%) |")
    lines.append(f"| Macro-average score | {mean:.4f} ({mean*100:.1f}%) |")
    lines.append(f"| Median score | {median:.4f} |")
    lines.append(f"| Stdev | {stdev:.4f} |")
    lines.append(f"| Min score | {min(scores):.4f} |")
    lines.append(f"| Max score | {max(scores):.4f} |")
    lines.append(f"| % patients scoring >= 0.90 | {pct_pass_90:.1f}% |")
    lines.append(f"| Total entity checks | {total_checks} |")
    lines.append(f"| Total entities found | {total_found} |")
    lines.append(f"| Total entities missed | {total_checks - total_found} |")
    lines.append("")

    lines.append("## Score distribution")
    lines.append("```")
    lines.append(_histogram(scores))
    lines.append("```")
    lines.append("")

    lines.append("## Per-tier breakdown")
    lines.append("")
    lines.append("| Tier | n | Mean score | Median | % >= 0.90 | Weighted recall |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for tier, n_t, mean_t, median_t, pct_t, wrecall_t in tier_rows:
        gate_t = "PASS" if wrecall_t >= 0.90 else ("WARN" if wrecall_t >= 0.85 else "FAIL")
        lines.append(
            f"| {tier} | {n_t} | {mean_t:.4f} | {median_t:.4f} | "
            f"{pct_t:.1f}% | {wrecall_t:.4f} ({gate_t}) |"
        )
    lines.append("")

    lines.append("## Per-entity-class breakdown")
    lines.append("")
    lines.append("| Entity class | Total checks | Found | Missed | Pass-rate |")
    lines.append("| --- | --- | --- | --- | --- |")
    all_classes = list(dict.fromkeys(
        ENTITY_CLASS_ORDER + [k for k in class_total if k not in ENTITY_CLASS_ORDER]
    ))
    for cls in all_classes:
        t = class_total.get(cls, 0)
        f = class_found_cnt.get(cls, 0)
        m = t - f
        pr = f / t if t else 1.0
        lines.append(f"| `{cls}` | {t} | {f} | {m} | {pr:.3f} ({pr*100:.1f}%) |")
    lines.append("")

    lines.append("## Top-10 missing-item categories (by miss count)")
    lines.append("")
    for kind, count in per_class_misses.most_common(10):
        t = class_total.get(kind, 0)
        pr = 1.0 - count / t if t else 0.0
        lines.append(f"- `{kind}` -- {count} misses of {t} total (pass-rate {pr*100:.1f}%)")
    lines.append("")

    lines.append("## Top-10 worst-performing narratives (spot-check list)")
    lines.append("")
    lines.append("| Rank | Patient ID | Tier | Score | n_checks | n_found | Missing categories |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for rank, r in enumerate(worst_10, 1):
        miss_kinds = Counter(
            _kind_prefix(m.get("kind") or "") for m in r.get("missing_items", [])
        )
        top = ", ".join(f"{k}x{v}" for k, v in miss_kinds.most_common(5))
        lines.append(
            f"| {rank} | `{r['patient_id']}` | {r['tier']} | {r['score']:.4f} "
            f"| {r['n_checks']} | {r['n_found']} | {top} |"
        )
    lines.append("")

    lines.append("## All patients below 0.90")
    below_90 = sorted([r for r in records if r["score"] < 0.90], key=lambda r: r["score"])
    if not below_90:
        lines.append("_None._")
    else:
        lines.append(f"_{len(below_90)} patients below 0.90 threshold:_")
        lines.append("")
        for r in below_90:
            miss_kinds = Counter(
                _kind_prefix(m.get("kind") or "") for m in r.get("missing_items", [])
            )
            top = ", ".join(f"{k}x{v}" for k, v in miss_kinds.most_common(3))
            lines.append(
                f"- `{r['patient_id']}` (tier {r['tier']}): "
                f"score={r['score']:.3f}, missed={top}"
            )
    lines.append("")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n")
    print(
        f"aggregate: wrote {args.output} "
        f"(n={len(scores)} weighted_recall={weighted_recall:.4f} "
        f"macro_mean={mean:.4f} gate={gate_status})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
