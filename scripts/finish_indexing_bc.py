"""Finish indexing Systems B and C for the smoke-test patients.

Run from the project root:
    HF_HUB_OFFLINE=1 python scripts/finish_indexing_bc.py

B still needs: patients 7, 8, 9
C still needs: patients 6, 7, 8, 9
"""
from __future__ import annotations

import os
import sys

# Force offline model loading before any sentence-transformers import
os.environ.setdefault("HF_HUB_OFFLINE", "1")

# Add project root to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import json
from pathlib import Path

FHIR_BUNDLES_DIR = Path(project_root) / "data" / "fhir_bundles"
B_CHROMA = Path(project_root) / "systems" / "structured_naive" / "chroma"
C_CHROMA = Path(project_root) / "systems" / "structured_aware" / "chroma"

# First 10 patients sorted
all_patients = sorted([f[:-5] for f in os.listdir(FHIR_BUNDLES_DIR) if f.endswith(".json")])[:10]

b_done = set(os.listdir(B_CHROMA)) if B_CHROMA.exists() else set()
c_done = set(os.listdir(C_CHROMA)) if C_CHROMA.exists() else set()

b_needed = [p for p in all_patients if p not in b_done]
c_needed = [p for p in all_patients if p not in c_done]

print(f"System B needs: {len(b_needed)} patients: {[p[:8] for p in b_needed]}")
print(f"System C needs: {len(c_needed)} patients: {[p[:8] for p in c_needed]}")

if not b_needed and not c_needed:
    print("Both systems fully indexed. Nothing to do.")
    sys.exit(0)

# Import systems (model loaded once per process)
print("Importing systems (model load on first embed)...")
from systems.structured_rag_naive import StructuredRAGNaive
from systems.structured_rag_aware import StructuredRAGAware

sys_b = StructuredRAGNaive()
sys_c = StructuredRAGAware()

print("\n=== System B remaining patients ===")
for i, pid in enumerate(b_needed):
    print(f"  B {pid[:8]} ...", flush=True, end=" ")
    try:
        sys_b.index_patient(pid)
        print("done")
    except Exception as e:
        print(f"ERROR: {e}")

print("\n=== System C remaining patients ===")
for i, pid in enumerate(c_needed):
    print(f"  C {pid[:8]} ...", flush=True, end=" ")
    try:
        sys_c.index_patient(pid)
        print("done")
    except Exception as e:
        print(f"ERROR: {e}")

# Final verification
b_count = len(list(B_CHROMA.iterdir())) if B_CHROMA.exists() else 0
c_count = len(list(C_CHROMA.iterdir())) if C_CHROMA.exists() else 0
print(f"\nFinal state: B={b_count}/10, C={c_count}/10")
if b_count == 10 and c_count == 10:
    print("SUCCESS: Both systems fully indexed.")
else:
    print("WARNING: Not all patients indexed!")
    sys.exit(1)
