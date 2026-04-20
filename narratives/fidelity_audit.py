"""Programmatic fidelity audit for LLM-generated narratives.

Checks — per narrative — that the following items from the source FHIR
bundle are textually recoverable from the narrative:

  * Each medication descriptor (or a substring alias).
  * Each critical date (regimen_start, regimen_end, first & last admin per component).
  * Each interval / cycle specification (e.g. "every 8 weeks", "4 weeks on").
  * The PRN indication, when present.
  * The total administration count per component (as a number token).

Fidelity score = fraction of required items recovered. Uses regex only — no LLM.
Output per patient: narratives/fidelity_reports/<patient_id>.json.

Usage:
  python -m narratives.fidelity_audit \
      --bundles data/fhir_bundles \
      --narratives narratives/llm_narratives \
      --output narratives/fidelity_reports [--sample N]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any


DATE_PATTERN = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
NUMBER_PATTERN = re.compile(r"\b\d+\b")


def _normalise(text: str) -> str:
    return text.lower().strip()


def _descriptor_aliases(descriptor: str) -> list[str]:
    """Return a list of substrings any one of which must appear in the narrative."""
    d = descriptor.lower()
    aliases = [d]
    # Short aliases that preserve meaning
    if "long-acting" in d and "injectable" in d:
        aliases.append("long-acting")
        aliases.append("injectable")
    if "cyclic" in d:
        aliases.append("cyclic")
    if "oral" in d:
        aliases.append("oral")
    if "biologic" in d:
        aliases.append("biologic")
    if "adjunct" in d:
        aliases.append("adjunct")
    if "prn" in d or "as needed" in d or "rescue" in d:
        aliases.extend(["prn", "as needed", "rescue"])
    if "inhaler" in d:
        aliases.append("inhaler")
    if "subcutaneous" in d:
        aliases.append("subcutaneous")
    return list(dict.fromkeys(aliases))


def _interval_tokens(component: dict[str, Any]) -> list[str]:
    toks: list[str] = []
    kind = component.get("schedule_kind")
    if kind == "fixed_interval":
        iv = component.get("interval_days")
        if iv == 1:
            toks.extend(["daily", "each day", "every day", "every 1 day"])
        elif iv == 7:
            toks.extend(["weekly", "every 7 days", "every week"])
        elif iv == 28:
            toks.extend(["every 4 weeks", "every 28 days", "q4w"])
        elif iv == 56:
            toks.extend(["every 8 weeks", "every 56 days", "q8w"])
        elif iv:
            toks.append(f"every {iv} days")
    elif kind == "cyclic":
        on = component.get("cycle_on_weeks")
        off = component.get("cycle_off_weeks")
        if on is not None:
            toks.extend([f"{on} weeks on", f"{on}-week", f"{on} weeks"])
        if off is not None:
            toks.extend([f"{off} weeks off", f"{off}-week"])
        toks.extend(["cyclic", "cycle"])
    elif kind == "prn":
        toks.extend(["prn", "as needed"])
    return toks


def _required_dates(component: dict[str, Any]) -> list[str]:
    """Return first and last administration dates per component (if any)."""
    events = component.get("dose_event_dates") or []
    out: list[str] = []
    if events:
        out.append(events[0])
        out.append(events[-1])
    return list(dict.fromkeys(out))


def audit_one(meta: dict[str, Any], narrative: str) -> dict[str, Any]:
    """Run the fidelity audit for a single patient narrative."""
    text = _normalise(narrative)
    checks: list[dict[str, Any]] = []

    def _check(kind: str, needle: str, *, any_of: list[str] | None = None) -> bool:
        if any_of:
            found = any(n.lower() in text for n in any_of)
            checks.append(
                {
                    "kind": kind,
                    "needle": needle,
                    "any_of": any_of,
                    "found": found,
                }
            )
            return found
        found = needle.lower() in text
        checks.append({"kind": kind, "needle": needle, "found": found})
        return found

    # Tier description (a soft check — we only require any descriptor fragment)
    _check(
        "tier_description",
        meta["tier_description"],
        any_of=_descriptor_aliases(meta["tier_description"]),
    )

    # Regimen start / end dates
    _check("regimen_start", meta["regimen_start"])
    _check("regimen_end", meta["regimen_end"])

    # Per-component checks
    for comp in meta["components"]:
        _check(
            f"descriptor:{comp['component_id']}",
            comp["descriptor"],
            any_of=_descriptor_aliases(comp["descriptor"]),
        )
        intervals = _interval_tokens(comp)
        if intervals:
            _check(
                f"schedule:{comp['component_id']}",
                comp.get("schedule_kind") or "",
                any_of=intervals,
            )
        for d in _required_dates(comp):
            _check(f"admin_date:{comp['component_id']}:{d}", d)
        n = len(comp.get("dose_event_dates") or [])
        if n >= 5:
            # For components with many events, the narrative should state the count
            _check(f"admin_count:{comp['component_id']}", str(n))
        if comp.get("prn_indication"):
            _check(
                f"prn_indication:{comp['component_id']}",
                comp["prn_indication"],
                any_of=[comp["prn_indication"], "as needed", "prn", "rescue"],
            )

    total = len(checks)
    found = sum(1 for c in checks if c["found"])
    score = (found / total) if total else 1.0

    missing = [
        {"kind": c["kind"], "needle": c.get("needle"), "any_of": c.get("any_of")}
        for c in checks
        if not c["found"]
    ]

    return {
        "patient_id": meta["patient_id"],
        "tier": meta["tier"],
        "n_checks": total,
        "n_found": found,
        "score": round(score, 4),
        "missing_items": missing,
        "audited_at": date.today().isoformat(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundles", required=True, type=Path)
    parser.add_argument("--narratives", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--sample", type=int, default=0)
    args = parser.parse_args(argv)

    index = json.loads((args.bundles / "_regimen_index.json").read_text())
    patients = list(index["patients"].values())
    if args.sample > 0:
        patients = patients[: args.sample]

    args.output.mkdir(parents=True, exist_ok=True)
    scores: list[float] = []
    missing: list[str] = []
    for meta in patients:
        pid = meta["patient_id"]
        narrative_path = args.narratives / f"{pid}.txt"
        if not narrative_path.exists():
            missing.append(pid)
            continue
        narrative = narrative_path.read_text()
        report = audit_one(meta, narrative)
        (args.output / f"{pid}.json").write_text(json.dumps(report, indent=2, sort_keys=True))
        scores.append(report["score"])

    if scores:
        mean = sum(scores) / len(scores)
        print(
            f"fidelity: n={len(scores)} mean={mean:.4f} "
            f"min={min(scores):.4f} max={max(scores):.4f} missing_narratives={len(missing)}"
        )
    else:
        print("fidelity: no narratives found", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
