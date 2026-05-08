"""Eval harness skeleton — runs any System A/B/C over a question set.

Usage (CLI)::

    python -m eval.harness \\
        --system stub \\
        --questions questions/questions.jsonl \\
        --patients 014abeea-627d-f33c-834c-e2a6605046ee \\
        --output results/raw/stub.jsonl \\
        --limit 3

Or import and call ``run_harness()`` directly from another script.

Design:
- Loads the system by name from the ``SYSTEM_REGISTRY`` dict.
- Iterates questions in stable, deterministic order (sorted by ``id`` field).
- Calls ``system.answer(question, patient_id)`` for each question whose
  patient_id is in the requested subset.
- Writes one JSON line per question to the output JSONL file.
- Does NOT score answers — scoring is the evaluator's job.
- Fully reproducible: same seeds, same ordering, same cache keys on every run.
- A partial run is safe to resume: already-written IDs are skipped on restart.
"""
from __future__ import annotations

import argparse
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from eval.config import QUESTIONS_PATH, RESULTS_RAW_DIR
from systems.base import BaseSystem, SystemResponse


# ---------------------------------------------------------------------------
# System registry
# STUB is always available. Real systems A/B/C will be imported lazily when
# they exist so this module stays importable before Week 2 implementations.
# ---------------------------------------------------------------------------

def _load_system(name: str) -> BaseSystem:
    """Resolve *name* to a system instance.

    Add real systems here as they are implemented in T2.2–T2.4.
    """
    name_lower = name.lower()

    if name_lower == "stub":
        return _StubSystem()

    # --- Lazy imports so harness is importable before systems exist ---
    if name_lower in ("a", "narrative", "narrative_rag"):
        from systems.narrative_rag import NarrativeRAG  # type: ignore[import]
        return NarrativeRAG()

    if name_lower in ("b", "naive", "structured_rag_naive", "structured_naive"):
        from systems.structured_rag_naive import StructuredRAGNaive  # type: ignore[import]
        return StructuredRAGNaive()

    if name_lower in ("c", "aware", "structured_rag_aware", "structured_aware"):
        from systems.structured_rag_aware import StructuredRAGAware  # type: ignore[import]
        return StructuredRAGAware()

    raise ValueError(
        f"Unknown system: {name!r}. "
        "Valid names: stub, a/narrative, b/naive, c/aware"
    )


# ---------------------------------------------------------------------------
# Stub system — always available for harness smoke-tests
# ---------------------------------------------------------------------------

class _StubSystem:
    """Trivial stub that always returns 'N/A' with empty retrieval.

    Used to verify the harness plumbing before any real system is built.
    """

    def answer(self, question: str, patient_id: str) -> SystemResponse:
        return SystemResponse(
            answer="N/A",
            retrieved=[],
            tokens_in=0,
            tokens_out=0,
            latency_ms=0.0,
        )


# ---------------------------------------------------------------------------
# Question loading
# ---------------------------------------------------------------------------

