"""Recover the patients that have empty chroma collections.

Identifies patients in B and C whose collection is empty, wipes their dir,
and re-indexes them with full traceback capture (no try/except swallow).
Run from project root:

    python scripts/index_recover.py [--system b|c|both] [--limit N]
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import time
import traceback
from pathlib import Path

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import chromadb  # noqa: E402

B_CHROMA = Path(project_root) / "systems" / "structured_naive" / "chroma"
C_CHROMA = Path(project_root) / "systems" / "structured_aware" / "chroma"


def _empty_patients(base: Path, prefix: str) -> list[str]:
    """Return UUIDs of patients with an existing dir but zero-vector collection."""
    if not base.exists():
        return []
    out: list[str] = []
    for pdir in sorted(base.iterdir()):
        if not pdir.is_dir():
            continue
        try:
            cl = chromadb.PersistentClient(path=str(pdir))
            col = cl.get_or_create_collection(
                prefix + pdir.name[:8], metadata={"hnsw:space": "cosine"}
            )
            n = col.count()
            del cl, col
        except Exception:
            n = 0
        if n == 0:
            out.append(pdir.name)
    return out


def _wipe_one(base: Path, pid: str) -> None:
    p = base / pid
    if p.exists():
        shutil.rmtree(p, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--system", choices=["b", "c", "both"], default="both")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    failed: list[tuple[str, str, str]] = []
    succeeded: list[tuple[str, str]] = []

    if args.system in ("b", "both"):
        from systems.structured_rag_naive import StructuredRAGNaive

        empties = _empty_patients(B_CHROMA, "snv_")
        print(f"B has {len(empties)} empty patients", flush=True)
        if args.limit:
            empties = empties[: args.limit]
        sys_b = StructuredRAGNaive()
        for i, pid in enumerate(empties, 1):
            _wipe_one(B_CHROMA, pid)
            t0 = time.time()
            try:
                sys_b.index_patient(pid)
                # Verify
                cl = chromadb.PersistentClient(path=str(B_CHROMA / pid))
                col = cl.get_or_create_collection(
                    "snv_" + pid[:8], metadata={"hnsw:space": "cosine"}
                )
                n = col.count()
                del cl, col
                if n > 0:
                    succeeded.append(("B", pid))
                    print(
                        f"  B {i}/{len(empties)} OK {pid[:8]}  count={n}  {time.time()-t0:.1f}s",
                        flush=True,
                    )
                else:
                    failed.append(("B", pid, "silent: count==0 after index_patient"))
                    print(
                        f"  B {i}/{len(empties)} SILENT FAIL {pid[:8]}  {time.time()-t0:.1f}s",
                        flush=True,
                    )
            except Exception as e:  # noqa: BLE001
                tb = traceback.format_exc()
                failed.append(("B", pid, f"{type(e).__name__}: {e}"))
                print(
                    f"  B {i}/{len(empties)} EXCEPTION {pid[:8]}  {time.time()-t0:.1f}s  "
                    f"{type(e).__name__}: {e}",
                    flush=True,
                )
                # Print full traceback for the FIRST failure only — keep log readable
                if len([x for x in failed if x[0] == "B"]) == 1:
                    print(tb, flush=True)

    if args.system in ("c", "both"):
        from systems.structured_rag_aware import StructuredRAGAware

        empties = _empty_patients(C_CHROMA, "sva_")
        print(f"C has {len(empties)} empty patients", flush=True)
        if args.limit:
            empties = empties[: args.limit]
        sys_c = StructuredRAGAware()
        for i, pid in enumerate(empties, 1):
            _wipe_one(C_CHROMA, pid)
            t0 = time.time()
            try:
                sys_c.index_patient(pid)
                cl = chromadb.PersistentClient(path=str(C_CHROMA / pid))
                col = cl.get_or_create_collection(
                    "sva_" + pid[:8], metadata={"hnsw:space": "cosine"}
                )
                n = col.count()
                del cl, col
                if n > 0:
                    succeeded.append(("C", pid))
                    print(
                        f"  C {i}/{len(empties)} OK {pid[:8]}  count={n}  {time.time()-t0:.1f}s",
                        flush=True,
                    )
                else:
                    failed.append(("C", pid, "silent: count==0 after index_patient"))
                    print(
                        f"  C {i}/{len(empties)} SILENT FAIL {pid[:8]}  {time.time()-t0:.1f}s",
                        flush=True,
                    )
            except Exception as e:  # noqa: BLE001
                tb = traceback.format_exc()
                failed.append(("C", pid, f"{type(e).__name__}: {e}"))
                print(
                    f"  C {i}/{len(empties)} EXCEPTION {pid[:8]}  {time.time()-t0:.1f}s  "
                    f"{type(e).__name__}: {e}",
                    flush=True,
                )
                if len([x for x in failed if x[0] == "C"]) == 1:
                    print(tb, flush=True)

    print("\n=== SUMMARY ===", flush=True)
    print(f"Succeeded: {len(succeeded)}", flush=True)
    print(f"Failed:    {len(failed)}", flush=True)
    if failed:
        print("Failed patients:", flush=True)
        for sysname, pid, reason in failed:
            print(f"  {sysname}  {pid}  {reason}", flush=True)
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
