# FHIR-RAG: Structured FHIR vs LLM-Narrative Retrieval

Paired-data comparison of structured-FHIR RAG vs. LLM-narrative RAG on adherence-indicator question answering for long-acting specialty medication regimens. Synthetic data only; no real PHI.

The same clinical facts are rendered into two parallel representations per patient (a FHIR R4B bundle and an LLM-generated narrative), 13,800 paired questions are run across three retrieval systems sharing a single answer LLM, and differences are evaluated with paired bootstrap and McNemar tests.

Full plan: [docs/00_PROJECT_PLAN.md](docs/00_PROJECT_PLAN.md). Stack and budget decisions: [docs/07_DECISIONS_v2_FREE_STACK.md](docs/07_DECISIONS_v2_FREE_STACK.md). Append-only decision log: [docs/decisions.md](docs/decisions.md).

## Status

| Stage | State | Tag |
|---|---|---|
| Week 1 — dataset, narratives, fidelity, question bank | Frozen | `dataset-freeze-v1` |
| Week 2 — three retrieval systems + full evaluation matrix | Frozen | `results-freeze-v1` |
| Week 3 — statistics, error taxonomy, figures | In progress | — |
| Week 4–5 — paper drafting | In progress | — |

Headline numbers (see [analysis/results.md](analysis/results.md), [analysis/recall_at_k.md](analysis/recall_at_k.md)):

- 13,800 paired questions per system, 200 patients, 5 PSP-grounded question families.
- Exact-match accuracy: A (narrative RAG) 40.6% [39.8, 41.4], B (structured naive) 35.3%, C (structured aware) 33.4%.
- Retrieval recall@5 (B vs C, k=5): 0.762 vs 0.852; C beats B on 4 of 5 families.
- All pairwise differences significant under McNemar, p < 0.001.

## Stack

Free-tier and local-only. Total project cost: $0 CAD. Details in [docs/07_DECISIONS_v2_FREE_STACK.md](docs/07_DECISIONS_v2_FREE_STACK.md).

| Component | Choice |
|---|---|
| Narrative-generation LLM | `llama-3.3-70b-versatile` via Groq free tier |
| Answer LLM (held constant across systems) | `qwen-3-32b` via Groq free tier |
| Embeddings | `BAAI/bge-large-en-v1.5` local via sentence-transformers |
| FHIR models | `fhir.resources` >= 8.0 (R4B) |
| Vector store | ChromaDB (local) |
| Synthetic patients | Synthea + custom 3-tier specialty-regimen overlay |

## Repository layout

| Path | Purpose |
|---|---|
| [overlay/](overlay/) | Specialty-regimen overlay generator, tier definitions, tests |
| [data/](data/) | Synthea base + 200 enhanced FHIR bundles + `freeze.json` SHA-256 manifest |
| [narratives/](narratives/) | LLM and templated narratives, fidelity audit, fidelity reports |
| [questions/](questions/) | 13,800-row question bank + ground-truth functions |
| [features/](features/) | Adherence metrics (PDC, MPR, persistence) — shared by ground truth and the feature-extraction arm |
| [systems/](systems/) | System A narrative RAG, System B structured naive, System C structured resource-aware |
| [eval/](eval/) | Evaluation harness, scoring, response cache (cache itself not checked in) |
| [results/](results/) | `scored.csv`, `recall_at_k.csv`, `latency_tokens.csv`, `conformance_rates.csv`, raw JSONL traces |
| [analysis/](analysis/) | Statistics, error taxonomy, recall@k, latency/tokens writeups |
| [paper/](paper/) | LaTeX preprint source, sections, bibliography, appendix |
| [mh_integration/](mh_integration/) | R4B validator hookup + System C FastAPI wrapper (Phase 0 handoff to metricHEALTH) |
| [scripts/](scripts/) | Synthea setup, dataset freeze, indexing helpers |
| [reproducibility/](reproducibility/) | Repro guide, env, smoke test |

Invariants: `data/` is frozen at the end of W1; `results/` is frozen at the end of W3; `eval/cache/` is critical to reproduction but is gitignored (back up separately). See [docs/04_REPO_LAYOUT.md](docs/04_REPO_LAYOUT.md).

## Quick start

```bash
pip install -e ".[dev]"
```

`make help` lists every Make target. The most useful ones:

```bash
make smoke SAMPLE=10        # 10-patient end-to-end check, writes to *_smoke paths only
make dataset                # Full W1 pipeline: synthea, overlay, narratives, fidelity, questions, freeze
make reproduce              # As above; warns and pauses if eval/cache/ is empty
```

`make dataset` and `make reproduce` need `GROQ_API_KEY` in the environment for the narrative-generation step. Templated narratives, fidelity audit, question generation, and the freeze are deterministic and need no API key. Synthea generation needs a JRE; `scripts/setup_synthea.sh` handles the portable JRE on Windows + Bash.

Manual step-by-step (each target above expands to one of these):

```bash
# 1. Synthea base (one-time)
bash scripts/setup_synthea.sh
bash scripts/generate_synthea.sh 20260427 200

# 2. Specialty-regimen overlay
python -m overlay.specialty_regimen_generator \
    --input data/synthea_base/fhir --output data/fhir_bundles \
    --seed 20260427 --reference-today 2026-04-27

# 3. Narratives (LLM needs GROQ_API_KEY; templated is deterministic)
python -m narratives.gen_llm_narrative       --bundles data/fhir_bundles --output narratives/llm_narratives
python -m narratives.gen_templated_narrative --bundles data/fhir_bundles --output narratives/templated_narratives

# 4. Fidelity audit (W1 gate >= 90%)
python -m narratives.fidelity_audit \
    --bundles data/fhir_bundles \
    --narratives narratives/llm_narratives \
    --output narratives/fidelity_reports
python -m narratives.fidelity_aggregate \
    --reports narratives/fidelity_reports \
    --output reports/fidelity_audit_llm.md

# 5. Question bank (13,800 rows)
python -m questions.gen_question_bank \
    --bundles data/fhir_bundles --output questions/questions.jsonl --seed 20260427

# 6. Freeze
python scripts/freeze_dataset.py --output data/freeze.json --strict
```

## Reproducibility

- All seeds are pinned (default `20260427`); any stochastic call passes `seed` or `random_state` explicitly.
- `data/freeze.json` is the SHA-256 manifest that pins the W1 dataset bit-for-bit.
- `eval/cache/` holds every Groq response keyed by request hash. With it present, `make reproduce` is offline; without it, the rebuild reissues live calls and burns rate-limit time. The Make target prints a warning and a 5-second abort window.
- The `dataset-freeze-v1` and `results-freeze-v1` git tags pin the exact commits the paper's numbers come from.
- A `Dockerfile` is provided for hermetic builds.

## Licence

- Code: Apache-2.0 — see [LICENSE](LICENSE).
- Dataset: CC-BY-4.0 (pending employer clearance per [docs/05_OPEN_QUESTIONS.md](docs/05_OPEN_QUESTIONS.md) E2).

## Citation

A preprint is in preparation. Until it is on arXiv, cite this repository directly. Authorship is sole-authored: Tirthesh Jani.
