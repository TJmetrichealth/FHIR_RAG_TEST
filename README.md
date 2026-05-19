# FHIR-RAG: Structured FHIR vs LLM-Narrative Retrieval

Paired-data comparison of structured-FHIR RAG vs. LLM-narrative RAG on adherence-indicator question answering for long-acting specialty medication regimens. Synthetic data only; no real PHI.

The same clinical facts are rendered into two parallel representations per patient (a FHIR R4B bundle and an LLM-generated narrative derived from the same bundle), 13,800 paired questions are run across three retrieval systems sharing a single answer LLM, and differences are evaluated with paired bootstrap and McNemar tests. Two further arms are included: a no-retrieval baseline (System N) that isolates question-text-attributable accuracy, and a deterministic templated-narrative ablation (System A-T) that isolates narrative format from LLM-specific lexical regularity.

The combined deposit (preprint PDF + code + synthetic dataset) is published at [doi:10.5281/zenodo.20263384](https://doi.org/10.5281/zenodo.20263384). Frozen artifacts are tagged in git as `dataset-freeze-v1`, `results-freeze-v1`, and `results-freeze-v2`.

## Headline findings

Numbers from [analysis/results.md](analysis/results.md), [analysis/recall_at_k.md](analysis/recall_at_k.md), [analysis/templated_compare.md](analysis/templated_compare.md), and [analysis/feature_extraction.md](analysis/feature_extraction.md).

- 13,800 paired questions per system, 200 patients, 5 PSP-grounded question families.
- Exact-match accuracy: A (narrative RAG) 40.6% [39.8, 41.4], B (structured naive) 35.3%, C (structured aware) 33.4%. All pairwise differences significant under McNemar (p < 0.001) with paired-bootstrap CIs excluding zero.
- Retrieval recall@5: B 0.762, C 0.852. C beats B on 4 of 5 families.
- No-retrieval baseline (System N): 25.2% overall, decomposing A's accuracy into a 25.2% question-text-attributable floor plus a +15.4 pp retrieval-attributable lift (B +10.1, C +8.2). All retrieval lifts have CIs excluding zero.
- Templated-narrative ablation (System A-T, deterministic, no LLM): 41.3% vs. A's 40.6%; paired-bootstrap delta +0.74 pp [+0.13, +1.34]. The narrative-format advantage is not LLM-specific. Within narrative format, style still matters per family: templated wins `temporal_comparison` by +10.21 pp; LLM wins `regimen_aggregation` by +7.29 pp.
- Feature-extraction arm (synthetic adherence label): FS-Structured AUC 0.997 vs. FS-Narrative 0.846 vs. FS-Aware 0.769. The representation that wins narrative QA is not the representation that wins downstream ML adherence prediction. The synthetic-label tautology is acknowledged and discussed in [paper/sections/05_discussion.tex](paper/sections/05_discussion.tex).

## Stack

Free-tier and local-only for narrative generation. Total API spend across the full project: $32.68 USD (Groq Developer plan, paid only for the evaluation matrix; narrative generation used the free tier).

| Component | Choice |
|---|---|
| Narrative-generation LLM | `llama-3.3-70b-versatile` via Groq |
| Answer LLM (held constant across systems) | `qwen/qwen3-32b` via Groq |
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
| [features/](features/) | Adherence metrics (PDC, MPR, persistence) shared by ground truth and the feature-extraction arm |
| [systems/](systems/) | System A narrative RAG, System B structured naive, System C structured resource-aware |
| [eval/](eval/) | Evaluation harness, scoring, response cache (cache itself not checked in) |
| [results/](results/) | `scored.csv`, `recall_at_k.csv`, `latency_tokens.csv`, `conformance_rates.csv`, raw JSONL traces |
| [analysis/](analysis/) | Statistics, error taxonomy, recall@k, latency/tokens, templated and no-retrieval comparisons, tier-3 breakdown |
| [paper/](paper/) | LaTeX preprint source, sections, bibliography |
| [mh_integration/](mh_integration/) | R4B validator hookup + System C FastAPI wrapper |
| [scripts/](scripts/) | Synthea setup, dataset freeze, indexing helpers, revision-arm runners |
| [reproducibility/](reproducibility/) | Repro guide, env, smoke test |

Invariants: `data/` and `results/` are frozen (tags above) and any change requires a new tagged release. `eval/cache/` is critical for byte-reproducible rebuilds and is gitignored, so back it up separately.

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

`make dataset` and `make reproduce` need `GROQ_API_KEY` in the environment for the narrative-generation step. Templated narratives, fidelity audit, question generation, and the freeze are deterministic and need no API key. Synthea generation needs a JRE; `scripts/setup_synthea.sh` handles a portable JRE on Windows + Bash.

Manual step-by-step (each Make target above expands to one of these):

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

# 4. Fidelity audit (W1 gate >= 90%; both narrative sources passed at 100% prompted-entity recall)
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

## Evaluation matrix

The three canonical systems plus the two revision-arm systems:

```bash
# Canonical systems A / B / C (full 13,800-question matrix)
python -m eval.harness --system a --concurrency 4
python -m eval.harness --system b --concurrency 4
python -m eval.harness --system c --concurrency 4

# Revision arms
python scripts/run_no_retrieval_arm.py --concurrency 4   # System N
python scripts/run_templated_arm.py    --concurrency 4   # System A-T

# Scoring
python -m eval.score                                                                # A/B/C
python -m eval.score --raw-dir results/raw_noretrieval/ --output-dir results/scored_noretrieval/ --systems n
python -m eval.score --raw-dir results/raw_templated/  --output-dir results/scored_templated/  --systems a_templated

# Analysis
python analysis/run_stats.py                  # paired bootstrap, McNemar
python analysis/run_tier3_baseline.py         # per-family modal baseline at Tier 3
python analysis/run_tier3_recall_breakdown.py # retriever vs. answer-LLM attribution
python analysis/run_templated_compare.py      # A-T vs. A
python analysis/run_token_sweep_compare.py    # 1024-token sensitivity sweep
python analysis/run_error_taxonomy.py         # deterministic regex taxonomy
python features/run_feature_arm.py            # FS-Structured / FS-Narrative / FS-Aware AUC
```

Regenerating evaluation responses without `eval/cache*/` populated will issue live Groq API calls. The cached responses are byte-reproducible; the cache directory is gitignored, so back it up separately.

## Reproducibility

- All seeds are pinned (default `20260427`); every stochastic call passes `seed` or `random_state` explicitly.
- `data/freeze.json` is the SHA-256 manifest pinning the W1 dataset bit-for-bit (overall SHA-256 `4d0da93e...`). `data/freeze_v2.json` extends this with the 20 revision-arm artifacts (overall SHA-256 `2358e828...`).
- `eval/cache/`, `eval/cache_1024/`, `eval/cache_noretrieval/`, and `eval/cache_templated/` hold every Groq response keyed by request hash. With them present, `make reproduce` is offline; without them, the rebuild reissues live calls.
- The `dataset-freeze-v1`, `results-freeze-v1`, and `results-freeze-v2` git tags pin the exact commits the paper's numbers come from.
- A `Dockerfile` is provided for hermetic builds.
- FHIR R4B conformance is verified by `make fhir-validate` (HL7 official Java validator plus extended Pydantic checks over every `Reference` field). Compliance posture, allowlisted warnings, and out-of-scope items are documented in [docs/FHIR_COMPLIANCE.md](docs/FHIR_COMPLIANCE.md).

## Licence

- Code: Apache-2.0. See [LICENSE](LICENSE).
- Dataset: CC-BY-4.0, released as part of the combined Zenodo deposit.

The combined Zenodo deposit ([doi:10.5281/zenodo.20263384](https://doi.org/10.5281/zenodo.20263384)) is the canonical citation. It uses CC-BY-4.0 as the record-level umbrella; the code component within the deposit remains Apache-2.0 via the included `LICENSE` file.

## Citation

The arXiv submission is in preparation. Until it is posted, cite the Zenodo deposit:

```bibtex
@software{jani2026fhirrag,
  author    = {Jani, Tirthesh},
  title     = {{FHIR-RAG}: Paired-Data Comparison of Structured {FHIR} and {LLM}-Narrative Retrieval for Adherence-Indicator Question Answering},
  year      = {2026},
  publisher = {Zenodo},
  version   = {v1.0.0},
  doi       = {10.5281/zenodo.20263384},
  url       = {https://doi.org/10.5281/zenodo.20263384}
}
```

Authorship is sole-authored: Tirthesh Jani (ORCID [0009-0005-5965-4409](https://orcid.org/0009-0005-5965-4409)).
