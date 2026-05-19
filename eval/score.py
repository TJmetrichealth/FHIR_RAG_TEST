"""Scoring module for the FHIR-RAG evaluation.

Reads raw JSONL traces from results/raw/{a,b,c}.jsonl, scores each answer
against the programmatic ground truth, and writes:

  results/scored.csv            -- one row per (system, question_id)
  results/recall_at_k.csv       -- aggregated recall@k per (system, family, type, tier, k)
  results/latency_tokens.csv    -- per-system latency and token summary stats

Scoring rules:
  - ISO date strings: parse both sides; exact match on YYYY-MM-DD.
  - Numeric (int / float): exact for int; 2% relative tolerance for float.
  - Boolean / yes-no / N/A: case-insensitive canonical match.
  - List / set: parse both sides; exact_match = set equality; partial = Jaccard.
  - Free-text: entity match via fidelity_audit logic (FHIR bundle lookup).
  - Recall@k (B/C only): top-k retrieved chunks contain patient's primary
    MedicationRequest or CarePlan resource (v1 heuristic).
  - System A recall@k: N/A (no resource-level retrieval semantics).

Hard rules:
  - NO LLM-as-judge.  All scoring is deterministic / programmatic.
  - Raw traces are never modified.
  - Uncertain rows are flagged; scorer never skips silently.

Usage (CLI):
  python -m eval.score
  python -m eval.score --raw-dir results/raw --questions questions/questions.jsonl \\
                       --output-dir results --bundles data/fhir_bundles

"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Project root (so this module works when invoked from any cwd)
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------
Record = dict[str, Any]

# ---------------------------------------------------------------------------
# ISO date regex — used to detect whether a string looks like a date
# ---------------------------------------------------------------------------
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Separators for list-type ground truth encoded as a plain string
_LIST_SEP_RE = re.compile(r"[,;]")

# ---------------------------------------------------------------------------
# Canonical boolean / yes-no / N/A forms
# ---------------------------------------------------------------------------
_BOOL_CANON: dict[str, str] = {
    "yes": "yes", "true": "yes", "1": "yes",
    "no": "no", "false": "no", "0": "no",
    "n/a": "n/a", "na": "n/a", "none": "n/a", "null": "n/a", "not applicable": "n/a",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_iso_date(v: Any) -> bool:
    """Return True if v is a YYYY-MM-DD string."""
    return isinstance(v, str) and bool(_DATE_RE.match(v.strip()))


def _parse_date_safe(s: str) -> str | None:
    """Normalise any ISO-ish date string to YYYY-MM-DD, or return None."""
    s = s.strip()
    try:
        return datetime.fromisoformat(s[:10]).strftime("%Y-%m-%d")
    except (ValueError, IndexError):
        return None


def _is_numeric(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _is_bool_like(v: Any) -> bool:
    """Return True for Python booleans or strings canonicalised as yes/no/N/A."""
    if isinstance(v, bool):
        return True
    if isinstance(v, str):
        return v.strip().lower() in _BOOL_CANON
    return False


def _canon_bool(v: Any) -> str | None:
    """Return canonical form ('yes'/'no'/'n/a') or None if not mappable."""
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, str):
        return _BOOL_CANON.get(v.strip().lower())
    return None


def _extract_answer_value(answer: str) -> str:
    """Extract the core value from an answer string.

    Strips trailing punctuation, 'The answer is:', 'Answer:', common
    preamble patterns that LLMs add even at temperature 0.
    """
    a = answer.strip()
    # Remove "Answer:" style preambles
    for prefix in ("answer:", "the answer is", "response:"):
        if a.lower().startswith(prefix):
            a = a[len(prefix):].strip()
    # Strip trailing period/comma
    a = a.rstrip(".,;:").strip()
    return a


def _parse_list_value(v: Any) -> set[str]:
    """Parse a list ground-truth value into a set of lower-cased strings.

    Accepts:
      - Python list / set → items as strings
      - JSON string encoding a list → parse then items
      - Comma/semicolon-separated string → split
    """
    if isinstance(v, (list, tuple, set)):
        return {str(x).strip().lower() for x in v if str(x).strip()}
    if isinstance(v, str):
        s = v.strip()
        # Try JSON parse first
        if s.startswith("["):
            try:
                items = json.loads(s)
                if isinstance(items, list):
                    return {str(x).strip().lower() for x in items if str(x).strip()}
            except json.JSONDecodeError:
                pass
        # Fall back to separator split
        parts = _LIST_SEP_RE.split(s)
        return {p.strip().lower() for p in parts if p.strip()}
    return set()


def _detect_gt_type(gt: Any) -> str:
    """Return one of: 'date', 'numeric', 'bool', 'list', 'free_text'."""
    if gt is None:
        return "free_text"
    if _is_iso_date(gt):
        return "date"
    # Check numeric before bool (Python bool IS a subclass of int)
    if _is_numeric(gt):
        return "numeric"
    if _is_bool_like(gt):
        return "bool"
    if isinstance(gt, (list, tuple, set)):
        return "list"
    if isinstance(gt, str):
        s = gt.strip()
        # JSON-encoded list?
        if s.startswith("["):
            try:
                parsed = json.loads(s)
                if isinstance(parsed, list):
                    return "list"
            except json.JSONDecodeError:
                pass
        # Comma/semicolon-separated multi-item?
        if _LIST_SEP_RE.search(s):
            parts = [p.strip() for p in _LIST_SEP_RE.split(s) if p.strip()]
            if len(parts) > 1:
                return "list"
        # Boolean / N/A string?
        if s.lower() in _BOOL_CANON:
            return "bool"
    return "free_text"


# ---------------------------------------------------------------------------
# Scoring functions — each returns (exact_match: bool, partial_credit: float,
#                                   flag: bool, flag_reason: str)
# ---------------------------------------------------------------------------

def _score_date(gt: str, answer: str) -> tuple[bool, float, bool, str]:
    gt_norm = _parse_date_safe(gt)
    if gt_norm is None:
        return False, 0.0, True, f"ground truth date unparseable: {gt!r}"

    # Find a date in the answer
    answer_clean = _extract_answer_value(answer)
    # Try the entire cleaned answer first
    ans_norm = _parse_date_safe(answer_clean)
    if ans_norm is None:
        # Hunt for a YYYY-MM-DD substring in the answer
        m = re.search(r"\d{4}-\d{2}-\d{2}", answer)
        if m:
            ans_norm = _parse_date_safe(m.group(0))
    if ans_norm is None:
        return False, 0.0, False, "no parseable date in answer"

    exact = gt_norm == ans_norm
    return exact, 1.0 if exact else 0.0, False, ""


def _score_numeric(gt: float | int, answer: str) -> tuple[bool, float, bool, str]:
    import math

    answer_clean = _extract_answer_value(answer)
    # Extract first number from the answer
    m = re.search(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?", answer_clean)
    if not m:
        return False, 0.0, False, "no number found in answer"
    try:
        ans_val = float(m.group(0))
    except (ValueError, OverflowError):
        return False, 0.0, True, f"number parse failed: {m.group(0)!r}"

    # Reject NaN / Inf — these can never match a finite ground truth.
    if not math.isfinite(ans_val):
        return False, 0.0, True, f"answer is non-finite: {m.group(0)!r}"

    gt_val = float(gt)
    if not math.isfinite(gt_val):
        return False, 0.0, True, f"ground truth is non-finite: {gt!r}"

    if isinstance(gt, int) and "." not in m.group(0):
        exact = int(ans_val) == int(gt)
        return exact, 1.0 if exact else 0.0, False, ""
    # Float: 2% relative tolerance (or 0.01 absolute floor)
    tol = max(0.01, 0.02 * abs(gt_val))
    exact = abs(ans_val - gt_val) <= tol
    partial = 1.0 if exact else 0.0
    return exact, partial, False, ""


def _score_bool(gt: Any, answer: str) -> tuple[bool, float, bool, str]:
    gt_canon = _canon_bool(gt)
    if gt_canon is None:
        return False, 0.0, True, f"ground truth bool not canonicalisable: {gt!r}"

    answer_clean = _extract_answer_value(answer).lower()
    ans_canon = _BOOL_CANON.get(answer_clean)
    if ans_canon is None:
        # Try to find a canonical token within the answer
        for token, canon in sorted(_BOOL_CANON.items(), key=lambda x: -len(x[0])):
            if token in answer_clean:
                ans_canon = canon
                break
    if ans_canon is None:
        return False, 0.0, False, f"answer not canonicalisable as bool: {answer_clean!r}"

    exact = gt_canon == ans_canon
    return exact, 1.0 if exact else 0.0, False, ""


def _score_list(gt: Any, answer: str) -> tuple[bool, float, bool, str]:
    gt_set = _parse_list_value(gt)
    if not gt_set:
        return False, 0.0, True, f"ground truth list is empty or unparseable: {gt!r}"

    answer_clean = _extract_answer_value(answer)
    ans_set = _parse_list_value(answer_clean)
    if not ans_set:
        return False, 0.0, False, "answer list is empty"

    intersection = gt_set & ans_set
    union = gt_set | ans_set
    partial = len(intersection) / len(union) if union else 0.0
    exact = gt_set == ans_set
    return exact, partial, False, ""


# ---------------------------------------------------------------------------
# Free-text scoring — entity match against FHIR bundle
# ---------------------------------------------------------------------------
# We re-use the fidelity_audit logic.  The scorer has access to the FHIR
# bundles directory; it extracts expected entities from the bundle for the
# patient in question, then counts how many appear in the answer text.
# This is deterministic and does NOT call any LLM.

def _load_bundle_gt(bundle_path: Path) -> dict[str, Any] | None:
    """Load and extract ground-truth entities from a FHIR bundle."""
    try:
        from narratives.fidelity_audit import _extract_ground_truth  # type: ignore[import]
        return _extract_ground_truth(bundle_path)
    except Exception:
        return None


def _expected_entities_for_question(
    bundle_gt: dict[str, Any],
    question_id: str,
) -> list[str]:
    """Return a list of entity strings expected to appear for this question.

    For free-text questions we return all medication names and a sample of
    administration dates from the bundle.  This gives a reasonable proxy for
    "does the answer contain entities grounded in this patient's FHIR data?"
    """
    entities: list[str] = []
    if not bundle_gt:
        return entities
    for comp in bundle_gt.get("components") or []:
        name = comp.get("medication_name") or ""
        if name:
            entities.append(name.lower())
        # Sample dates: first + last
        dates = comp.get("admin_dates") or []
        if dates:
            entities.append(dates[0])
            entities.append(dates[-1])
    tier_desc = bundle_gt.get("tier_description") or ""
    if tier_desc:
        entities.append(tier_desc.lower())
    return list(dict.fromkeys(e for e in entities if e))


def _score_free_text(
    gt: Any,
    answer: str,
    bundle_path: Path | None,
    question_id: str,
) -> tuple[bool, float, bool, str]:
    """Score a free-text answer using entity matching against the FHIR bundle."""
    if bundle_path is None or not bundle_path.exists():
        # No bundle available — fall back to substring match of gt in answer
        gt_str = str(gt).strip().lower()
        answer_lower = answer.lower()
        if gt_str and gt_str in answer_lower:
            return True, 1.0, False, "fallback: gt substring found in answer (no bundle)"
        return False, 0.0, True, "no bundle available for entity match"

    bundle_gt = _load_bundle_gt(bundle_path)
    if bundle_gt is None:
        return False, 0.0, True, "bundle parse failed"

    entities = _expected_entities_for_question(bundle_gt, question_id)
    if not entities:
        return False, 0.0, True, "no entities extractable from bundle"

    answer_lower = answer.lower()
    found = [e for e in entities if e.lower() in answer_lower]
    partial = len(found) / len(entities)
    exact = partial >= 1.0
    return exact, round(partial, 4), False, ""


# ---------------------------------------------------------------------------
# Master scorer
# ---------------------------------------------------------------------------

def score_row(
    record: Record,
    bundle_path: Path | None = None,
) -> Record:
    """Score a single raw harness record.

    Returns a flat dict suitable for one CSV row (scored.csv).
    All booleans are stored as Python bool; the CSV writer converts to True/False.
    """
    question_id: str = record.get("question_id", "")
    system: str = record.get("system", "")
    patient_id: str = record.get("patient_id", "")
    family: str = _infer_family(question_id)
    qtype: str = record.get("question_type", "")
    tier = record.get("tier")
    reference_date: str = record.get("reference_date") or ""
    gt = record.get("ground_truth")
    answer: str = record.get("answer") or ""
    retrieved: list = record.get("retrieved") or []
    tokens_in: int = record.get("tokens_in") or 0
    tokens_out: int = record.get("tokens_out") or 0
    latency_ms: float = float(record.get("latency_ms") or 0.0)
    extras: dict = record.get("extras") or {}

    # Error flag
    error_flag = answer == "ERROR" or bool(extras.get("error"))
    error_reason = str(extras.get("error") or "")

    # Default scoring values
    exact_match = False
    partial_credit = 0.0
    flag = False
    flag_reason = ""

    if error_flag:
        flag = True
        flag_reason = f"system error: {error_reason[:200]}"
    else:
        gt_type = _detect_gt_type(gt)
        if gt_type == "date":
            exact_match, partial_credit, flag, flag_reason = _score_date(str(gt), answer)
        elif gt_type == "numeric":
            exact_match, partial_credit, flag, flag_reason = _score_numeric(gt, answer)
        elif gt_type == "bool":
            exact_match, partial_credit, flag, flag_reason = _score_bool(gt, answer)
        elif gt_type == "list":
            exact_match, partial_credit, flag, flag_reason = _score_list(gt, answer)
        else:  # free_text
            exact_match, partial_credit, flag, flag_reason = _score_free_text(
                gt, answer, bundle_path, question_id
            )

    # Recall@k
    recall_at_1, recall_at_3, recall_at_5, recall_at_10 = _compute_recall(
        system=system,
        patient_id=patient_id,
        retrieved=retrieved,
        bundle_path=bundle_path,
    )

    return {
        "question_id": question_id,
        "system": system,
        "patient_id": patient_id,
        "family": family,
        "type": qtype,
        "tier": tier,
        "reference_date": reference_date,
        "ground_truth": json.dumps(gt) if isinstance(gt, (list, dict)) else str(gt) if gt is not None else "",
        "answer": answer[:500],  # truncate for CSV readability
        "exact_match": exact_match,
        "partial_credit": round(partial_credit, 4),
        "recall_at_1": recall_at_1,
        "recall_at_3": recall_at_3,
        "recall_at_5": recall_at_5,
        "recall_at_10": recall_at_10,
        "latency_ms": round(latency_ms, 2),
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "error_flag": error_flag,
        "error_reason": flag_reason if (error_flag or flag) else "",
        "near_miss_flag": flag and not error_flag,
    }


def _infer_family(question_id: str) -> str:
    """Infer PSP family from question id template prefix."""
    # question_id format: {patient_id}::{template_id}
    # template_id prefixes: tl.=temporal_lookup, tc.=temporal_comparison,
    #   rc.=regimen_compliance, ra.=regimen_aggregation, cr.=cross_resource
    parts = question_id.split("::", 1)
    if len(parts) < 2:
        return "unknown"
    tid = parts[1]
    prefix = tid.split(".", 1)[0] if "." in tid else tid
    mapping = {
        "tl": "temporal_lookup",
        "tc": "temporal_comparison",
        "rc": "regimen_compliance",
        "ra": "regimen_aggregation",
        "cr": "cross_resource",
    }
    return mapping.get(prefix, tid)


# ---------------------------------------------------------------------------
# Recall@k computation
# ---------------------------------------------------------------------------
# V1 heuristic: for Systems B and C, check whether any of the top-k retrieved
# chunk IDs contain the patient's primary MedicationRequest or CarePlan
# resource ID as a prefix.  Chunk ID format: {resourceType}_{resource_id}::chunk_{i}
# System A: narrative chunks — no resource-level IDs → always None (N/A).

def _primary_resource_ids(patient_id: str, bundle_path: Path | None) -> set[str]:
    """Return resource IDs that are considered 'relevant' for heuristic recall.

    V1: primary MedicationRequest (spec-req-*-primary) and specialty CarePlan
    (spec-cp-*) for the patient.  Falls back to patient_id prefix patterns
    if no bundle is available.
    """
    ids: set[str] = set()
    if bundle_path is None or not bundle_path.exists():
        # Best-effort: known naming convention without parsing the bundle
        short = patient_id[:8]
        ids.add(f"spec-req-{short}")  # prefix match used later
        ids.add(f"spec-cp-{short}")
        return ids

    try:
        data = json.loads(bundle_path.read_text(encoding="utf-8"))
    except Exception:
        return ids

    for entry in data.get("entry", []):
        r = entry.get("resource", {})
        rid = r.get("id", "")
        rt = r.get("resourceType", "")
        if rt == "CarePlan" and rid.startswith("spec-cp-"):
            ids.add(rid)
        if rt == "MedicationRequest" and rid.endswith("-primary"):
            ids.add(rid)
    return ids


def _chunk_contains_resource(chunk: object, resource_ids: set[str]) -> bool:
    """Return True if *chunk* references one of the given resource IDs.

    The harness's ``retrieved`` field is a list of dicts (per system answer
    contracts), each with a ``resource_id`` (B/C) or just metadata (A).
    For backwards compatibility we also accept a raw chunk-id string of the
    form ``{resourceType}_{resource_id}::chunk_{i}``.
    """
    # Dict form (current harness output)
    if isinstance(chunk, dict):
        resource_id = chunk.get("resource_id") or ""
        if not resource_id:
            return False
        if resource_id in resource_ids:
            return True
        for rid in resource_ids:
            if resource_id.startswith(rid) or rid.startswith(resource_id):
                return True
        return False

    # String form (legacy / chunk-id only)
    if not isinstance(chunk, str):
        return False
    base = chunk.split("::")[0] if "::" in chunk else chunk
    parts = base.split("_", 1)
    if len(parts) == 2:
        resource_id = parts[1]
        if resource_id in resource_ids:
            return True
        for rid in resource_ids:
            if resource_id.startswith(rid) or rid.startswith(resource_id):
                return True
    return False


def _compute_recall(
    system: str,
    patient_id: str,
    retrieved: list[str],
    bundle_path: Path | None,
) -> tuple[bool | None, bool | None, bool | None, bool | None]:
    """Compute recall@1, @3, @5, @10.

    Returns None for System A (no resource-level retrieval semantics).
    Returns bool for Systems B/C.
    """
    if system.lower() in ("a", "narrative", "narrative_rag"):
        return None, None, None, None

    resource_ids = _primary_resource_ids(patient_id, bundle_path)
    if not resource_ids:
        return None, None, None, None

    def _hit_at(k: int) -> bool:
        top_k = retrieved[:k]
        return any(_chunk_contains_resource(c, resource_ids) for c in top_k)

    r1 = _hit_at(1)
    r3 = _hit_at(3)
    r5 = _hit_at(5)
    r10 = _hit_at(10)
    return r1, r3, r5, r10


# ---------------------------------------------------------------------------
# Wilson score confidence interval (95%)
# ---------------------------------------------------------------------------

def _wilson_ci(n_success: int, n: int) -> tuple[float, float]:
    """95% Wilson score CI for a proportion."""
    if n == 0:
        return 0.0, 0.0
    z = 1.95996  # z_{0.025}
    p_hat = n_success / n
    denom = 1 + z * z / n
    centre = (p_hat + z * z / (2 * n)) / denom
    margin = (z * math.sqrt(p_hat * (1 - p_hat) / n + z * z / (4 * n * n))) / denom
    lo = max(0.0, centre - margin)
    hi = min(1.0, centre + margin)
    return round(lo, 4), round(hi, 4)


# ---------------------------------------------------------------------------
# CSV writers
# ---------------------------------------------------------------------------

_SCORED_COLS = [
    "question_id", "system", "patient_id", "family", "type", "tier",
    "reference_date", "ground_truth", "answer",
    "exact_match", "partial_credit",
    "recall_at_1", "recall_at_3", "recall_at_5", "recall_at_10",
    "latency_ms", "tokens_in", "tokens_out",
    "error_flag", "error_reason", "near_miss_flag",
]

_RECALL_COLS = [
    "system", "family", "type", "tier", "k",
    "n_questions", "n_hits", "recall_mean", "recall_ci_lo", "recall_ci_hi",
]

_LATENCY_COLS = [
    "system", "n_calls", "n_errors", "error_rate",
    "latency_mean_ms", "latency_p50_ms", "latency_p95_ms", "latency_p99_ms",
    "tokens_in_mean", "tokens_out_mean", "total_tokens",
    "exact_match_rate",
]


def _percentile(data: list[float], p: float) -> float:
    """Compute p-th percentile (0–100) using nearest-rank."""
    if not data:
        return 0.0
    sorted_d = sorted(data)
    idx = max(0, int(math.ceil(p / 100 * len(sorted_d))) - 1)
    return sorted_d[idx]


def write_scored_csv(rows: list[Record], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_SCORED_COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def write_recall_at_k_csv(rows: list[Record], output_path: Path) -> None:
    """Aggregate recall@k and write to CSV."""
    # Group by (system, family, type, tier, k)
    # Only rows where recall_at_k is not None (i.e. systems B/C)
    k_vals = [1, 3, 5, 10]
    k_field = {1: "recall_at_1", 3: "recall_at_3", 5: "recall_at_5", 10: "recall_at_10"}

    # Build grouped hits/counts
    groups: dict[tuple, dict[int, list[bool]]] = defaultdict(lambda: {k: [] for k in k_vals})
    for row in rows:
        key = (row["system"], row["family"], row["type"], str(row.get("tier") or ""))
        for k in k_vals:
            val = row[k_field[k]]
            if val is not None:  # None = N/A (System A)
                groups[key][k].append(bool(val))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_RECALL_COLS)
        w.writeheader()
        for (system, family, qtype, tier), k_hits in sorted(groups.items()):
            for k in k_vals:
                hits = k_hits[k]
                if not hits:
                    continue
                n = len(hits)
                n_hit = sum(hits)
                lo, hi = _wilson_ci(n_hit, n)
                w.writerow({
                    "system": system,
                    "family": family,
                    "type": qtype,
                    "tier": tier,
                    "k": k,
                    "n_questions": n,
                    "n_hits": n_hit,
                    "recall_mean": round(n_hit / n, 4),
                    "recall_ci_lo": lo,
                    "recall_ci_hi": hi,
                })


def write_latency_tokens_csv(rows: list[Record], output_path: Path) -> None:
    """Write per-system latency and token summary statistics."""
    by_system: dict[str, list[Record]] = defaultdict(list)
    for row in rows:
        by_system[row["system"]].append(row)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_LATENCY_COLS)
        w.writeheader()
        for system in sorted(by_system):
            sys_rows = by_system[system]
            n = len(sys_rows)
            n_errors = sum(1 for r in sys_rows if r["error_flag"])
            latencies = [r["latency_ms"] for r in sys_rows]
            tokens_in = [r["tokens_in"] for r in sys_rows]
            tokens_out = [r["tokens_out"] for r in sys_rows]
            n_exact = sum(1 for r in sys_rows if r["exact_match"] and not r["error_flag"])
            n_answered = n - n_errors
            w.writerow({
                "system": system,
                "n_calls": n,
                "n_errors": n_errors,
                "error_rate": round(n_errors / n, 4) if n else 0.0,
                "latency_mean_ms": round(sum(latencies) / n, 2) if n else 0.0,
                "latency_p50_ms": round(_percentile(latencies, 50), 2),
                "latency_p95_ms": round(_percentile(latencies, 95), 2),
                "latency_p99_ms": round(_percentile(latencies, 99), 2),
                "tokens_in_mean": round(sum(tokens_in) / n, 1) if n else 0.0,
                "tokens_out_mean": round(sum(tokens_out) / n, 1) if n else 0.0,
                "total_tokens": sum(tokens_in) + sum(tokens_out),
                "exact_match_rate": round(n_exact / n_answered, 4) if n_answered else 0.0,
            })


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_scoring(
    raw_dir: Path,
    questions_path: Path,
    output_dir: Path,
    bundles_dir: Path,
    system_names: list[str] | None = None,
) -> list[Record]:
    """Run scoring over all available raw JSONL files.

    Parameters
    ----------
    raw_dir : Path
        Directory containing {a,b,c}.jsonl (or other system names).
    questions_path : Path
        Path to questions.jsonl (used to fill any missing metadata fields).
    output_dir : Path
        Directory to write scored.csv, recall_at_k.csv, latency_tokens.csv.
    bundles_dir : Path
        Directory containing {patient_uuid}.json FHIR bundles.
    system_names : list[str] | None
        Which system files to score.  Defaults to ['a', 'b', 'c'].

    Returns
    -------
    list[Record]
        All scored rows (across all systems).
    """
    if system_names is None:
        system_names = ["a", "b", "c"]

    # Build a lookup from question_id → question row (for any missing metadata)
    q_lookup: dict[str, dict] = {}
    if questions_path.exists():
        with open(questions_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                q = json.loads(line)
                q_lookup[q["id"]] = q
    else:
        print(f"[score] WARNING: questions file not found: {questions_path}", file=sys.stderr)

    all_scored: list[Record] = []

    for sname in system_names:
        raw_path = raw_dir / f"{sname}.jsonl"
        if not raw_path.exists():
            print(f"[score] WARNING: {raw_path} not found — skipping system {sname!r}",
                  file=sys.stderr)
            continue

        print(f"[score] Scoring {raw_path} ...", file=sys.stderr)
        n_scored = 0
        n_errors = 0
        n_near_miss = 0

        with open(raw_path, encoding="utf-8") as fh:
            for line_no, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    print(f"[score] SKIP line {line_no} in {raw_path}: JSON error: {exc}",
                          file=sys.stderr)
                    continue

                # Merge any missing metadata from question bank
                qid = record.get("question_id", "")
                if qid in q_lookup:
                    q_row = q_lookup[qid]
                    if not record.get("question_type"):
                        record["question_type"] = q_row.get("type", "")
                    if record.get("tier") is None:
                        record["tier"] = q_row.get("tier")
                    if not record.get("ground_truth"):
                        record["ground_truth"] = q_row.get("ground_truth")

                # Bundle path for entity matching and recall@k
                pid = record.get("patient_id", "")
                bundle_path = (bundles_dir / f"{pid}.json") if pid else None

                scored = score_row(record, bundle_path=bundle_path)
                all_scored.append(scored)
                n_scored += 1
                if scored["error_flag"]:
                    n_errors += 1
                if scored["near_miss_flag"]:
                    n_near_miss += 1

        print(
            f"[score]   {sname}: {n_scored} rows, {n_errors} errors, "
            f"{n_near_miss} near-miss flags",
            file=sys.stderr,
        )

    if not all_scored:
        print("[score] WARNING: no rows scored.", file=sys.stderr)
        return all_scored

    # Write outputs
    output_dir.mkdir(parents=True, exist_ok=True)
    scored_path = output_dir / "scored.csv"
    recall_path = output_dir / "recall_at_k.csv"
    latency_path = output_dir / "latency_tokens.csv"

    write_scored_csv(all_scored, scored_path)
    write_recall_at_k_csv(all_scored, recall_path)
    write_latency_tokens_csv(all_scored, latency_path)

    print(f"[score] Wrote: {scored_path}", file=sys.stderr)
    print(f"[score] Wrote: {recall_path}", file=sys.stderr)
    print(f"[score] Wrote: {latency_path}", file=sys.stderr)

    # Summary report to stdout
    _print_summary(all_scored)

    return all_scored


def _print_summary(rows: list[Record]) -> None:
    """Print one-page evaluation summary to stdout."""
    by_system: dict[str, list[Record]] = defaultdict(list)
    for r in rows:
        by_system[r["system"]].append(r)

    n_patients = len({r["patient_id"] for r in rows})
    n_calls = len(rows)
    n_errors = sum(1 for r in rows if r["error_flag"])

    print("\n" + "=" * 72)
    print("FHIR-RAG EVALUATION SUMMARY")
    print("=" * 72)
    print(f"  n_questions (per system): {n_calls // max(len(by_system), 1)}")
    print(f"  n_patients: {n_patients}")
    print(f"  n_systems:  {len(by_system)}")
    print(f"  n_calls total: {n_calls}")
    print(f"  n_errors total: {n_errors}")
    print(f"  error_rate total: {n_errors/n_calls:.1%}" if n_calls else "")
    total_tokens_in = sum(r["tokens_in"] for r in rows)
    total_tokens_out = sum(r["tokens_out"] for r in rows)
    print(f"  total_tokens: {total_tokens_in + total_tokens_out:,} "
          f"(in={total_tokens_in:,} out={total_tokens_out:,})")
    # Cost estimate: Groq qwen-3-32b free tier pricing ~$0 (paid tier ~$0.29/$1.20 per 1M)
    cost_lo = (total_tokens_in / 1e6 * 0.29) + (total_tokens_out / 1e6 * 1.20)
    print(f"  cost_estimate (paid tier qwen-3-32b): ${cost_lo:.4f} USD")
    print()
    print(f"  {'System':<12} {'n_rows':>8} {'n_err':>7} {'exact_match':>12} {'partial_mean':>13}")
    print(f"  {'-'*12} {'-'*8} {'-'*7} {'-'*12} {'-'*13}")
    for sname in sorted(by_system):
        sys_rows = by_system[sname]
        n = len(sys_rows)
        n_err = sum(1 for r in sys_rows if r["error_flag"])
        n_answered = n - n_err
        n_exact = sum(1 for r in sys_rows if r["exact_match"] and not r["error_flag"])
        partial_vals = [r["partial_credit"] for r in sys_rows if not r["error_flag"]]
        partial_mean = sum(partial_vals) / len(partial_vals) if partial_vals else 0.0
        em_rate = n_exact / n_answered if n_answered else float("nan")
        print(f"  {sname:<12} {n:>8} {n_err:>7} {em_rate:>12.1%} {partial_mean:>13.4f}")
    print("=" * 72 + "\n")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Score raw FHIR-RAG evaluation results against ground truth.",
    )
    p.add_argument(
        "--raw-dir",
        type=Path,
        default=_PROJECT_ROOT / "results" / "raw",
        help="Directory containing {a,b,c}.jsonl (default: results/raw/)",
    )
    p.add_argument(
        "--questions",
        type=Path,
        default=_PROJECT_ROOT / "questions" / "questions.jsonl",
        help="Path to questions.jsonl (default: questions/questions.jsonl)",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=_PROJECT_ROOT / "results",
        help="Directory for output CSVs (default: results/)",
    )
    p.add_argument(
        "--bundles",
        type=Path,
        default=_PROJECT_ROOT / "data" / "fhir_bundles",
        help="FHIR bundles directory (default: data/fhir_bundles/)",
    )
    p.add_argument(
        "--systems",
        nargs="*",
        default=["a", "b", "c"],
        metavar="NAME",
        help="Which system files to score (default: a b c)",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run_scoring(
        raw_dir=args.raw_dir,
        questions_path=args.questions,
        output_dir=args.output_dir,
        bundles_dir=args.bundles,
        system_names=args.systems,
    )
