"""Python wrapper around the HL7 official Java FHIR Validator (validator_cli.jar).

Runs the jar in batch mode or per-bundle, parses OperationOutcome JSON output,
applies an allowlist to separate expected from unexpected issues.

Usage:
  from mh_integration.hl7_validator import HL7Validator, HL7Issue, HL7ValidationResult
  v = HL7Validator(jar_path=Path("tools/hl7-validator/validator_cli.jar"),
                   jre_path=Path("tools/jre"),
                   allowlist_path=Path("mh_integration/expected_warnings.json"))
  results = v.validate_directory(Path("data/fhir_bundles"), Path("results/hl7_validator_raw"))
"""
from __future__ import annotations

import json
import logging
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class HL7Issue:
    severity: str       # 'fatal' | 'error' | 'warning' | 'information'
    code: str           # FHIR issue code, e.g. 'code-unknown', 'structure'
    location: str       # FHIR path like 'Bundle.entry[3].resource.code.coding[0]'
    diagnostics: str
    expression: list[str] = field(default_factory=list)


@dataclass
class HL7ValidationResult:
    patient_id: str
    severity_counts: dict[str, int]         # severity -> count
    errors: list[HL7Issue]                  # non-allowlisted ERROR/FATAL only
    expected_warnings: list[HL7Issue]       # allowlisted issues
    other_warnings: list[HL7Issue]          # non-allowlisted WARNING/INFORMATION
    raw_output_path: Path


def _resolve_java_exe(jre_path: Path) -> Path:
    """Return the path to the java executable under jre_path/bin/."""
    bin_dir = jre_path / "bin"
    if sys.platform.startswith("win"):
        java_exe = bin_dir / "java.exe"
    else:
        java_exe = bin_dir / "java"
    return java_exe.resolve()


def _load_allowlist(allowlist_path: Path) -> list[dict]:
    """Load the allowlist JSON; return empty list if path is None or missing."""
    if allowlist_path is None or not allowlist_path.exists():
        logger.info("_load_allowlist: no allowlist at %s; using empty list", allowlist_path)
        return []
    raw = json.loads(allowlist_path.read_text(encoding="utf-8"))
    # Filter out meta/comment entries
    return [e for e in raw if isinstance(e, dict) and "issue_code" in e]


def _is_allowlisted(issue: HL7Issue, allowlist: list[dict]) -> bool:
    """Return True if issue matches any allowlist entry.

    An issue is allowlisted if its code matches issue_code AND its
    diagnostics or location contains url_substring.
    """
    for entry in allowlist:
        if issue.code != entry.get("issue_code", ""):
            continue
        url_sub = entry.get("url_substring", "")
        if url_sub and (url_sub in issue.diagnostics or url_sub in issue.location):
            logger.debug(
                "_is_allowlisted: matched entry code=%s url_substring=%s", issue.code, url_sub
            )
            return True
    return False


def _parse_operation_outcome(
    outcome_json: dict,
    patient_id: str,
    raw_output_path: Path,
    allowlist: list[dict],
) -> HL7ValidationResult:
    """Parse a single OperationOutcome dict into an HL7ValidationResult."""
    severity_counts: dict[str, int] = {}
    errors: list[HL7Issue] = []
    expected_warnings: list[HL7Issue] = []
    other_warnings: list[HL7Issue] = []

    issues_raw = outcome_json.get("issue", []) or []
    for iss in issues_raw:
        if not isinstance(iss, dict):
            continue
        severity = iss.get("severity", "information").lower()
        code = iss.get("code", "")
        # The OperationOutcome spec places the human-readable message in
        # `details.text`. The validator also sometimes uses `diagnostics` for
        # a technical hint. Prefer details.text; fall back to diagnostics.
        details = iss.get("details") or {}
        details_text = details.get("text", "") if isinstance(details, dict) else ""
        diagnostics_raw = iss.get("diagnostics", "")
        diagnostics = details_text or diagnostics_raw
        expression = iss.get("expression", []) or []
        if not isinstance(expression, list):
            expression = [str(expression)]
        location = expression[0] if expression else iss.get("location", "")

        issue = HL7Issue(
            severity=severity,
            code=code,
            location=location,
            diagnostics=diagnostics,
            expression=expression,
        )

        severity_counts[severity] = severity_counts.get(severity, 0) + 1

        if severity in ("fatal", "error"):
            if _is_allowlisted(issue, allowlist):
                expected_warnings.append(issue)
            else:
                errors.append(issue)
        else:
            # warning / information
            if _is_allowlisted(issue, allowlist):
                expected_warnings.append(issue)
            else:
                other_warnings.append(issue)

    logger.info(
        "_parse_operation_outcome: patient=%s severity_counts=%s errors=%d expected=%d other=%d",
        patient_id,
        severity_counts,
        len(errors),
        len(expected_warnings),
        len(other_warnings),
    )
    return HL7ValidationResult(
        patient_id=patient_id,
        severity_counts=severity_counts,
        errors=errors,
        expected_warnings=expected_warnings,
        other_warnings=other_warnings,
        raw_output_path=raw_output_path,
    )


