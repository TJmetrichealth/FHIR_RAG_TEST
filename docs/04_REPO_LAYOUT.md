# Repository Layout

Target directory structure for the project (v3 dual-purpose). Set this up in Week 1 Day 1 so all subsequent work has a consistent home.

**v3 changes:** Added `mh_integration/` (R4B validator hookup + System C FastAPI wrapper for metricCONNECT); added `features/` (adherence metrics + feature-extraction arm); added `thesis_chapter/` (Phase 0 scaffold).

```
fhir-rag-preprint/
├── README.md                     # Project overview, install, quickstart
├── CLAUDE.md                     # Claude Code routing policy (see 01_CLAUDE_CODE_AGENT_PLAN.md)
├── LICENSE                       # Apache-2.0 (code) per v2
├── LICENSE-DATA                  # CC-BY-4.0 (dataset) per v2
├── Makefile                      # `make reproduce` runs everything end-to-end
├── pyproject.toml                # or requirements.txt — pinned versions
├── Dockerfile                    # For strong reproducibility (see C5)
│
├── .claude/
│   └── agents/
│       ├── planner.md
│       ├── researcher.md
│       ├── data-engineer.md
│       ├── narrative-smith.md
│       ├── question-architect.md
│       ├── retrieval-engineer.md
│       ├── evaluator.md
│       ├── statistician.md
│       ├── writer.md
│       └── reviewer.md
│
├── docs/
│   ├── 00_PROJECT_PLAN.md
│   ├── 01_CLAUDE_CODE_AGENT_PLAN.md
│   ├── 02_LITERATURE_REVIEW_QUERIES.md
│   ├── 03_PAPER_DRAFT_STRUCTURE.md
│   ├── 04_REPO_LAYOUT.md
│   ├── 05_OPEN_QUESTIONS.md
│   ├── 06_DECISIONS_ANSWERED.md     # v1 paid-stack — audit trail only
│   ├── 07_DECISIONS_v2_FREE_STACK.md # v2 free-stack + v3 dual-purpose addendum
│   ├── decisions.md                  # Append-only decision log
│   ├── checkpoints/
│   │   ├── week_1.md
│   │   ├── week_2.md
│   │   └── ...
│   ├── reviews/
│   │   └── YYYY-MM-DD.md             # Reviewer-agent reports
│   └── literature/
│       ├── bibliography.bib
│       ├── clinical_rag.md
│       ├── structured_vs_unstructured.md
│       ├── fhir_ml.md
│       ├── clinical_temporal.md
│       ├── synthea.md
│       ├── psp_adherence_indicators.md   # Block 6 (renamed from specialty_pharmacy)
│       ├── llm_clinical_documentation.md
│       ├── retrieval_strategies.md
│       ├── rag_evaluation.md
│       ├── canadian_psp.md               # Block 10 (light)
│       └── adherence_ml_features.md      # Block 11 (new for v3)
│
├── data/                         # DATASET — frozen at end of Week 1
│   ├── freeze.json               # SHA-256 manifest of every file here
│   ├── synthea_base/             # Raw Synthea output
│   ├── fhir_bundles/             # Enhanced FHIR bundles with specialty overlay
│   └── README.md                 # Dataset documentation (for release)
│
├── narratives/
│   ├── llm_narratives/           # Generated with A1 LLM, fixed prompt
│   ├── templated_narratives/     # Deterministic template output (ablation)
│   └── fidelity_reports/         # Per-narrative fidelity audit
│
├── questions/
│   ├── questions.jsonl           # The 120-question bank (5 adherence families × 24 each)
│   ├── ground_truth/             # Programmatic ground-truth functions
│   ├── audit_sample.md           # 20-question hand-audit results
│   └── pytest_harness/           # pytest-style wrapper making the question bank reusable as a regression suite (consumed by metricHEALTH Phase 5)
│
├── overlay/
│   ├── specialty_regimen_generator.py
│   ├── tiers.py                  # Tier 1, 2, 3 definitions
│   └── tests/
│
├── features/                     # NEW for v3 — adherence metrics + feature-extraction arm
│   ├── adherence_metrics.py      # PDC, MPR, persistence, days-since-last-dose (shared: ground truth + features + metricHEALTH Phase 3)
│   ├── tests/                    # unit tests against known-case fixtures (R6 mitigation)
│   ├── extractors/
│   │   ├── fs_structured.py      # Compute features directly from FHIR bundle
│   │   ├── fs_narrative.py       # Extract features from LLM narrative via extraction prompt
│   │   └── fs_aware.py           # Extract features via System C's resource-aware retrieval
│   └── classifiers/
│       ├── adherence_lgbm.py     # LightGBM adherence classifier
│       └── adherence_logreg.py   # Logistic regression baseline
│
├── systems/
│   ├── common/
│   │   ├── answer_llm.py         # Shared answer-LLM wrapper with caching (Qwen 3 32B via Groq)
│   │   ├── embedder.py           # Shared embedding client (BGE-large-v1.5 local)
│   │   ├── chunker.py            # Shared text chunking
│   │   ├── cache.py              # Response cache (hash-keyed)
│   │   └── types.py              # SystemResponse dataclass
│   ├── narrative_rag.py          # System A
│   ├── structured_rag_naive.py   # System B
│   ├── structured_rag_aware.py   # System C — resource-aware
│   └── tests/
│       └── smoke/                # End-to-end smoke tests per system
│
├── mh_integration/               # NEW for v3 — artefacts destined for metricHEALTH
│   ├── r4b_validator.py          # Pre-write R4B conformance validator (Phase 1 hookup); generic Reference walker over all fields
│   ├── hl7_validator.py          # NEW (2026-05-11) — wrapper around HL7 official Java FHIR Validator (validator_cli.jar)
│   ├── expected_warnings.json    # NEW (2026-05-11) — allowlist for intentional terminology warnings (decision B5)
│   ├── case_manager_qa.py        # FastAPI wrapper around System C — mounts into metricCONNECT (Phase 4 prototype)
│   ├── schemas/
│   │   └── case_manager_qa.py    # Pydantic request/response models
│   ├── tests/                    # NEW (2026-05-11) — pytest suite with synthetic fixtures for both validators
│   │   ├── conftest.py
│   │   ├── test_r4b_validator_extended.py
│   │   ├── test_hl7_validator.py
│   │   └── fixtures/             # 8 small Bundle fixtures: valid_minimal_urn, valid_minimal_relative, broken_subject_ref, broken_nested_ref, missing_careplan, bad_status, logical_reference, contained_resource
│   └── README.md                 # How the metricHEALTH team picks these up
│
├── eval/
│   ├── run_full_matrix.py        # Orchestrates the evaluation across systems × Qs × patients
│   ├── run_feature_extraction.py # NEW for v3 — runs the feature-extraction arm end-to-end
│   ├── score.py                  # Exact-match / set-equality / tolerance scoring (incl. proportion tolerance for PDC/MPR)
│   ├── recall_at_k.py            # Retrieval-only metrics
│   └── cache/                    # All LLM responses cached here (not checked in)
│
├── analysis/
│   ├── results.md                # Narrative of findings with numbers + figures
│   ├── statistical_tests.md      # Paired bootstrap, McNemar
│   ├── error_taxonomy.md         # 3–4 categories with examples
│   ├── templated_vs_llm_narrative.md  # Ablation writeup
│   └── feature_extraction.md     # NEW for v3 — O6 writeup with Phase 3 implications
│
├── results/
│   ├── raw/                      # Verbatim per-question-per-system traces (JSONL)
│   ├── scored.csv                # Scored evaluation matrix
│   ├── latency_tokens.csv        # Cost / latency per system
│   ├── recall_at_k.csv           # Retrieval-only metrics
│   ├── conformance_rates.csv     # Per-tier R4B conformance (Pydantic validator)
│   ├── hl7_validator_results.csv # NEW (2026-05-11) — per-bundle HL7 official-validator outcome
│   ├── hl7_validator_raw/        # NEW (2026-05-11) — raw OperationOutcome JSON per bundle (gitignored optionally)
│   └── feature_extraction/       # NEW for v3
│       ├── auc_by_feature_set.csv
│       ├── auc_by_classifier.csv
│       └── paired_bootstrap_cis.csv
│
├── figures/
│   ├── system_diagram.pdf
│   ├── regimen_tiers.pdf
│   ├── fidelity_distribution.pdf
│   ├── main_results.pdf
│   ├── complexity_gradient.pdf   # The money plot
│   ├── retrieval_vs_answer.pdf
│   ├── error_taxonomy.pdf
│   └── feature_extraction_auc.pdf  # NEW for v3
│
├── paper/
│   ├── main.tex                  # Preprint source
│   ├── main.pdf                  # Compiled PDF
│   ├── sections/
│   │   ├── abstract.tex          # MUST NOT reference metricHEALTH (R16)
│   │   ├── introduction.tex
│   │   ├── related_work.tex
│   │   ├── dataset.tex
│   │   ├── systems.tex
│   │   ├── evaluation.tex
│   │   ├── results.tex
│   │   ├── discussion.tex
│   │   ├── limitations.tex
│   │   └── conclusion.tex
│   ├── bibliography.bib          # Symlink or copy of docs/literature/bibliography.bib
│   └── appendix/
│
├── thesis_chapter/               # NEW for v3 — Phase 0 scaffold for the metricHEALTH thesis
│   ├── phase_0.md                # Same experiments, Phase 0 framing
│   └── integration_map.md        # Copy of §13 from 00_PROJECT_PLAN.md
│
├── reproducibility/
│   ├── README.md                 # Repro guide
│   ├── environment.yml           # Conda env
│   └── smoke_test.sh             # Sanity check for fresh clone
│
└── scripts/
    ├── freeze_dataset.py         # Computes SHA-256 manifest; writes data/freeze.json
    ├── check_cache.py            # Sanity-check cache hit rate
    ├── cost_preflight.py         # Estimate API cost before a full run (spoiler: $0 per v2)
    ├── setup_java_portable.sh    # Portable Eclipse Temurin JRE 21 into tools/jre/
    ├── setup_hl7_validator.sh    # NEW (2026-05-11) — pinned HL7 FHIR Validator jar into tools/hl7-validator/
    └── run_fhir_validation.py    # NEW (2026-05-11) — orchestrator: Pydantic + HL7 validator + report aggregator
```

