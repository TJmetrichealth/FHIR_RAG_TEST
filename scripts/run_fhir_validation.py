"""End-to-end FHIR validation orchestrator.

Runs the Pydantic R4B validator (always) and optionally the HL7 official
Java validator (requires tools/hl7-validator/validator_cli.jar).

Usage:
  python scripts/run_fhir_validation.py \\
      --bundles data/fhir_bundles \\
      --output-dir results \\
      --reports-dir reports \\
      [--skip-hl7]

Exit codes:
  0  Pydantic 100% pass AND HL7 zero non-allowlisted errors
  1  Pydantic failures or HL7 non-allowlisted errors
  2  Setup problem (missing jar, missing JRE) with instructions printed
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent

# Ensure the repo root is on sys.path so `from mh_integration.* import ...`
# works whether this script is invoked as `python scripts/run_fhir_validation.py`
# (no -m) or via `make fhir-validate`.
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _check_setup(skip_hl7: bool) -> int:
    """Verify that JRE and jar are present. Return 0 if ok; print instructions and return 2 if not."""
    jar_path = _REPO_ROOT / "tools" / "hl7-validator" / "validator_cli.jar"
    jre_path = _REPO_ROOT / "tools" / "jre"

    if skip_hl7:
        return 0

    jre_ok = jre_path.exists() and (
        (jre_path / "bin" / "java").exists() or (jre_path / "bin" / "java.exe").exists()
    )
    jar_ok = jar_path.exists()

    if not jre_ok or not jar_ok:
        missing = []
        if not jre_ok:
            missing.append(f"  JRE not found at {jre_path}")
        if not jar_ok:
            missing.append(f"  HL7 jar not found at {jar_path}")
        print("ERROR: HL7 validation setup incomplete:", file=sys.stderr)
        for m in missing:
            print(m, file=sys.stderr)
        print(
            "\nFix by running:\n"
            "  bash scripts/setup_java_portable.sh\n"
            "  bash scripts/setup_hl7_validator.sh\n"
            "\nOr skip HL7 validation with --skip-hl7",
            file=sys.stderr,
        )
        return 2

    return 0


def _extract_tier_from_bundle(bundle_path: Path) -> str:
    """Extract tier from a CarePlan note matching 'tier=N' in the bundle JSON.

    Returns the tier string or 'unknown'.
    """
    try:
        raw = json.loads(bundle_path.read_text(encoding="utf-8"))
        for entry in raw.get("entry", []):
            res = entry.get("resource", {})
            if res.get("resourceType") == "CarePlan" and res.get("id", "").startswith("spec-cp-"):
                for note in res.get("note", []):
                    text = note.get("text", "")
                    m = re.search(r"tier=(\d+)", text)
                    if m:
                        return m.group(1)
    except Exception:
        pass
    return "unknown"


def _run_pydantic_phase(bundles_dir: Path, output_dir: Path) -> dict:
    """Run the Pydantic validator and return a summary dict."""
    from mh_integration.r4b_validator import validate_all

    output_csv = output_dir / "conformance_rates.csv"
    summary = validate_all(bundles_dir, output_csv)
    summary["csv_path"] = str(output_csv)
    return summary


def _run_hl7_phase(
    bundles_dir: Path,
    output_dir: Path,
    allowlist_path: Path,
    disable_tx_server: bool = True,
) -> tuple[dict, Path]:
    """Run the HL7 validator and return (summary dict, results_csv_path)."""
    from mh_integration.hl7_validator import HL7Validator

    jar_path = _REPO_ROOT / "tools" / "hl7-validator" / "validator_cli.jar"
    jre_path = _REPO_ROOT / "tools" / "jre"
    raw_dir = output_dir / "hl7_validator_raw"
    results_csv = output_dir / "hl7_validator_results.csv"

    v = HL7Validator(
        jar_path=jar_path,
        jre_path=jre_path,
        allowlist_path=allowlist_path if allowlist_path.exists() else None,
        fhir_version="4.3.0",
    )
    results = v.validate_directory(bundles_dir, raw_dir, disable_tx_server=disable_tx_server)

    # Determine tier per patient from bundle files
    bundle_tier: dict[str, str] = {}
    for p in bundles_dir.glob("*.json"):
        if not p.stem.endswith("_regimen_index"):
            bundle_tier[p.stem] = _extract_tier_from_bundle(p)

    results_csv.parent.mkdir(parents=True, exist_ok=True)
    with results_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "patient_id", "tier", "error_count", "expected_warning_count",
                "other_warning_count", "severity_histogram_json", "errors_json",
            ],
        )
        writer.writeheader()
        for r in results:
            writer.writerow({
                "patient_id": r.patient_id,
                "tier": bundle_tier.get(r.patient_id, "unknown"),
                "error_count": len(r.errors),
                "expected_warning_count": len(r.expected_warnings),
                "other_warning_count": len(r.other_warnings),
                "severity_histogram_json": json.dumps(r.severity_counts),
                "errors_json": json.dumps([
                    {"severity": e.severity, "code": e.code, "location": e.location,
                     "diagnostics": e.diagnostics[:200]}
                    for e in r.errors
                ]),
            })

    total_errors = sum(len(r.errors) for r in results)
    total_expected = sum(len(r.expected_warnings) for r in results)
    total_other = sum(len(r.other_warnings) for r in results)
    all_sev: Counter = Counter()
    for r in results:
        all_sev.update(r.severity_counts)

    summary = {
        "total_bundles": len(results),
        "total_non_allowlisted_errors": total_errors,
        "total_expected_warnings": total_expected,
        "total_other_warnings": total_other,
        "severity_histogram": dict(all_sev),
        "csv_path": str(results_csv),
    }
    return summary, results_csv


def _write_pydantic_report(
    pydantic_summary: dict,
    bundles_dir: Path,
    reports_dir: Path,
    pydantic_version: str,
) -> Path:
    """Write conformance_rates.md markdown report."""
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / "conformance_rates.md"

    # Read the CSV for per-tier breakdown
    csv_path = Path(pydantic_summary["csv_path"])
    tier_stats: dict[str, dict[str, int]] = {}
    error_counter: Counter = Counter()

    if csv_path.exists():
        import csv as csv_mod
        with csv_path.open(encoding="utf-8") as f:
            for row in csv_mod.DictReader(f):
                tier = row.get("tier", "unknown")
                passed = row.get("passed", "False") == "True"
                if tier not in tier_stats:
                    tier_stats[tier] = {"n": 0, "passed": 0, "failed": 0, "total_errors": 0}
                tier_stats[tier]["n"] += 1
                if passed:
                    tier_stats[tier]["passed"] += 1
                else:
                    tier_stats[tier]["failed"] += 1
                    errs = json.loads(row.get("errors_json", "[]"))
                    tier_stats[tier]["total_errors"] += len(errs)
                    for e in errs:
                        # Extract error pattern (first 60 chars)
                        error_counter[e[:60]] += 1

    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    total = pydantic_summary.get("total", 0)
    passed = pydantic_summary.get("passed", 0)
    failed = pydantic_summary.get("failed", 0)

    lines = [
        "# FHIR R4B Pydantic Conformance Report",
        f"",
        f"Generated: {timestamp}",
        f"Validator: fhir.resources {pydantic_version} (Pydantic R4B)",
        f"",
        f"## Summary",
        f"",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total bundles | {total} |",
        f"| Passed | {passed} |",
        f"| Failed | {failed} |",
        f"| Pass rate | {100 * passed / total:.1f}% |" if total > 0 else "| Pass rate | N/A |",
        f"",
        f"## Per-tier breakdown",
        f"",
        f"| Tier | N | Passed | Failed | Pass rate | Total errors |",
        f"|------|---|--------|--------|-----------|--------------|",
    ]
    for tier, stats in sorted(tier_stats.items()):
        n = stats["n"]
        p = stats["passed"]
        fa = stats["failed"]
        rate = f"{100 * p / n:.1f}%" if n > 0 else "N/A"
        lines.append(f"| {tier} | {n} | {p} | {fa} | {rate} | {stats['total_errors']} |")

    if error_counter:
        lines += [
            f"",
            f"## Top-10 error patterns",
            f"",
            f"| Count | Pattern |",
            f"|-------|---------|",
        ]
        for pat, cnt in error_counter.most_common(10):
            lines.append(f"| {cnt} | `{pat}` |")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Pydantic report written to {report_path}")
    return report_path


def _write_hl7_report(
    hl7_summary: dict,
    reports_dir: Path,
    jar_sha_path: Path,
) -> Path:
    """Write hl7_validator_summary.md markdown report."""
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / "hl7_validator_summary.md"

    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # Read jar SHA pin
    jar_sha = "(not installed)"
    if jar_sha_path.exists():
        for line in jar_sha_path.read_text(encoding="utf-8").splitlines():
            if line and not line.startswith("#"):
                jar_sha = line.strip()
                break

    sev_hist = hl7_summary.get("severity_histogram", {})
    sev_rows = "\n".join(
        f"| {sev} | {cnt} |" for sev, cnt in sorted(sev_hist.items())
    )

    lines = [
        "# HL7 Official Validator Summary",
        f"",
        f"Generated: {timestamp}",
        f"Validator: HL7 FHIR Validator (validator_cli.jar) v6.5.18",
        f"JAR SHA-256: `{jar_sha}`",
        f"FHIR version: 4.3.0 (R4B)",
        f"",
        f"## Summary",
        f"",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total bundles | {hl7_summary.get('total_bundles', 0)} |",
        f"| Non-allowlisted errors | {hl7_summary.get('total_non_allowlisted_errors', 0)} |",
        f"| Expected (allowlisted) warnings | {hl7_summary.get('total_expected_warnings', 0)} |",
        f"| Other warnings/info | {hl7_summary.get('total_other_warnings', 0)} |",
        f"",
        f"## Severity histogram",
        f"",
        f"| Severity | Count |",
        f"|----------|-------|",
        sev_rows if sev_rows else "| (none) | 0 |",
    ]

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"HL7 report written to {report_path}")
    return report_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bundles",
        required=True,
        type=Path,
        help="Directory of FHIR bundle JSON files",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        dest="output_dir",
        help="Directory for CSV output files",
    )
    parser.add_argument(
        "--reports-dir",
        required=True,
        type=Path,
        dest="reports_dir",
        help="Directory for Markdown report files",
    )
    parser.add_argument(
        "--skip-hl7",
        action="store_true",
        dest="skip_hl7",
        help="Skip HL7 jar validation; run Pydantic only",
    )
    parser.add_argument(
        "--enable-tx-server",
        action="store_true",
        dest="enable_tx_server",
        help=(
            "Allow the HL7 validator to contact tx.fhir.org. Default is offline "
            "(local terminology packages only) which is materially faster and "
            "still validates display-names and code-system membership against "
            "the locally bundled R4B + terminology packages."
        ),
    )
    args = parser.parse_args(argv)

    # Step 1: verify setup
    rc = _check_setup(args.skip_hl7)
    if rc != 0:
        return rc

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.reports_dir.mkdir(parents=True, exist_ok=True)

    # Step 2: Pydantic validator
    print("Running Pydantic R4B validator...")
    pydantic_summary = _run_pydantic_phase(args.bundles, args.output_dir)

    try:
        import fhir.resources as fr_pkg
        pydantic_version = getattr(fr_pkg, "__version__", "unknown")
    except Exception:
        pydantic_version = "unknown"

    _write_pydantic_report(pydantic_summary, args.bundles, args.reports_dir, pydantic_version)

    pydantic_ok = pydantic_summary.get("failed", 0) == 0

    hl7_ok = True
    # Step 3: HL7 validator (optional)
    if not args.skip_hl7:
        print("Running HL7 official validator...")
        allowlist_path = _REPO_ROOT / "mh_integration" / "expected_warnings.json"
        hl7_summary, _ = _run_hl7_phase(
            args.bundles,
            args.output_dir,
            allowlist_path,
            disable_tx_server=not args.enable_tx_server,
        )

        jar_sha_path = _REPO_ROOT / "tools" / "hl7-validator" / "validator_cli.sha256"
        _write_hl7_report(hl7_summary, args.reports_dir, jar_sha_path)

        hl7_ok = hl7_summary.get("total_non_allowlisted_errors", 0) == 0
    else:
        print("Skipping HL7 validation (--skip-hl7 set)")

    if pydantic_ok and hl7_ok:
        print("All validation checks passed.")
        return 0

    if not pydantic_ok:
        print(
            f"Pydantic validation: {pydantic_summary['failed']} bundles failed.",
            file=sys.stderr,
        )
    if not hl7_ok:
        print("HL7 validation: non-allowlisted errors found.", file=sys.stderr)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
