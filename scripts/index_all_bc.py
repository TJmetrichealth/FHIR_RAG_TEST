"""Pre-index Systems B and C against the frozen FHIR bundles.

Run from the project root:
    python scripts/index_all_bc.py [--system b|c|both] [--max-patients N]

Idempotent: skips any patient whose chroma dir already contains a non-empty
collection. Failed/empty dirs (size < 1 MB) are wiped on startup so they are
re-attempted, not skipped as "done".

The script defaults to HF_HUB_OFFLINE=1 ONLY if BGE-large is already cached;
otherwise it allows the first download. Set the env var explicitly to override.

Sliced operation:
  --system c --max-patients 50  → process at most 50 patients then exit.
  Spawn this script multiple times (each in a fresh process) to bound
  per-process state accumulation — works around a numpy ``_fdopen`` issue
  observed when a single process indexes ~150+ patients in a row on Windows.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import time

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from pathlib import Path

FHIR_BUNDLES_DIR = Path(project_root) / "data" / "fhir_bundles"
B_CHROMA = Path(project_root) / "systems" / "structured_naive" / "chroma"
C_CHROMA = Path(project_root) / "systems" / "structured_aware" / "chroma"

# An "empty" chroma dir holds just the SQLite skeleton (~184 KB on Windows).
# Real, fully-indexed collections are several MB; even minimal ones cross 1 MB
# once HNSW index files are written.
_EMPTY_DIR_THRESHOLD_BYTES = 1_000_000


def _wipe_empty_dirs(base: Path) -> int:
    if not base.exists():
        return 0
    wiped = 0
    for p in sorted(base.iterdir()):
        if not p.is_dir():
            continue
        size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
        if size < _EMPTY_DIR_THRESHOLD_BYTES:
            shutil.rmtree(p, ignore_errors=True)
            wiped += 1
    return wiped


def _all_patients() -> list[str]:
    return sorted(
        f[:-5]
        for f in os.listdir(FHIR_BUNDLES_DIR)
        if f.endswith(".json") and not f.startswith("_")
    )


def _needed(all_patients: list[str], chroma_dir: Path) -> list[str]:
    done = set(os.listdir(chroma_dir)) if chroma_dir.exists() else set()
    return [p for p in all_patients if p not in done]


def _run_slice(
    system_name: str,
    pids_needed: list[str],
    max_patients: int | None,
) -> None:
    if not pids_needed:
        print(f"=== {system_name} fully indexed, nothing to do ===", flush=True)
        return

    work = pids_needed if max_patients is None else pids_needed[:max_patients]
    print(
        f"\n=== Indexing {system_name} (this slice: {len(work)}, "
        f"remaining after: {len(pids_needed) - len(work)}) ===",
        flush=True,
    )

    if system_name == "B":
        from systems.structured_rag_naive import StructuredRAGNaive

        sys_obj = StructuredRAGNaive()
    elif system_name == "C":
        from systems.structured_rag_aware import StructuredRAGAware

        sys_obj = StructuredRAGAware()
    else:
        raise ValueError(f"unknown system: {system_name}")

    t0 = time.time()
    for i, pid in enumerate(work, 1):
        try:
            sys_obj.index_patient(pid)
            if i % 5 == 0 or i == len(work):
                elapsed = time.time() - t0
                print(
                    f"  {system_name} {i}/{len(work)} ({pid[:8]}) elapsed={elapsed:.0f}s",
                    flush=True,
                )
        except Exception as e:  # noqa: BLE001
            print(f"  {system_name} ERROR {pid[:8]}: {e}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--system",
        choices=["b", "c", "both"],
        default="both",
        help="Which system(s) to index (default: both).",
    )
    parser.add_argument(
        "--max-patients",
        type=int,
        default=None,
        help=(
            "Cap the number of patients indexed in this run "
            "(per-system). Useful for sliced/subprocess runs. "
            "Default: unlimited (process every still-needed patient)."
        ),
    )
    parser.add_argument(
        "--no-wipe",
        action="store_true",
        help="Skip the startup empty-dir wipe.",
    )
    args = parser.parse_args()

    all_patients = _all_patients()
    print(f"Total patients: {len(all_patients)}")

    if not args.no_wipe:
        b_wiped = _wipe_empty_dirs(B_CHROMA)
        c_wiped = _wipe_empty_dirs(C_CHROMA)
        if b_wiped or c_wiped:
            print(
                f"Wiped empty chroma dirs: B={b_wiped}, C={c_wiped}",
                flush=True,
            )

    b_needed = _needed(all_patients, B_CHROMA) if args.system in ("b", "both") else []
    c_needed = _needed(all_patients, C_CHROMA) if args.system in ("c", "both") else []
    print(
        f"To index this run: B={len(b_needed)}, C={len(c_needed)} "
        f"(--max-patients={args.max_patients})"
    )

    if args.system in ("b", "both") and b_needed:
        _run_slice("B", b_needed, args.max_patients)
    if args.system in ("c", "both") and c_needed:
        _run_slice("C", c_needed, args.max_patients)

    b_count = len(list(B_CHROMA.iterdir())) if B_CHROMA.exists() else 0
    c_count = len(list(C_CHROMA.iterdir())) if C_CHROMA.exists() else 0
    print(f"\nFinal: B={b_count}/200, C={c_count}/200", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