def load_questions(
    questions_path: Path,
    patient_ids: list[str] | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Load and filter questions from a JSONL file.

    Parameters
    ----------
    questions_path:
        Path to questions.jsonl.
    patient_ids:
        If provided, only questions whose ``patient_id`` is in this list
        are returned.
    limit:
        If provided, return at most this many questions (after patient filter).

    Returns
    -------
    list[dict]
        Sorted by ``id`` for deterministic ordering.
    """
    questions: list[dict[str, Any]] = []
    with open(questions_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            q = json.loads(line)
            if patient_ids is None or q["patient_id"] in patient_ids:
                questions.append(q)

    # Sort by id for deterministic, reproducible ordering
    questions.sort(key=lambda q: q["id"])

    if limit is not None:
        questions = questions[:limit]
    return questions


# ---------------------------------------------------------------------------
# Core runner
# ---------------------------------------------------------------------------

def _answer_one(
    system: BaseSystem,
    system_name: str,
    q: dict[str, Any],
) -> dict[str, Any]:
    """Run a single system.answer() call and build the result record.

    Pure function — safe to call from worker threads. Errors are captured
    into the record (never propagate) so a single bad question does not
    abort the run.
    """
    t0 = time.perf_counter()
    try:
        resp: SystemResponse = system.answer(q["question"], q["patient_id"])
    except Exception as exc:  # noqa: BLE001
        resp = SystemResponse(
            answer="ERROR",
            retrieved=[],
            tokens_in=0,
            tokens_out=0,
            latency_ms=(time.perf_counter() - t0) * 1000.0,
            extras={"error": str(exc)},
        )
    return {
        "question_id": q["id"],
        "patient_id": q["patient_id"],
        "question": q["question"],
        "question_type": q["type"],
        "tier": q.get("tier"),
        "reference_date": q.get("reference_date"),
        "ground_truth": q.get("ground_truth"),
        "system": system_name,
        "answer": resp.answer,
        "retrieved": resp.retrieved,
        "tokens_in": resp.tokens_in,
        "tokens_out": resp.tokens_out,
        "latency_ms": resp.latency_ms,
        "extras": resp.extras,
    }


def run_harness(
    system: BaseSystem,
    system_name: str,
    questions_path: Path = QUESTIONS_PATH,
    patient_ids: list[str] | None = None,
    output_path: Path | None = None,
    limit: int | None = None,
    *,
    resume: bool = True,
    concurrency: int = 1,
) -> list[dict[str, Any]]:
    """Run *system* over *questions_path* and write results to *output_path*.

    Parameters
    ----------
    system:
        An object satisfying the BaseSystem protocol.
    system_name:
        Short label written into every result record (e.g. ``"stub"``).
    questions_path:
        Path to the JSONL question bank.
    patient_ids:
        Subset of patients to evaluate. ``None`` = all patients.
    output_path:
        Destination JSONL file. Defaults to
        ``results/raw/<system_name>.jsonl``.
    limit:
        Cap on number of questions (after patient filter). Useful for smoke
        tests.
    resume:
        If True and *output_path* already exists, skip question IDs that
        are already present in the file.
    concurrency:
        Number of in-flight ``system.answer`` calls. ``1`` (default) keeps
        the original synchronous behaviour. ``>=2`` uses a ThreadPoolExecutor
        so multiple Groq calls overlap. Output ordering is no longer
        deterministic, but the question_id-keyed dedup on resume makes order
        irrelevant.

    Returns
    -------
    list[dict]
        All result records produced by THIS invocation (does not include
        previously-cached records loaded from disk).
    """
    if not isinstance(system, BaseSystem):
        raise TypeError(
            f"{system!r} does not satisfy the BaseSystem protocol. "
            "Make sure it implements answer(question: str, patient_id: str) -> SystemResponse."
        )
    if concurrency < 1:
        raise ValueError(f"concurrency must be >= 1, got {concurrency}")

    output_path = output_path or (RESULTS_RAW_DIR / f"{system_name}.jsonl")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    questions = load_questions(questions_path, patient_ids=patient_ids, limit=limit)

    # Load already-completed IDs for resume support (single-threaded; safe)
    done_ids: set[str] = set()
    if resume and output_path.exists():
        with open(output_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        done_ids.add(json.loads(line)["question_id"])
                    except (KeyError, json.JSONDecodeError):
                        pass

    remaining = [q for q in questions if q["id"] not in done_ids]
    skipped = len(questions) - len(remaining)
    if skipped:
        print(f"[harness] Resuming: skipping {skipped} already-done questions.")

    results: list[dict[str, Any]] = []
    write_lock = threading.Lock()
    completed_counter = {"n": 0}

    def _write_record(record: dict[str, Any], out_fh: Any) -> None:
        with write_lock:
            out_fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            out_fh.flush()
            results.append(record)
            completed_counter["n"] += 1
            n = completed_counter["n"]
            if n == 1 or n % 10 == 0 or n == len(remaining):
                print(f"[harness] {n}/{len(remaining)} questions answered.", flush=True)

    with open(output_path, "a", encoding="utf-8") as out_fh:
        if concurrency == 1:
            # Synchronous path — preserves original behaviour bit-for-bit.
            for q in remaining:
                record = _answer_one(system, system_name, q)
                _write_record(record, out_fh)
        else:
            # Concurrent path — many in-flight Groq calls.
            with ThreadPoolExecutor(
                max_workers=concurrency, thread_name_prefix="harness"
            ) as ex:
                futures = [
                    ex.submit(_answer_one, system, system_name, q) for q in remaining
                ]
                for fut in as_completed(futures):
                    record = fut.result()  # _answer_one never raises
                    _write_record(record, out_fh)

    print(f"[harness] Done. {len(results)} new records written to {output_path}.")
    return results


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run a retrieval system over the question bank."
    )
    p.add_argument(
        "--system",
        default="stub",
        help="System name: stub | a | b | c (default: stub)",
    )
    p.add_argument(
        "--questions",
        type=Path,
        default=QUESTIONS_PATH,
        help="Path to questions.jsonl",
    )
    p.add_argument(
        "--patients",
        nargs="*",
        metavar="PATIENT_ID",
        default=None,
        help="Space-separated patient UUIDs to restrict evaluation to. "
             "Omit for all patients.",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSONL path. Defaults to results/raw/<system>.jsonl",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of questions to answer (useful for smoke tests).",
    )
    p.add_argument(
        "--no-resume",
        action="store_true",
        help="Do not skip already-completed question IDs.",
    )
    p.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help=(
            "Number of in-flight system.answer calls. "
            "1 = synchronous (default); 4-8 saturates Developer-plan TPM."
        ),
    )
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    sys_obj = _load_system(args.system)
    run_harness(
        system=sys_obj,
        system_name=args.system,
        questions_path=args.questions,
        patient_ids=args.patients,
        output_path=args.output,
        limit=args.limit,
        resume=not args.no_resume,
        concurrency=args.concurrency,
    )
