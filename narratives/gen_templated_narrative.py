"""Deterministic templated-narrative generator.

Renders the regimen metadata for each patient into prose — no LLM, no
randomness. This is the ablation ceiling (maximum fidelity by construction)
and the fallback if the LLM narratives fail the 90% gate (Risk R1).

Template version: v2 (2026-04-19)
Design rationale:
  - Prose style approximates a PSP nurse handover note — full sentences, not
    a structured dump — so the text is comparable in register to the LLM
    narratives but is 100% deterministic.
  - Every entity class checked by fidelity_audit.py is explicitly rendered:
      tier_description  regimen_start  regimen_end  descriptor (per component)
      schedule (interval or cycle tokens)  admin_date (first + last per
      component)  admin_count (when >= 5 events)  prn_indication.
  - For fixed_interval components the interval is expressed in both days AND
    weeks/shorthand where natural (e.g. "every 56 days (every 8 weeks, q8w)")
    so the audit regex hits either token variant.
  - The first-three / last-three date sentence is included for all components
    with > 6 events, matching the LLM narrative style and satisfying
    admin_date checks.
  - No extra data beyond what is in the regimen index is assumed.
  - Rendering is pure-Python string building (no Jinja2 whitespace ambiguity).

Usage:
  python -m narratives.gen_templated_narrative \
      --bundles data/fhir_bundles \
      --output narratives/templated_narratives [--sample N]
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Human-readable interval helpers
# ---------------------------------------------------------------------------

def _interval_prose(interval_days: int | None) -> str:
    """Return a prose interval string that satisfies all fidelity-audit tokens."""
    if interval_days is None:
        return "an unspecified interval"
    if interval_days == 1:
        return "every 1 day (daily)"
    if interval_days == 7:
        return "every 7 days (weekly)"
    if interval_days == 14:
        return "every 14 days (biweekly)"
    if interval_days == 28:
        return "every 28 days (every 4 weeks, q4w)"
    if interval_days == 56:
        return "every 56 days (every 8 weeks, q8w)"
    if interval_days % 7 == 0:
        w = interval_days // 7
        return f"every {interval_days} days (every {w} weeks)"
    return f"every {interval_days} days"


# ---------------------------------------------------------------------------
# Core renderer — pure Python string building
# ---------------------------------------------------------------------------

def _render_component(comp: dict[str, Any], index: int, total: int) -> str:
    """Render one component as a prose paragraph."""
    parts: list[str] = []

    # Component prefix for multi-component regimens
    if total > 1:
        prefix = f"Component {index} of {total}: "
    else:
        prefix = ""

    descriptor = comp["descriptor"]
    kind = comp.get("schedule_kind")

    # Schedule sentence
    if kind == "fixed_interval":
        interval_prose = _interval_prose(comp.get("interval_days"))
        schedule_sent = (
            f"{prefix}The {descriptor} is given on a fixed schedule of {interval_prose}."
        )
    elif kind == "cyclic":
        on = comp.get("cycle_on_weeks")
        off = comp.get("cycle_off_weeks")
        schedule_sent = (
            f"{prefix}The {descriptor} follows a cyclic schedule of "
            f"{on} weeks on and {off} weeks off (cyclic)."
        )
    elif kind == "prn":
        prn_ind = comp.get("prn_indication")
        if prn_ind:
            schedule_sent = (
                f"{prefix}The {descriptor} is administered as needed (PRN) for {prn_ind}."
            )
        else:
            schedule_sent = (
                f"{prefix}The {descriptor} is administered as needed (PRN)."
            )
    else:
        schedule_sent = f"{prefix}The {descriptor} has an unspecified schedule."

    parts.append(schedule_sent)

    # Administration dates / count sentence
    dates = comp.get("dose_event_dates") or []
    n = len(dates)
    if n == 0:
        parts.append(
            "No administrations have been recorded for this component "
            "within the observation window."
        )
    else:
        pl = "administrations" if n != 1 else "administration"
        count_sent = (
            f"A total of {n} {pl} are on record for this component. "
            f"The first administration was on {dates[0]} and the most recent "
            f"was on {dates[-1]}."
        )
        parts.append(count_sent)
        if n > 6:
            first3 = ", ".join(dates[:3])
            last3 = ", ".join(dates[-3:])
            # Mid-window coverage: emit the median-indexed administration date
            # so the fidelity audit's admin_dates[n//2] check is satisfied.
            # This is a real date from the MedicationAdministration resources,
            # not synthesized. For n <= 6, first-three/last-three already span
            # the full list, so no additional date is needed.
            mid_date = dates[n // 2]
            parts.append(
                f"The first three recorded dates are {first3}; "
                f"the last three are {last3}; "
                f"a mid-window administration occurred on {mid_date}."
            )

    return " ".join(parts)


def render(meta: dict[str, Any]) -> str:
    """Render one patient's regimen as a deterministic prose narrative."""
    lines: list[str] = []

    # Opening paragraph: tier description + regimen window
    tier_desc = meta["tier_description"]
    tier = meta["tier"]
    tier_label = meta["tier_label"]
    start = meta["regimen_start"]
    end = meta["regimen_end"]
    horizon = meta["horizon_days"]

    lines.append(
        f"This patient is enrolled in a {tier_desc} "
        f"The specialty regimen is classified as tier {tier} ({tier_label}) "
        f"and spans from {start} to {end}, "
        f"a total observation window of {horizon} days."
    )
    lines.append("")

    # One paragraph per component
    components = meta.get("components") or []
    total = len(components)
    for i, comp in enumerate(components, start=1):
        lines.append(_render_component(comp, i, total))
        if i < total:
            lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Template version hash — SHA-256 of the render function source for
# reproducibility. Computed over the body of _render_component + render.
# ---------------------------------------------------------------------------

import inspect as _inspect

_RENDER_SOURCE = (
    _inspect.getsource(_render_component) + _inspect.getsource(render)
)
TEMPLATE_VERSION_HASH = hashlib.sha256(_RENDER_SOURCE.encode()).hexdigest()[:16]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundles", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--sample", type=int, default=0)
    args = parser.parse_args(argv)

    args.output.mkdir(parents=True, exist_ok=True)
    index = json.loads((args.bundles / "_regimen_index.json").read_text())
    patients = list(index["patients"].values())
    if args.sample > 0:
        patients = patients[: args.sample]

    produced = 0
    manifest_entries: list[dict[str, Any]] = []

    for meta in patients:
        text = render(meta)
        out_path = args.output / f"{meta['patient_id']}.txt"
        out_path.write_text(text.strip() + "\n", encoding="utf-8")
        manifest_entries.append(
            {
                "patient_id": meta["patient_id"],
                "tier": meta["tier"],
                "tier_label": meta["tier_label"],
                "output_file": out_path.name,
            }
        )
        produced += 1

    # Write generation manifest (single file for the whole run)
    manifest = {
        "generator": "gen_templated_narrative.py",
        "template_version": "v2",
        "render_fn_sha256_prefix": TEMPLATE_VERSION_HASH,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "n_patients": produced,
        "patients": manifest_entries,
    }
    manifest_path = args.output / "_generation_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(
        f"templated: produced={produced} "
        f"template_version=v2 "
        f"render_hash={TEMPLATE_VERSION_HASH} "
        f"output_dir={args.output} "
        f"manifest={manifest_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
