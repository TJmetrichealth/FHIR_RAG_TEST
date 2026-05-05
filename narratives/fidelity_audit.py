"""Programmatic fidelity audit for LLM-generated (or templated) narratives.

Ground-truth redesign (v2, 2026-04-27)
---------------------------------------
v1 of this auditor read expected values from ``data/fhir_bundles/_regimen_index.json``.
Because the LLM narrative prompt *also* reads from that same index, the audit was
circular: it measured "did the LLM copy its own prompt back" rather than "can FHIR
entities be recovered from the narrative text."

v2 derives ALL expected values directly from the FHIR bundle resources:

  * Medication names      — ``Medication.code.text`` (primary)
                            ``Medication.code.coding[].display`` (fallback)
  * Regimen start/end     — specialty ``CarePlan.period.start/.end``
                            (CarePlan whose id starts with ``spec-cp-``)
  * Tier (integer)        — parsed from ``CarePlan.note[].text`` (``tier=N``)
  * Tier description      — ``CarePlan.description``
  * Dose-event dates      — ``MedicationAdministration.effectiveDateTime[:10]``
                            (grouped by ``request.reference`` → component_id suffix)
  * Dosage text           — ``MedicationRequest.dosageInstruction[0].text``
  * Schedule              — derived from ``MedicationRequest.dosageInstruction``

The ``_regimen_index.json`` is never read by this module.

Descriptor matching policy (v2)
---------------------------------
A tier-description or component-descriptor check PASSES only if either:
  (a) the full descriptor substring appears verbatim (case-insensitive) in the
      narrative, OR
  (b) at least TWO distinct alias tokens co-occur within the narrative.

A single generic alias token (e.g. "oral") is NOT sufficient on its own.  A
narrative that says "patient takes an oral medication" will no longer pass a T2
descriptor check whose descriptor is "cyclic oral specialty therapy (4 weeks on,
2 weeks off)".  The intent is to reward narratives that surface the distinguishing
descriptor terms, not ones that happen to mention a single generic word.

Output shape per patient
--------------------------
{
  "patient_id": ...,
  "tier": ...,
  "n_checks": ...,
  "n_found": ...,
  "score": ...,
  "checks_by_class": { class: { "total": N, "found": N } },
  "missing_items": [ { "kind": ..., "needle": ..., "any_of": [...] } ],
  "audited_at": "YYYY-MM-DD",
  "errors": [ "string describing any parse error" ]
}

The ``fidelity_aggregate.py`` script reads this shape; it is unchanged from v1.

Usage:
  python -m narratives.fidelity_audit \\
      --bundles data/fhir_bundles \\
      --narratives narratives/llm_narratives \\
      --output narratives/fidelity_reports [--sample N]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any


DATE_PATTERN = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
NUMBER_PATTERN = re.compile(r"\b\d+\b")

# --------------------------------------------------------------------------- #
# FHIR bundle parsing — independent ground truth                               #
# --------------------------------------------------------------------------- #

def _extract_ground_truth(bundle_path: Path) -> dict[str, Any]:
    """Parse a FHIR bundle and return structured ground-truth entities.

    Returns a dict with keys:
      patient_id, tier, tier_description,
      regimen_start, regimen_end,
      components: list of {
          component_id, medication_name, dosage_text, n_administrations,
          admin_dates (sorted list of YYYY-MM-DD strings)
      }
      errors: list of str
    """
    errors: list[str] = []
    pid = bundle_path.stem

    try:
        data = json.loads(bundle_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"patient_id": pid, "tier": 0, "tier_description": "", "regimen_start": "",
                "regimen_end": "", "components": [], "errors": [f"bundle parse error: {exc}"]}

    entries = data.get("entry", [])

    # Index resources by id for O(1) lookup
    res_by_id: dict[str, dict] = {}
    for e in entries:
        r = e.get("resource", {})
        rid = r.get("id", "")
        if rid:
            res_by_id[rid] = r

    # ------------------------------------------------------------------ #
    # Step 1: Locate the specialty CarePlan (id prefix "spec-cp-")        #
    # ------------------------------------------------------------------ #
    spec_cp: dict | None = None
    for e in entries:
        r = e.get("resource", {})
        if r.get("resourceType") == "CarePlan" and r.get("id", "").startswith("spec-cp-"):
            spec_cp = r
            break

    if spec_cp is None:
        errors.append("no specialty CarePlan (spec-cp-*) found")
        return {"patient_id": pid, "tier": 0, "tier_description": "",
                "regimen_start": "", "regimen_end": "", "components": [], "errors": errors}

    # Period start/end
    period = spec_cp.get("period") or {}
    regimen_start: str = (period.get("start") or "")[:10]
    regimen_end: str = (period.get("end") or "")[:10]
    if not regimen_start:
        errors.append("CarePlan.period.start missing")
    if not regimen_end:
        errors.append("CarePlan.period.end missing")

    # Tier description from description field
    tier_description: str = spec_cp.get("description") or ""
    if not tier_description:
        errors.append("CarePlan.description missing")

    # Tier integer from note
    tier: int = 0
    for note in spec_cp.get("note") or []:
        text = note.get("text") or ""
        m = re.search(r"tier=(\d+)", text)
        if m:
            tier = int(m.group(1))
            break
    if tier == 0:
        # Fallback: parse from title "Specialty regimen — tier N"
        title = spec_cp.get("title") or ""
        m2 = re.search(r"tier\s+(\d+)", title, re.IGNORECASE)
        if m2:
            tier = int(m2.group(1))
        else:
            errors.append("Could not parse tier from CarePlan note or title")

    # ------------------------------------------------------------------ #
    # Step 2: Identify specialty MedicationRequests from CarePlan         #
    # activities. Each activity reference → one component.               #
    # ------------------------------------------------------------------ #
    activities = spec_cp.get("activity") or []
    req_ids: list[str] = []
    for act in activities:
        ref = (act.get("reference") or {}).get("reference") or ""
        if ref.startswith("MedicationRequest/spec-req-"):
            req_ids.append(ref.split("/", 1)[1])

    if not req_ids:
        errors.append("No specialty MedicationRequest activities in CarePlan")

    # ------------------------------------------------------------------ #
    # Step 3: Build component ground truth from MedicationRequest +       #
    # Medication resources                                                #
    # ------------------------------------------------------------------ #
    components: list[dict[str, Any]] = []

    for req_id in req_ids:
        req = res_by_id.get(req_id)
        if req is None:
            errors.append(f"MedicationRequest {req_id!r} not found in bundle")
            continue

        # Derive component_id from the req id suffix (e.g. "...-primary" → "primary")
        # Convention: spec-req-<pid>-<component_id>
        parts = req_id.rsplit("-", 1)
        component_id = parts[-1] if len(parts) == 2 else req_id

        # Medication name — resolve via medicationReference
        med_name: str = ""
        med_ref = (req.get("medicationReference") or {}).get("reference") or ""
        if med_ref.startswith("Medication/"):
            med_id = med_ref.split("/", 1)[1]
            med = res_by_id.get(med_id)
            if med:
                # Prefer code.text, then first coding.display
                code = med.get("code") or {}
                med_name = code.get("text") or ""
                if not med_name:
                    for coding in code.get("coding") or []:
                        if coding.get("display"):
                            med_name = coding["display"]
                            break
            else:
                errors.append(f"Medication {med_id!r} not found for request {req_id!r}")
        else:
            errors.append(f"MedicationRequest {req_id!r} has no medicationReference")

        # Dosage text from first dosageInstruction
        dosage_text: str = ""
        for di in req.get("dosageInstruction") or []:
            dosage_text = di.get("text") or ""
            break

        components.append({
            "component_id": component_id,
            "req_id": req_id,
            "medication_name": med_name,
            "dosage_text": dosage_text,
            "admin_dates": [],   # filled in step 4
            "n_administrations": 0,
        })

    # Build a map from req_id to component entry
    comp_by_req: dict[str, dict] = {c["req_id"]: c for c in components}

    # ------------------------------------------------------------------ #
    # Step 4: Collect MedicationAdministration dates per component        #
    # ------------------------------------------------------------------ #
    for e in entries:
        r = e.get("resource", {})
        if r.get("resourceType") != "MedicationAdministration":
            continue
        req_ref = (r.get("request") or {}).get("reference") or ""
        # Format: "MedicationRequest/<req_id>"
        if req_ref.startswith("MedicationRequest/"):
            ref_req_id = req_ref.split("/", 1)[1]
        else:
            ref_req_id = req_ref

        comp = comp_by_req.get(ref_req_id)
        if comp is None:
            continue

        eff = r.get("effectiveDateTime") or ""
        date_str = eff[:10]
        if DATE_PATTERN.match(date_str):
            comp["admin_dates"].append(date_str)

    for comp in components:
        comp["admin_dates"] = sorted(set(comp["admin_dates"]))
        comp["n_administrations"] = len(comp["admin_dates"])

    return {
        "patient_id": pid,
        "tier": tier,
        "tier_description": tier_description,
        "regimen_start": regimen_start,
        "regimen_end": regimen_end,
        "components": components,
        "errors": errors,
    }


# --------------------------------------------------------------------------- #
# Descriptor alias & matching policy (v2 — stricter)                           #
# --------------------------------------------------------------------------- #

def _descriptor_aliases(descriptor: str) -> list[str]:
    """Return candidate alias tokens for a descriptor string.

    Matching policy (v2):
      A descriptor check passes ONLY if either:
        (a) the full descriptor substring appears verbatim (case-insensitive), OR
        (b) at least TWO distinct alias tokens from this list co-occur in the text.

      A single alias token alone is NOT sufficient.  This prevents a narrative
      that says "patient takes an oral medication" from passing a descriptor check
      whose descriptor is "cyclic oral specialty therapy (4 weeks on, 2 weeks off)".

    Aliases are chosen to be semantically specific — generic single-word tokens
    like "oral" or "daily" do not appear alone (they appear alongside more
    specific tokens or not at all).
    """
    d = descriptor.lower()
    aliases: list[str] = []
    # Route tokens (specific pairings only)
    if "subcutaneous" in d:
        aliases.append("subcutaneous")
    if "injectable" in d:
        aliases.append("injectable")
    if "inhaler" in d:
        aliases.append("inhaler")
    # Mode/class tokens
    if "biologic" in d:
        aliases.append("biologic")
    if "adjunct" in d:
        aliases.append("adjunct")
    if "long-acting" in d:
        aliases.append("long-acting")
    # Schedule tokens
    if "cyclic" in d:
        aliases.append("cyclic")
    if "4 weeks on" in d or "4-week" in d:
        aliases.append("4 weeks on")
    if "2 weeks off" in d or "2-week" in d:
        aliases.append("2 weeks off")
    if "q4w" in d or "every 4 weeks" in d or "every 28 days" in d:
        aliases.extend(["q4w", "every 4 weeks", "every 28 days"])
    if "q8w" in d or "every 8 weeks" in d or "every 56 days" in d:
        aliases.extend(["q8w", "every 8 weeks", "every 56 days"])
    if "daily" in d:
        aliases.append("daily")
    if "weekly" in d:
        aliases.append("weekly")
    # PRN synonyms
    if "prn" in d or "as needed" in d or "rescue" in d:
        aliases.extend(["prn", "as needed", "rescue"])
    # Route for oral — only as a reinforcing token, never sole pass
    if "oral" in d:
        aliases.append("oral")
    return list(dict.fromkeys(aliases))


def _descriptor_found(descriptor: str, text: str) -> bool:
    """Return True if the descriptor is sufficiently present in text.

    Policy (v2):
      (a) full descriptor (case-insensitive substring) present, OR
      (b) >= 2 distinct alias tokens co-occur.
    """
    d_lower = descriptor.lower()
    if d_lower in text:
        return True
    aliases = _descriptor_aliases(descriptor)
    matched = [a for a in aliases if a.lower() in text]
    return len(set(matched)) >= 2


# --------------------------------------------------------------------------- #
# Schedule token extraction from FHIR dosageInstruction text                  #
# --------------------------------------------------------------------------- #

def _schedule_tokens_from_dosage(dosage_text: str) -> list[str]:
    """Derive schedule check tokens from the dosage instruction text.

    We parse the free-text ``dosageInstruction.text`` from the MedicationRequest.
    This is the ground truth for schedule — not the regimen_index.
    """
    toks: list[str] = []
    d = dosage_text.lower()

    # Cyclic pattern detection
    cycle_match = re.search(r"(\d+)\s*weeks?\s+on[,/\s]+(\d+)\s*weeks?\s+off", d)
    if cycle_match:
        on = cycle_match.group(1)
        off = cycle_match.group(2)
        toks.extend([
            f"{on} weeks on", f"{on}-week", f"{on} weeks",
            f"{off} weeks off", f"{off}-week",
            "cyclic", "cycle",
        ])

    # Fixed interval patterns
    if re.search(r"every\s+56\s*days|every\s+8\s*weeks|q8w|q-8w", d):
        toks.extend(["every 8 weeks", "every 56 days", "q8w"])
    elif re.search(r"every\s+28\s*days|every\s+4\s*weeks|q4w|q-4w", d):
        toks.extend(["every 4 weeks", "every 28 days", "q4w"])
    elif re.search(r"every\s+14\s*days|biweekly|bi-weekly|every\s+2\s*weeks", d):
        toks.extend(["every 14 days", "biweekly", "every 2 weeks"])
    elif re.search(r"every\s+7\s*days|weekly|every\s+week", d):
        toks.extend(["weekly", "every 7 days", "every week"])
    elif re.search(r"every\s+1\s*day|daily|each\s+day|every\s+day", d):
        toks.extend(["daily", "each day", "every day", "every 1 day"])
    elif re.search(r"every\s+(\d+)\s*days", d):
        m = re.search(r"every\s+(\d+)\s*days", d)
        if m:
            toks.append(f"every {m.group(1)} days")

    # PRN
    if re.search(r"\bprn\b|as needed|rescue", d):
        toks.extend(["prn", "as needed"])

    return list(dict.fromkeys(toks))


# --------------------------------------------------------------------------- #
# Core audit function                                                          #
# --------------------------------------------------------------------------- #

def audit_one(ground_truth: dict[str, Any], narrative: str) -> dict[str, Any]:
    """Run the fidelity audit for a single patient narrative.

    ``ground_truth`` is the output of ``_extract_ground_truth()``.
    ``narrative`` is the raw narrative text string.

    Returns a per-patient report dict.
    """
    text = narrative.lower().strip()
    checks: list[dict[str, Any]] = []
    parse_errors: list[str] = ground_truth.get("errors") or []

    def _check_exact(kind: str, needle: str) -> bool:
        found = needle.lower() in text
        checks.append({"kind": kind, "needle": needle, "found": found})
        return found

    def _check_any_of(kind: str, needle: str, any_of: list[str]) -> bool:
        found = any(n.lower() in text for n in any_of)
        checks.append({"kind": kind, "needle": needle, "any_of": any_of, "found": found})
        return found

    def _check_descriptor(kind: str, descriptor: str) -> bool:
        found = _descriptor_found(descriptor, text)
        aliases = _descriptor_aliases(descriptor)
        checks.append({"kind": kind, "needle": descriptor, "any_of": aliases, "found": found})
        return found

    # ---- tier description ------------------------------------------------ #
    tier_desc = ground_truth.get("tier_description") or ""
    if tier_desc:
        _check_descriptor("tier_description", tier_desc)

    # ---- regimen dates --------------------------------------------------- #
    regimen_start = ground_truth.get("regimen_start") or ""
    regimen_end = ground_truth.get("regimen_end") or ""
    if regimen_start:
        _check_exact("regimen_start", regimen_start)
    if regimen_end:
        _check_exact("regimen_end", regimen_end)

    # ---- per-component checks -------------------------------------------- #
    for comp in ground_truth.get("components") or []:
        comp_id = comp["component_id"]
        med_name = comp.get("medication_name") or ""
        dosage_text = comp.get("dosage_text") or ""
        admin_dates: list[str] = comp.get("admin_dates") or []
        n_admin = comp.get("n_administrations") or 0

        # Medication name / descriptor
        if med_name:
            _check_descriptor(f"descriptor:{comp_id}", med_name)

        # Dosage/schedule tokens (derived from dosageInstruction.text)
        sched_toks = _schedule_tokens_from_dosage(dosage_text)
        if sched_toks:
            _check_any_of(
                f"schedule:{comp_id}",
                dosage_text,
                any_of=sched_toks,
            )

        # Administration dates: first, last, and a middle sample
        if admin_dates:
            required_dates: list[str] = []
            required_dates.append(admin_dates[0])
            required_dates.append(admin_dates[-1])
            if len(admin_dates) >= 3:
                mid = len(admin_dates) // 2
                required_dates.append(admin_dates[mid])
            for d in dict.fromkeys(required_dates):
                _check_exact(f"admin_date:{comp_id}:{d}", d)

        # Administration count — only for components with >= 5 events
        if n_admin >= 5:
            _check_exact(f"admin_count:{comp_id}", str(n_admin))

        # PRN indication — derived from dosageInstruction.text
        if re.search(r"\bprn\b|as needed", dosage_text.lower()):
            # Extract the indication phrase if present (after "for ")
            m_for = re.search(r"for\s+(.+)", dosage_text, re.IGNORECASE)
            prn_indication = m_for.group(1).strip() if m_for else ""
            if prn_indication:
                _check_any_of(
                    f"prn_indication:{comp_id}",
                    prn_indication,
                    any_of=[prn_indication.lower(), "as needed", "prn", "rescue"],
                )
            else:
                _check_any_of(
                    f"prn_indication:{comp_id}",
                    "prn",
                    any_of=["prn", "as needed", "rescue"],
                )

    total = len(checks)
    found = sum(1 for c in checks if c["found"])
    score = (found / total) if total else 1.0

    missing = [
        {"kind": c["kind"], "needle": c.get("needle"), "any_of": c.get("any_of")}
        for c in checks
        if not c["found"]
    ]

    # Per-class breakdowns
    checks_by_class: dict[str, dict[str, int]] = {}
    for c in checks:
        prefix = (c["kind"] or "unknown").split(":", 1)[0]
        entry = checks_by_class.setdefault(prefix, {"total": 0, "found": 0})
        entry["total"] += 1
        if c["found"]:
            entry["found"] += 1

    return {
        "patient_id": ground_truth["patient_id"],
        "tier": ground_truth["tier"],
        "n_checks": total,
        "n_found": found,
        "score": round(score, 4),
        "checks_by_class": checks_by_class,
        "missing_items": missing,
        "errors": parse_errors,
        "audited_at": date.today().isoformat(),
    }


# --------------------------------------------------------------------------- #
# CLI entry point                                                               #
# --------------------------------------------------------------------------- #

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundles", required=True, type=Path,
                        help="Directory containing FHIR bundles (*.json).")
    parser.add_argument("--narratives", required=True, type=Path,
                        help="Directory containing narrative text files (<pid>.txt).")
    parser.add_argument("--output", required=True, type=Path,
                        help="Directory to write per-patient JSON fidelity reports.")
    parser.add_argument("--sample", type=int, default=0,
                        help="Audit only the first N bundles (0 = all).")
    args = parser.parse_args(argv)

    bundle_paths = sorted(args.bundles.glob("[!_]*.json"))
    if args.sample > 0:
        bundle_paths = bundle_paths[: args.sample]

    args.output.mkdir(parents=True, exist_ok=True)
    scores: list[float] = []
    missing_narratives: list[str] = []
    parse_error_count = 0

    for bundle_path in bundle_paths:
        pid = bundle_path.stem
        narrative_path = args.narratives / f"{pid}.txt"
        if not narrative_path.exists():
            missing_narratives.append(pid)
            continue

        ground_truth = _extract_ground_truth(bundle_path)
        if ground_truth.get("errors"):
            parse_error_count += 1

        narrative = narrative_path.read_text(encoding="utf-8")
        report = audit_one(ground_truth, narrative)

        (args.output / f"{pid}.json").write_text(
            json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
        )
        scores.append(report["score"])

    if scores:
        mean = sum(scores) / len(scores)
        print(
            f"fidelity: n={len(scores)} mean={mean:.4f} "
            f"min={min(scores):.4f} max={max(scores):.4f} "
            f"missing_narratives={len(missing_narratives)} "
            f"parse_errors={parse_error_count}"
        )
    else:
        print("fidelity: no narratives found", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