class HL7Validator:
    """Wrapper around the HL7 official FHIR Validator CLI jar.

    Parameters
    ----------
    jar_path:
        Path to validator_cli.jar. Must exist before calling validate_*.
    jre_path:
        Path to a JRE root (i.e. tools/jre or tools/jre-<version>).
        The executable is expected at jre_path/bin/java[.exe].
    allowlist_path:
        Optional path to expected_warnings.json allowlist.
    fhir_version:
        FHIR version string to pass to -version flag. Default '4.3.0' (R4B).
    """

    def __init__(
        self,
        jar_path: Path,
        jre_path: Path,
        allowlist_path: Path | None = None,
        fhir_version: str = "4.3.0",
    ) -> None:
        self._jar_path = Path(jar_path)
        self._jre_path = Path(jre_path)
        self._allowlist_path = Path(allowlist_path) if allowlist_path is not None else None
        self._fhir_version = fhir_version
        self._allowlist = _load_allowlist(self._allowlist_path) if self._allowlist_path else []
        logger.info(
            "HL7Validator: jar=%s jre=%s fhir_version=%s allowlist_entries=%d",
            self._jar_path,
            self._jre_path,
            self._fhir_version,
            len(self._allowlist),
        )

    def _java_exe(self) -> Path:
        return _resolve_java_exe(self._jre_path)

    def _check_jar(self) -> None:
        if not self._jar_path.exists():
            raise RuntimeError(
                f"HL7 validator jar not found at {self._jar_path}. "
                "Run scripts/setup_hl7_validator.sh first."
            )

    def validate_directory(
        self,
        bundles_dir: Path,
        output_dir: Path,
        disable_tx_server: bool = False,
        chunk_size: int = 25,
    ) -> list[HL7ValidationResult]:
        """Run jar in chunked batch mode over every *.json in bundles_dir.

        Strategy: split inputs into chunks of `chunk_size` bundles. For each chunk,
        pass all bundle paths to the validator jar in one JVM invocation. The
        validator writes a single FHIR Bundle (type=collection) where each entry
        is an OperationOutcome for the corresponding input file, in input order.
        We split the chunk's combined Bundle into one OperationOutcome JSON file
        per input and write each to `output_dir/<patient_id>.json`.

        Why chunked: a single JVM holding 200 OperationOutcomes for ~40MB-each
        Synthea bundles drives memory north of 8GB and slows validation roughly
        linearly per bundle (likely GC pressure). Chunks of 25 stay in the
        ~2-3GB working-set band and keep per-bundle wall time near the
        steady-state minimum (~4-5s per Synthea-sized bundle).

        Parameters
        ----------
        disable_tx_server:
            Pass `-tx n/a` to the validator. The validator still validates against
            the locally bundled FHIR R4B + terminology packages (display-name
            mismatches and code-system membership are still flagged), but it does
            not call out to tx.fhir.org. Materially faster; trade-off is that less
            recent terminology updates are not seen.
        chunk_size:
            Bundles per JVM invocation. Default 25. Set to 0 (or len(inputs)) for
            single-JVM mode if you have plenty of RAM and want to avoid the
            per-chunk JVM-startup overhead.
        """
        self._check_jar()
        output_dir.mkdir(parents=True, exist_ok=True)

        bundle_files = sorted(
            p for p in bundles_dir.glob("*.json")
            if not p.stem.endswith("_regimen_index") and p.stem != "_regimen_index"
        )
        logger.info(
            "validate_directory: found %d bundle files in %s (chunked, chunk_size=%d)",
            len(bundle_files),
            bundles_dir,
            chunk_size,
        )
        if not bundle_files:
            return []

        effective_chunk = chunk_size if chunk_size > 0 else len(bundle_files)
        chunks = [
            bundle_files[i : i + effective_chunk]
            for i in range(0, len(bundle_files), effective_chunk)
        ]
        logger.info(
            "validate_directory: split into %d chunks (chunk_size=%d, total=%d)",
            len(chunks),
            effective_chunk,
            len(bundle_files),
        )

        all_results: list[HL7ValidationResult] = []
        for chunk_idx, chunk in enumerate(chunks):
            print(
                f"  [hl7 chunk {chunk_idx + 1}/{len(chunks)}] "
                f"validating {len(chunk)} bundles "
                f"({chunk[0].stem[:12]}.. -> {chunk[-1].stem[:12]}..)",
                flush=True,
            )
            chunk_results = self._validate_chunk(
                chunk,
                output_dir,
                disable_tx_server=disable_tx_server,
                chunk_idx=chunk_idx,
            )
            all_results.extend(chunk_results)

        return all_results

    def _validate_chunk(
        self,
        bundle_files: list[Path],
        output_dir: Path,
        *,
        disable_tx_server: bool,
        chunk_idx: int,
    ) -> list[HL7ValidationResult]:
        """Run the jar on one chunk of bundle files; return per-bundle results."""
        combined_path = output_dir.parent / f"hl7_validator_combined_chunk_{chunk_idx:03d}.json"

        java_exe = self._java_exe()
        cmd = [str(java_exe), "-jar", str(self._jar_path)]
        cmd.extend(str(p) for p in bundle_files)
        cmd.extend([
            "-version", self._fhir_version,
            "-output", str(combined_path),
            "-output-style", "json",
        ])
        if disable_tx_server:
            cmd.extend(["-tx", "n/a"])

        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        logger.info(
            "_validate_chunk: chunk %d returncode=%d stderr_excerpt=%r",
            chunk_idx,
            proc.returncode,
            (proc.stderr or "")[:200],
        )

        if not combined_path.exists():
            logger.warning(
                "_validate_chunk: combined output %s missing; falling back to per-bundle",
                combined_path,
            )
            return [
                self.validate_bundle(bp, output_dir / f"{bp.stem}.json")
                for bp in bundle_files
            ]

        try:
            combined = json.loads(combined_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            logger.error("_validate_chunk: chunk %d JSON parse failed: %s", chunk_idx, exc)
            return [
                self.validate_bundle(bp, output_dir / f"{bp.stem}.json")
                for bp in bundle_files
            ]

        entries = combined.get("entry") if isinstance(combined, dict) else None
        # When the combined output contains a SINGLE entry (e.g. only one bundle
        # was passed), the validator may emit it as a bare OperationOutcome.
        if isinstance(combined, dict) and combined.get("resourceType") == "OperationOutcome" and len(bundle_files) == 1:
            patient_id = bundle_files[0].stem
            per_bundle_path = output_dir / f"{patient_id}.json"
            per_bundle_path.write_text(json.dumps(combined, indent=2), encoding="utf-8")
            return [_parse_operation_outcome(combined, patient_id, per_bundle_path, self._allowlist)]

        if not isinstance(entries, list) or len(entries) != len(bundle_files):
            logger.warning(
                "_validate_chunk: chunk %d has %s entries vs %d inputs; falling back",
                chunk_idx,
                "no" if entries is None else str(len(entries)),
                len(bundle_files),
            )
            return [
                self.validate_bundle(bp, output_dir / f"{bp.stem}.json")
                for bp in bundle_files
            ]

        results: list[HL7ValidationResult] = []
        for bundle_path, entry in zip(bundle_files, entries):
            patient_id = bundle_path.stem
            outcome_json = entry.get("resource") if isinstance(entry, dict) else None
            per_bundle_path = output_dir / f"{patient_id}.json"
            if isinstance(outcome_json, dict):
                per_bundle_path.write_text(json.dumps(outcome_json, indent=2), encoding="utf-8")
                results.append(
                    _parse_operation_outcome(
                        outcome_json, patient_id, per_bundle_path, self._allowlist
                    )
                )
            else:
                logger.warning(
                    "_validate_chunk: entry for %s has no OperationOutcome",
                    patient_id,
                )
                results.append(
                    HL7ValidationResult(
                        patient_id=patient_id,
                        severity_counts={"missing_outcome": 1},
                        errors=[
                            HL7Issue(
                                severity="error",
                                code="structure",
                                location="",
                                diagnostics=(
                                    f"Validator combined output missing OperationOutcome for {patient_id}"
                                ),
                            )
                        ],
                        expected_warnings=[],
                        other_warnings=[],
                        raw_output_path=per_bundle_path,
                    )
                )
        return results

    def validate_bundle(
        self,
        bundle_path: Path,
        output_path: Path,
    ) -> HL7ValidationResult:
        """Run the jar on a single bundle file.

        Writes raw OperationOutcome JSON to output_path.
        Returns a parsed HL7ValidationResult.
        """
        self._check_jar()
        patient_id = bundle_path.stem
        java_exe = self._java_exe()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            str(java_exe),
            "-jar", str(self._jar_path),
            str(bundle_path),
            "-version", self._fhir_version,
            "-output", str(output_path),
            "-output-style", "json",
        ]
        logger.info("validate_bundle: running command for %s", patient_id)

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )

        # The jar exits non-zero even on WARNING-only results; do not raise on non-zero.
        if proc.returncode not in (0, 1) and not output_path.exists():
            # Real failure: record stderr in output for debugging
            stderr_excerpt = (proc.stderr or "")[:500]
            logger.error(
                "validate_bundle: jar returned code %d for %s stderr=%r",
                proc.returncode,
                patient_id,
                stderr_excerpt,
            )
            debug_path = output_path.with_suffix(".stderr.txt")
            debug_path.write_text(
                f"exit_code={proc.returncode}\n--- stderr ---\n{proc.stderr or ''}\n",
                encoding="utf-8",
            )

        # Parse the OperationOutcome output
        if output_path.exists():
            try:
                outcome_json = json.loads(output_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                logger.error(
                    "validate_bundle: JSON parse error for %s: %s", patient_id, exc
                )
                stderr_excerpt = (proc.stderr or "")[:500]
                return HL7ValidationResult(
                    patient_id=patient_id,
                    severity_counts={"parse_error": 1},
                    errors=[
                        HL7Issue(
                            severity="error",
                            code="structure",
                            location="",
                            diagnostics=f"OperationOutcome JSON parse error: {exc}. stderr: {stderr_excerpt}",
                        )
                    ],
                    expected_warnings=[],
                    other_warnings=[],
                    raw_output_path=output_path,
                )
        else:
            # No output file produced
            stderr_excerpt = (proc.stderr or "")[:500]
            logger.warning(
                "validate_bundle: no output file for %s (exit=%d)", patient_id, proc.returncode
            )
            return HL7ValidationResult(
                patient_id=patient_id,
                severity_counts={"no_output": 1},
                errors=[
                    HL7Issue(
                        severity="error",
                        code="structure",
                        location="",
                        diagnostics=f"No output produced by validator (exit={proc.returncode}). stderr: {stderr_excerpt}",
                    )
                ],
                expected_warnings=[],
                other_warnings=[],
                raw_output_path=output_path,
            )

        return _parse_operation_outcome(outcome_json, patient_id, output_path, self._allowlist)