---

## Invariants

- **`data/` is frozen at the end of Week 1.** Any change requires a decision-log entry.
- **`results/` is frozen at the end of Week 3.** The paper's numbers come from this directory, unchanged.
- **`eval/cache/` is never checked in** but is critical — losing it means re-paying free-tier rate-limit time. Back it up to cloud storage at end of each day during Week 3.
- **`paper/sections/*.tex`** is the single source of truth; `paper/main.tex` is a thin `\input` wrapper.
- **`paper/sections/abstract.tex` must not reference metricHEALTH** (R16 mitigation). The grep check is part of the reviewer's checklist.
- **`docs/decisions.md`** is append-only. Earlier decisions are never edited — only superseded by later entries.
- **`features/adherence_metrics.py`** is load-bearing: the question-architect uses it for ground truth, the evaluator uses it for feature extraction, metricHEALTH Phase 3 will use it for ML features. Any edit after the Week 1 freeze requires regenerating ground truth AND all feature extractions.
- **`mh_integration/`** artefacts are designed to be lifted into the metricHEALTH repo as-is. Changes there are cross-repo decisions.
- **FHIR R4B compliance posture** is documented in [docs/FHIR_COMPLIANCE.md](FHIR_COMPLIANCE.md): what is checked, by which validator, what is intentionally out of scope (profile conformance, real terminology), and how to reproduce `make fhir-validate` locally.

---

## Branch strategy

- `main` — only green commits. Merged from feature branches after reviewer-agent gate passes.
- `dataset/week1` — dataset construction work, including R4B validator hookup. Merged at Week 1 gate.
- `systems/week2` — retrieval systems work, including `mh_integration/case_manager_qa.py` FastAPI wrapper. Merged at Week 2 gate.
- `eval/week3` — evaluation harness, full runs, and feature-extraction arm. Merged at Week 3 gate.
- `analysis/week4` — statistics, figures, error taxonomy, feature-extraction writeup.
- `paper/week5` — writing (preprint + thesis chapter scaffold).

Tag the dataset freeze: `git tag dataset-freeze-v1`.
Tag the results freeze: `git tag results-freeze-v1`.
Tag the arXiv submission: `git tag arxiv-submission-v1`.
Tag the metricHEALTH handoff: `git tag mh-handoff-v1` (when mh_integration/ artefacts are ready for the main thesis repo).
