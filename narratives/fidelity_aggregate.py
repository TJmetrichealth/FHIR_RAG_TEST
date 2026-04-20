"""Aggregate fidelity reports into a single markdown summary.

Emits reports/fidelity_audit.md with:
  * Summary line: n, mean, median, stdev, min, max, % ≥ 0.90.
  * Score distribution histogram (ASCII).
  * Top 5 missing-item categories across the corpus.
  * Patients below 0.90 with their top missing items.
"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path


def _histogram(scores: list[float]) -> str:
    buckets = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    for s in scores:
        idx = min(9, int(s * 10))
        buckets[idx] += 1
    width = max(buckets) or 1
    lines = []
    for i, b in enumerate(buckets):
        bar = "#" * int(40 * b / width)
        lo, hi = i / 10, (i + 1) / 10
        lines.append(f"  [{lo:.1f}–{hi:.1f})  {bar} ({b})")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    reports = sorted(args.reports.glob("*.json"))
    if not reports:
        print(f"No reports found in {args.reports}")
        return 1

    records = [json.loads(p.read_text()) for p in reports]
    scores = [r["score"] for r in records]
    missing_kinds: Counter[str] = Counter()
    for r in records:
        for m in r.get("missing_items", []):
            kind = (m.get("kind") or "unknown").split(":", 1)[0]
            missing_kinds[kind] += 1

    below = sorted(
        [r for r in records if r["score"] < 0.90],
        key=lambda r: r["score"],
    )

    mean = statistics.fmean(scores)
    median = statistics.median(scores)
    stdev = statistics.pstdev(scores)
    pct_pass = 100.0 * sum(1 for s in scores if s >= 0.90) / len(scores)

    lines: list[str] = []
    lines.append("# Fidelity Audit — Aggregate")
    lines.append("")
    lines.append(
        f"- **n** = {len(scores)}  "
        f"**mean** = {mean:.4f}  "
        f"**median** = {median:.4f}  "
        f"**stdev** = {stdev:.4f}  "
        f"**min** = {min(scores):.4f}  "
        f"**max** = {max(scores):.4f}"
    )
    lines.append(f"- **% ≥ 0.90** = {pct_pass:.1f}%")
    lines.append("")
    lines.append("## Score distribution")
    lines.append("```")
    lines.append(_histogram(scores))
    lines.append("```")
    lines.append("")
    lines.append("## Top missing-item categories")
    for kind, count in missing_kinds.most_common(10):
        lines.append(f"- `{kind}` — {count}")
    lines.append("")
    lines.append("## Patients below 0.90")
    if not below:
        lines.append("_None._")
    else:
        for r in below:
            miss_kinds = Counter(
                (m.get("kind") or "").split(":", 1)[0] for m in r.get("missing_items", [])
            )
            top = ", ".join(f"{k}×{v}" for k, v in miss_kinds.most_common(3))
            lines.append(
                f"- `{r['patient_id']}` (tier {r['tier']}): "
                f"score={r['score']:.3f}, missing={top}"
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n")
    print(f"aggregate: wrote {args.output} (n={len(scores)} mean={mean:.4f} pass={pct_pass:.1f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
