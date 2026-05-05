# FHIRretrievaltest

Paired-data comparison of structured-FHIR RAG vs. LLM-narrative RAG on temporally-grounded specialty-medication question answering.

See `docs/00_PROJECT_PLAN.md` for the full plan, `docs/07_DECISIONS_v2_FREE_STACK.md` for the current (free-stack) decisions, and `CLAUDE.md` for Claude Code routing.

## Quick start (Setup + Week 1)

```bash
# 1. Install
pip install -e ".[dev]"

# 2. Synthea (one-time; requires JRE)
bash scripts/setup_synthea.sh
bash scripts/generate_synthea.sh 20260427 200

# 3. Specialty-regimen overlay
python -m overlay.specialty_regimen_generator \
    --input data/synthea_base/fhir --output data/fhir_bundles --seed 20260427

# 4. Narratives (LLM requires GROQ_API_KEY; templated is deterministic)
GROQ_API_KEY=... python -m narratives.gen_llm_narrative \
    --bundles data/fhir_bundles --output narratives/llm_narratives
python -m narratives.gen_templated_narrative \
    --bundles data/fhir_bundles --output narratives/templated_narratives

# 5. Fidelity audit (Week-1 gate ≥ 90%)
python -m narratives.fidelity_audit \
    --bundles data/fhir_bundles \
    --narratives narratives/llm_narratives \
    --output narratives/fidelity_reports
python -m narratives.fidelity_aggregate \
    --reports narratives/fidelity_reports --output reports/fidelity_audit_llm.md

# 6. Question bank
python -m questions.gen_question_bank \
    --bundles data/fhir_bundles --output questions/questions.jsonl --seed 20260427

# 7. Freeze
python scripts/freeze_dataset.py --output data/freeze.json
git tag dataset-freeze-v1
```

Or run the whole pipeline via `make dataset` (needs `GROQ_API_KEY` for step 4). Use `make smoke SAMPLE=10` for a fast 10-patient end-to-end check.

## Stack

All free. No paid APIs. See `docs/07_DECISIONS_v2_FREE_STACK.md`.

- Narrative LLM — `llama-3.3-70b-versatile` via Groq free tier
- Answer LLM — `qwen-3-32b` via Groq free tier (used in Weeks 2+)
- Embeddings — `BAAI/bge-large-en-v1.5` local via sentence-transformers
- FHIR — `fhir.resources` ≥ 8.0 (R4B)
- Vector store — ChromaDB (local)

## Licence

Code: Apache-2.0 (see `LICENSE`). Dataset: CC-BY-4.0 (pending employer clearance per `docs/05_OPEN_QUESTIONS.md` §E2).
