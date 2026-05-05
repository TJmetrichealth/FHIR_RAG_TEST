"""Pre-index all 200 patients for Systems B and C.

Run from the project root:
    HF_HUB_OFFLINE=1 python scripts/index_all_bc.py
"""
from __future__ import annotations

import os
import sys
import time

os.environ.setdefault("HF_HUB_OFFLINE", "1")

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from pathlib import Path

FHIR_BUNDLES_DIR = Path(project_root) / "data" / "fhir_bundles"
B_CHROMA = Path(project_root) / "systems" / "structured_naive" / "chroma"
C_CHROMA = Path(project_root) / "systems" / "structured_aware" / "chroma"

all_patients = sorted([f[:-5] for f in os.listdir(FHIR_BUNDLES_DIR) if f.endswith(".json")])
print(f"Total patients: {len(all_patients)}")

b_done = set(os.listdir(B_CHROMA)) if B_CHROMA.exists() else set()
c_done = set(os.listdir(C_CHROMA)) if C_CHROMA.exists() else set()

b_needed = [p for p in all_patients if p not in b_done]
c_needed = [p for p in all_patients if p not in c_done]

print(f"B needs: {len(b_needed)} patients")
print(f"C needs: {len(c_needed)} patients")

if not b_needed and not c_needed:
    print("Both fully indexed. Exiting.")
    sys.exit(0)

print("Loading systems (model will load lazily)...")
from systems.structured_rag_naive import StructuredRAGNaive
from systems.structured_rag_aware import StructuredRAGAware

sys_b = StructuredRAGNaive()
sys_c = StructuredRAGAware()

print(f"\n=== Indexing B ({len(b_needed)} patients) ===", flush=True)
t0 = time.time()
for i, pid in enumerate(b_needed, 1):
    try:
        sys_b.index_patient(pid)
        if i % 10 == 0 or i == len(b_needed):
            elapsed = time.time() - t0
            print(f"  B {i}/{len(b_needed)} ({pid[:8]}) elapsed={elapsed:.0f}s", flush=True)
    except Exception as e:
        print(f"  B ERROR {pid[:8]}: {e}", flush=True)

print(f"\n=== Indexing C ({len(c_needed)} patients) ===", flush=True)
t0 = time.time()
for i, pid in enumerate(c_needed, 1):
    try:
        sys_c.index_patient(pid)
        if i % 10 == 0 or i == len(c_needed):
            elapsed = time.time() - t0
            print(f"  C {i}/{len(c_needed)} ({pid[:8]}) elapsed={elapsed:.0f}s", flush=True)
    except Exception as e:
        print(f"  C ERROR {pid[:8]}: {e}", flush=True)

b_count = len(list(B_CHROMA.iterdir())) if B_CHROMA.exists() else 0
c_count = len(list(C_CHROMA.iterdir())) if C_CHROMA.exists() else 0
print(f"\nFinal: B={b_count}/200, C={c_count}/200")
