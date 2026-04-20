# Project: FHIR-RAG Preprint

Paired-data comparison of structured-FHIR RAG vs. LLM-narrative RAG on temporally-grounded specialty-medication QA. Full plan: `docs/00_PROJECT_PLAN.md`. Current stack decisions: `docs/07_DECISIONS_v2_FREE_STACK.md` (supersedes v1).

## Subagent routing
- Any task touching dataset generation, Synthea, or FHIR bundles → **data-engineer**
- Any task that writes or mutates production code → **retrieval-engineer** (for systems A/B/C) or **data-engineer** (for dataset code)
- Before merging to main, and at every week's gate → **reviewer** runs a read-only audit
- Literature searches, prior-art questions, "has anyone done X?" → **researcher**
- Scoring, metrics, statistical tests → **evaluator** (for running) then **statistician** (for interpreting)
- Narrative generation or fidelity questions → **narrative-smith**
- Paper drafting or section writes → **writer** (reviewer must read after)
- Planning, milestone updates, decision log entries → **planner**

## Hard rules
- No LLM-as-judge anywhere in evaluation. Evaluator must never be asked to score answers with a model.
- Dataset is frozen at the end of week 1; any change after that requires a decision-log entry.
- The reviewer is read-only. Never grant write tools to the reviewer.
- All material choices (model, k, chunk size, temperatures) go in docs/decisions.md.
- Free-stack only — no paid-API calls without explicit user approval and a decision-log entry.

## Stack (v2 free)
- Narrative LLM: `llama-3.3-70b-versatile` via Groq free tier
- Answer LLM: `qwen-3-32b` via Groq free tier (different vendor training lineage than narrative LLM)
- Embeddings: `BAAI/bge-large-en-v1.5` local via sentence-transformers
- FHIR: `fhir.resources` ≥8.0 (R4B pydantic models)
- Vector store: ChromaDB local
- Budget: $0 CAD

## Invariants (from `docs/04_REPO_LAYOUT.md`)
- `data/` is frozen at the end of Week 1 (tag: `dataset-freeze-v1`).
- `results/` is frozen at the end of Week 3 (tag: `results-freeze-v1`).
- `eval/cache/` is never checked in but must be preserved — losing it means re-paying rate-limit wall time.
- `docs/decisions.md` is append-only.
