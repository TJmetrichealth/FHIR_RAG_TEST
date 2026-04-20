# Project Plan — Paired-Data Comparison: Structured FHIR RAG vs. LLM-Narrative RAG for PSP Specialty Medication QA

**Working title:** *Paired-Data Comparison of Structured FHIR and LLM-Narrative Retrieval for Adherence-Indicator Question Answering in Canadian Patient Support Programs*

**Author:** Tirthesh Jani
**Type:** Empirical preprint (arXiv) **and** Phase 0 foundation study for the metricHEALTH FHIR R4B + ML Adherence research proposal
**Duration:** 5 weeks core + 4 weeks external buffer
**Status:** Planning — v3 dual-purpose pivot approved; see `07_DECISIONS_v2_FREE_STACK.md` (v3 addendum)

---

## 1. Executive Summary

This project produces the first controlled, paired-data comparison of structured-FHIR retrieval versus LLM-generated-narrative retrieval on adherence-indicator question answering for long-acting specialty medication regimens, framed around the kinds of questions Canadian Patient Support Program (PSP) case managers ask every day: persistence, proportion-of-days-covered (PDC), medication-possession-ratio (MPR), missed-dose detection, and next-scheduled-dose lookup.

The project serves two goals simultaneously:

1. **A standalone preprint** on arXiv (cs.CL / cs.IR) contributing a paired-data methodology, a FHIR-native retrieval baseline, a resource-aware retriever, and a complexity-stratified empirical result on adherence questions.

2. **Phase 0 of the metricHEALTH research proposal** — the side project's outputs directly feed four downstream metricHEALTH components: the Phase 1 R4B conformance validator is stress-tested against 200 bundles, System C is packaged as a case-manager Q&A prototype for Phase 4, the structured-vs-narrative finding pre-justifies Phase 3 feature-engineering choices for the ML adherence engine, and the question bank becomes the Phase 5 evaluation harness.

The contribution remains principally methodological (paired data holds information content constant across representations), engineering (a resource-aware FHIR retriever plus a feature-extraction comparison), and empirical (a complexity gradient test of where structure helps most). Deliverables are a public dataset, three retrieval systems, a feature-extraction comparison, an evaluation harness reusable by metricHEALTH, a preprint, and a reproducibility artefact.

---

## 2. Objectives and Success Criteria

### 2.1 Research objectives (in priority order)

| # | Objective | Success signal |
|---|---|---|
| **O1** | Demonstrate paired-data methodology that holds information content constant across structured-FHIR and narrative representations | Fidelity audit shows ≥90% of FHIR entities (medications, dose events, dates) recoverable from narratives |
| **O2** | Quantify the performance gap between structured-FHIR RAG and narrative RAG on adherence-indicator question answering | Statistically significant difference (paired bootstrap or McNemar) on ≥2 of 5 question families |
| **O3** | Characterise how the gap scales with regimen complexity (tiers 1→3) | Monotonic trend preferred; plateau or non-monotonic result still publishable as nuanced finding |
| **O4** | Show a resource-aware FHIR retriever beats a naive text-serialised FHIR retriever | ≥5 percentage-point absolute accuracy gain on tier-2/3 questions |
| **O5** | Produce an error taxonomy on temporal failures that explains *why* narratives underperform | 3–4 interpretable categories with ≥80% inter-rater agreement on a subsample |
| **O6** | Show that features extracted from structured FHIR are at least as predictive of adherence outcomes as features extracted from LLM narratives | Matched or higher AUC-ROC for structured-derived features on a held-out synthetic adherence classification task |

### 2.2 Publishable-outcome matrix

The plan is engineered so that multiple distinct outcomes each carry a paper. No single technical failure kills the preprint, and the metricHEALTH integration value is independent of publication outcome.

| Scenario | Paper still viable? | metricHEALTH value? | Framing |
|---|---|---|---|
| All six objectives succeed | ✅ Strong preprint | ✅ Full value | Confirmatory: structure wins across QA and feature extraction; gap widens with complexity; resource-awareness pays |
| O4 fails (resource-aware ≈ naive) | ✅ | ✅ | Primary claim holds; resource-awareness becomes secondary finding; System C still ships as a Phase 4 prototype |
| O3 plateaus | ✅ | ✅ | Report honestly; plateau itself contradicts "structure always scales," which is interesting |
| O6 null (features tie) | ✅ | ⚠️ Degraded | Paper unaffected; Phase 3 design decision reverts to "either works" rather than "structured wins" |
| Fidelity <85% (narratives too weak) | ⚠️ Degraded | ✅ | Fall back to templated-narrative ablation as primary condition; validator + System C + harness still deliverable |
| No statistical difference between any systems | ❌ Kill preprint | ⚠️ Partial | Null result weak for preprint but validator stress-test, feature comparison, and harness still useful to metricHEALTH |

### 2.3 Non-goals

- Not a new LLM architecture paper.
- Not a clinical-validity claim — synthetic data only; real-data follow-up happens post-REB in metricHEALTH Phase 3–4.
- Not a full RAG systems comparison — three systems, tightly scoped.
- Not a FHIR spec contribution.
- Not a replacement for the metricHEALTH Phase 3 ML adherence engine — the feature-extraction arm (O6) is a design-informing benchmark, not a production predictor.

---

## 3. Scope

### 3.1 In scope
- Synthea-generated synthetic patient population (~200)
- Custom specialty-regimen overlay (3 complexity tiers)
- LLM-generated narratives with fidelity verification
- Templated narratives as ablation ceiling
- 3 retrieval systems (narrative RAG, naive structured RAG, resource-aware structured RAG)
- ~120 programmatically-verifiable adherence-indicator questions across 5 PSP-grounded families
- Feature-extraction arm: adherence-outcome prediction from features derived from each of the three representations
- Every bundle validated against the metricHEALTH Phase 1 R4B conformance validator (reuses its code, reports conformance rates)
- System C packaged as a FastAPI endpoint that drops into metricCONNECT
- Single answer-generation LLM held constant across systems
- Evaluation: accuracy, recall@k, latency, tokens, error taxonomy, feature-extraction AUC
- Open-source release of dataset + code
- Question bank structured as a pytest-style regression harness reusable by metricHEALTH Phase 5

### 3.2 Out of scope
- Real-patient data (synthetic only)
- Multi-LLM generator comparison (one narrative LLM, one answer LLM, as set in v2 decisions)
- Fine-tuning experiments
- Clinical-reasoning questions beyond regimen/temporal/adherence
- Production deployment of the adherence classifier — that lives in metricHEALTH Phase 3
- Live FHIR server deployment — local FHIR bundles sufficient; Phase 2 is where the Azure FHIR endpoint lights up

---

## 4. Methodology Overview

Four tightly coupled components.

### 4.1 Dataset (paired design)
Each synthetic patient produces two parallel representations of the *same* clinical facts:
- **FHIR bundle** — Synthea base + specialty overlay (MedicationRequest, MedicationAdministration, Medication, CarePlan, Encounter, Patient, Practitioner), all validated against the metricHEALTH Phase 1 R4B conformance validator
- **LLM narrative** — generated from the FHIR bundle using a fixed prompt + model, fidelity-audited
- **Templated narrative** (ablation) — deterministic template rendering of the same FHIR bundle; represents "maximum fidelity" narrative ceiling

### 4.2 Complexity tiers
- **Tier 1 — Low**: Single long-acting injectable on fixed recurring schedule (e.g., q8w)
- **Tier 2 — Medium**: Cyclic regimens (e.g., weekly-for-N-weeks-then-rest) with "where in cycle?" reasoning
- **Tier 3 — High**: Multi-drug specialty regimens (biologic + oral adjunct + PRN rescue) with staggered or interdependent schedules

### 4.3 Question families (5, each grounded in a PSP adherence indicator, ~24 questions each)

The question families are reframed from the generic v1 categories into the actual operational questions a Canadian PSP case manager asks, each aligned with a canonical adherence metric:

1. **Next-dose lookup (next-scheduled-dose)** — "When is this patient's next scheduled administration?" Indicator: schedule adherence.
2. **Dose-history aggregation (MPR numerator)** — "How many doses have been administered in the past 90 days?" Indicator: MPR input.
3. **Coverage-window reasoning (PDC)** — "What proportion of the past 90 days was this patient covered by therapy?" Indicator: PDC.
4. **Missed-dose detection (gap detection)** — "Have any scheduled doses been missed in the past 90 days, and if so which?" Indicator: adherence failure events.
5. **Persistence / discontinuation signal** — "Is this patient still persistent on therapy, or is there evidence of discontinuation?" Indicator: persistence.

All ground truth computed programmatically from the FHIR bundle. **No LLM-as-judge, no manual scoring.** Adherence metric formulas (MPR, PDC, persistence) are implemented as pure Python functions over the bundle; these same functions become reusable feature extractors in §4.5.

### 4.4 Retrieval systems
- **System A — Narrative RAG**: Chunk narratives → embed → top-k retrieval → pass to answer LLM
- **System B — Structured RAG (naive)**: Serialize each FHIR resource to text → embed → top-k retrieval → same answer LLM
- **System C — Structured RAG (resource-aware)**: Typed filtering by resource type + reference traversal (MedicationRequest → Medication, Practitioner, Patient) + temporal pre-filter → then semantic search within the filtered set. Packaged as a FastAPI endpoint `mh_integration/case_manager_qa.py` that mounts into metricCONNECT.

Controlled variables (held constant across A/B/C): answer LLM, answer prompt, top-k budget, chunk token budget, embedding model, retrieval depth, temperature.

### 4.5 Feature-extraction arm
A fourth measurement — orthogonal to QA accuracy — addresses the Phase 3 metricHEALTH question "should the ML adherence engine consume structured FHIR features or narrative-derived features?"

- **Synthetic adherence outcome**: define a programmatic discontinuation-risk label from the bundle (e.g. "≥2 missed doses in final 60 days" or an equivalent gap-based rule). This is a synthetic label, honestly reported as such.
- **Three feature sets extracted from the same patients**:
  - **FS-Structured**: adherence metrics computed directly from the FHIR bundle (PDC, MPR, days-since-last-dose, etc.).
  - **FS-Narrative**: the same features, but extracted from the LLM narrative by an extraction prompt (LLM as extractor, not judge).
  - **FS-Aware**: features extracted via System C's resource-aware retrieval.
- **Model**: logistic regression and gradient-boosted trees (LightGBM), simplest honest baseline. Same hyperparameters across feature sets.
- **Metric**: AUC-ROC with paired bootstrap CIs on the same patient split.

This arm adds roughly 3–5 days of work (see §5), can be dropped first if the timeline tightens, and produces a standalone table + figure that tightens the preprint's claim from "QA works better with structure" to "QA and feature extraction both work better with structure."

---

## 5. Work Breakdown Structure

### Week 1 — Dataset construction + validator hookup
**Deliverables:**
- `data/synthea_base/` — 200 synthetic patients (raw Synthea output)
- `overlay/specialty_regimen_generator.py` — the ~200-line overlay assigning one of 3 tiers per patient
- `data/fhir_bundles/` — 200 enhanced FHIR bundles (one per patient)
- `mh_integration/r4b_validator.py` — shared validator module imported from the metricHEALTH Phase 1 codebase (or a standalone copy if the mH repo isn't accessible yet; reconvergence is planned)
- `reports/conformance_rates.md` — per-tier R4B conformance statistics on the 200 bundles
- `narratives/llm_narratives/` — LLM-generated narratives per bundle
- `narratives/templated_narratives/` — deterministic-template narratives (ablation)
- `questions/questions.jsonl` — ~120 questions across the 5 PSP-grounded adherence families with ground-truth functions + provenance pointers
- `reports/fidelity_audit.md` — per-narrative fidelity report

**Key tasks:**
- T1.1 Set up Synthea, generate 200 patients (1 day)
- T1.2 Build specialty-regimen overlay with 3 tiers (1.5 days)
- T1.3 Wire in the mH R4B validator; validate all 200 bundles; report conformance (0.5 day) — *new for v3*
- T1.4 Narrative generation prompt + iteration (1 day)
- T1.5 Fidelity audit script + iteration loop (1 day) — *gate: ≥90% fidelity before proceeding*
- T1.6 Templated-narrative generator (0.5 day) — *kill-switch if week 1 slips; defer to week 3 buffer*
- T1.7 Question bank generator (PSP adherence families) with programmatic ground truth; adherence metric functions (PDC, MPR, persistence) are reusable modules (1 day)
- T1.8 Dataset freeze + cryptographic hash + immutability commit

**Gate (end of week 1):** Dataset is frozen. No more edits to bundles, narratives, or questions after this point — modifications invalidate all downstream results.

---

### Week 2 — Retrieval systems (highest-risk week)
**Deliverables:**
- `systems/narrative_rag.py` — System A
- `systems/structured_rag_naive.py` — System B
- `systems/structured_rag_aware.py` — System C (the engineering novelty)
- `systems/common/` — shared answer-generation wrapper, chunking, embedding client
- `mh_integration/case_manager_qa.py` — FastAPI-packaged wrapper around System C, suitable for mounting into metricCONNECT
- `tests/smoke/` — one end-to-end test per system on a 10-patient sample

**Key tasks:**
- T2.1 Common infrastructure (embedding client, answer LLM wrapper, eval harness skeleton) — 1 day
- T2.2 System A (narrative RAG) — 0.5 day
- T2.3 System B (naive structured RAG) — 0.5 day
- T2.4 System C (resource-aware structured RAG) — 2 days *(main lift of the week)*
  - Typed retrieval index
  - Reference traversal graph
  - Temporal pre-filter
- T2.5 FastAPI packaging of System C into `mh_integration/case_manager_qa.py` (0.5 day) — *new for v3*
- T2.6 Smoke tests + bug fixes; **start System A's full evaluation as soon as its smoke test passes** (per v2 free-stack timeline) (1 day)

**Gate (end of week 2):** All three systems answer a sample-question smoke test end-to-end. System A evaluation started in background. Buffer: up to 2–3 days can be absorbed from week 3.

---

### Week 3 — Full evaluation + feature-extraction arm
**Deliverables:**
- `results/raw/` — per-question-per-system answer traces (JSONL, preserved verbatim)
- `results/scored.csv` — scored evaluation matrix
- `results/latency_tokens.csv` — cost/latency metrics per system
- `results/recall_at_k.csv` — retrieval-only metrics
- `results/feature_extraction/` — AUC-ROC tables for the three feature sets (new for v3)
- `features/extractors/` — feature extraction modules for each representation

**Key tasks:**
- T3.1 Complete full run of all 3 systems × 200 patients × ~120 questions (started in W2)
- T3.2 Scoring pass (programmatic, deterministic)
- T3.3 Stratified analyses (by complexity tier, by question family)
- T3.4 Retrieval-only analysis (recall@k independent of answer quality)
- T3.5 Full-run ablation with templated narratives on same question set
- T3.6 Feature-extraction arm: implement three extractors, train LGBM + logistic regression, paired bootstrap AUC (2 days) — *new for v3*

**Gate (end of week 3):** Results tables complete. All numbers in the paper from this point are fixed — any re-runs require written justification in the project log.

---

### Week 4 — Error analysis, ablations, figures
**Deliverables:**
- `analysis/error_taxonomy.md` — 3–4 categories of temporal failure with examples
- `analysis/templated_vs_llm_narrative.md` — ablation writeup
- `analysis/feature_extraction.md` — writeup of O6 results and their Phase 3 implications
- `figures/` — finalised figures (main results, complexity-stratified, retrieval recall, error distribution, feature-extraction AUC)
- `analysis/statistical_tests.md` — paired bootstrap / McNemar results with confidence intervals

**Key tasks:**
- T4.1 Sample 50 failure cases per system, categorise (0.5 day)
- T4.2 Inter-rater check on taxonomy via second-LLM triangulation only (per v2 decisions) (0.5 day)
- T4.3 Statistical tests (paired bootstrap + McNemar) (0.5 day)
- T4.4 Figure generation (matplotlib, 6–8 final figures) (1 day)
- T4.5 Feature-extraction writeup with direct Phase 3 implications (0.5 day)
- T4.6 Sensitivity analyses: top-k sweep, chunk-size sweep (optional, 1 day)

---

### Week 5 — Writing, repo cleanup, dual-framing, submission
**Deliverables:**
- `paper/main.tex` — full preprint
- `paper/main.pdf` — compiled preprint
- `thesis_chapter/` — same content, Phase-0 framing scaffold for future metricHEALTH thesis chapter
- `reproducibility/README.md` — repro guide
- `LICENSE` — dataset + code licence (Apache-2.0 + CC-BY-4.0 per v2)
- arXiv submission
- Optional: project page (GitHub README + results table)

**Key tasks:**
- T5.1 Draft intro + related work (1 day)
- T5.2 Draft methods + dataset + systems (1 day)
- T5.3 Draft results + discussion + limitations (1 day)
- T5.4 Repo cleanup, dockerfile, one-command repro (0.5 day)
- T5.5 Produce thesis-chapter scaffolding of same content with Phase 0 framing (0.5 day) — *new for v3*
- T5.6 Internal review pass (0.5 day)
- T5.7 arXiv submission (0.5 day)

---

## 6. Dependencies and Resources

### 6.1 External dependencies
| Dependency | Version | Notes |
|---|---|---|
| Python | 3.11+ | Match metricADVANCED stack for transfer value |
| Synthea | latest | Java dependency — ensure JRE installed |
| `fhir.resources` | ≥8.0 | R4B pydantic models (already in metricFHIR SDK) |
| metricHEALTH R4B validator | `mh_integration/r4b_validator.py` | Reuses Phase 1 Consent + pre-write validation code; standalone copy acceptable if mH repo access pending |
| Narrative-gen LLM | Llama 3.3 70B via Groq free tier | Per v2 decisions |
| Answer LLM | Qwen 3 32B via Groq free tier | Per v2 decisions |
| Embedding model | `BAAI/bge-large-en-v1.5` local | Per v2 decisions |
| Vector store | `chromadb` or `faiss` | Local-only, no external service needed |
| LightGBM | ≥4.0 | Feature-extraction arm |
| scikit-learn | ≥1.4 | Logistic regression baseline for feature-extraction arm |

### 6.2 Compute
- Laptop/workstation sufficient for dataset + evaluation + feature-extraction arm
- API spend: $0 CAD per v2 free-stack decisions
- GPU not required (CPU-based LightGBM is fine for ~200-patient samples)

### 6.3 Storage
- ~1 GB for dataset + narratives + results + feature extractions
- Git LFS or similar for the dataset release

---

## 7. Risk Register (v3 extended)

| # | Risk | L | I | Mitigation | Owner | Trigger |
|---|---|---|---|---|---|---|
| R1 | Narrative fidelity stays <90% after iteration | M | H | Use templated narratives as primary; reframe paper around structure-vs-template | Researcher | End of week 1 |
| R2 | Complexity gradient non-monotonic | M | M | Report honestly; paired-data methodology contribution still stands | Researcher | Week 3 results |
| R3 | Resource-aware retriever fails to beat naive | L | M | Primary claim unaffected; downgrade to secondary finding; System C still ships as Phase 4 prototype | Coder | Week 3 results |
| R4 | Week 2 (retrieval systems) slips | H | H | Absorb 2–3 days from week 3; defer sensitivity analyses and feature-extraction arm | Coder | Midweek 2 |
| R5 | API cost overrun | L | L | Free-stack; Groq rate limits are the real bottleneck — mitigation R13 | Coder | Pre-week 3 |
| R6 | Ground-truth generator has bugs | M | H | Hand-audit 20 questions against bundle before full run; unit-test the generator; adherence metric functions additionally unit-tested against known-case fixtures | Reviewer | Week 1 gate |
| R7 | LLM answer parsing flakiness | M | M | Constrained decoding / JSON-mode / structured outputs; re-run on parse failure | Coder | Week 2 smoke |
| R8 | Synthea medication module too limited for specialty regimens | H | L | Already mitigated by custom overlay (planned) | Researcher | Week 1 |
| R9 | arXiv endorsement delay (if first submission to a category) | L | L | Identify endorser early | Author | Week 4 |
| R10 | Venue submission timing conflicts with metricHEALTH deliverables | M | M | Preprint on arXiv first; thesis-chapter framing produced in Week 5 as scaffold | Author | Week 5 |
| R11 | Question bank has ambiguity in natural language (even if ground truth is clean) | M | M | Write 2 paraphrases per question; verify answer invariance across paraphrases | Researcher | Week 1 |
| R12 | Embedding/chunking choices become confounds across systems | M | H | Hold all embedding/chunking choices constant; report config explicitly | Reviewer | Week 2 gate |
| R13 | Groq free tier throttled or deprecated mid-project | M | H | Fallback to Cerebras / Gemini free tier or local Ollama | Coder | Ongoing |
| **R14** | mH R4B validator not yet implemented or unstable at W1 start | M | M | Standalone validator copy in `mh_integration/`; reconverge with Phase 1 later | Coder | Week 1 |
| **R15** | Feature-extraction arm (O6) produces null result | M | L | O6 is lowest priority; null is honest, still informs Phase 3 ("either works"); drop first if timeline tightens | Statistician | Week 3 |
| **R16** | Dual-framing creates confused reviewer expectations | L | M | Preprint is tightly scoped to paired-data methodology; metricHEALTH framing lives in thesis chapter only, not in arXiv abstract | Author | Week 5 |
| **R17** | Project serves two masters and schedule slips hurt both | M | M | Pre-committed drop order if timeline tightens: (1) feature-extraction arm, (2) System C FastAPI packaging, (3) sensitivity sweep. Paper must stand alone on paired-data methodology. | Planner | Ongoing |

L = Likelihood, I = Impact. Rows R14–R17 are new for v3.

---

## 8. Budget (API / Infrastructure)

Per v2 free-stack decisions: **$0 CAD total**.

The previous paid-stack budget is kept for audit trail in `06_DECISIONS_ANSWERED.md`. See `07_DECISIONS_v2_FREE_STACK.md` for the current free-stack configuration (Groq free tier + local embeddings + $0 spend).

The v3 dual-purpose pivot adds no budget line: the R4B validator is reused code, System C's FastAPI packaging is local, and LightGBM + scikit-learn are both free local libraries.

---

## 9. Reproducibility Checklist

- [ ] Deterministic seeds for Synthea + overlay
- [ ] Pinned model versions + snapshot IDs (Llama 3.3 70B, Qwen 3 32B, BGE-large v1.5)
- [ ] All LLM calls cached (response hash per prompt)
- [ ] Question bank versioned; ground truth regenerable from bundles
- [ ] Feature extractors versioned; adherence label regenerable from bundles
- [ ] One-command repro: `make reproduce` runs everything end-to-end (eval + feature extraction)
- [ ] Docker container for environment
- [ ] Released dataset under an open licence (CC-BY-4.0, pending employer clearance per v2)
- [ ] README explicitly lists "things we did NOT control for" (honesty clause)
- [ ] Question bank packaged as `pytest`-style regression harness reusable by metricHEALTH Phase 5

---

## 10. Publication Strategy

Same work, two framings — no double-publication issue because the arXiv preprint is tightly scoped to the paired-data methodology and the thesis chapter includes context the preprint does not.

- **arXiv preprint** (target 31 May 2026) — cs.CL + cs.IR cross-list. Frames the work as a paired-data methodology contribution. metricHEALTH appears only as an affiliation line; no platform claims.
- **Thesis chapter scaffold** (produced in Week 5, not published externally) — same experiments and results, framed as "Phase 0: benchmarking representation choices before committing to the ML engine design." Included later in the full metricHEALTH thesis / full-venue submission.
- **Short workshop paper** candidates (based on timing):
  - ML4H workshop at NeurIPS (primary target, per v2)
  - ACL ClinicalNLP workshop
  - AMIA Informatics Summit
- **Full venue** candidates (extend to 8–9 pages with real de-identified metricHEALTH data post-REB):
  - JAMIA (primary target, per v2)
  - JMIR Medical Informatics
  - npj Digital Medicine
- **Strategic positioning** in preprint discussion: frame as "first paired-data comparison" and "design-informing benchmark for downstream clinical ML systems" — avoids overclaiming.

---

## 11. Governance

- **Decision log** — `docs/decisions.md` captures every material choice (model, k, chunk size, fidelity threshold, feature-extraction arm scope)
- **Weekly checkpoint** — end-of-week self-review against plan; slip signals flagged early
- **External review** — one pass before arXiv submission (reviewer agent per `01_CLAUDE_CODE_AGENT_PLAN.md`)
- **Change control** — after the week-1 dataset freeze and week-3 results freeze, changes require written justification in the decision log
- **Drop order under slip** (R17): feature-extraction arm → System C FastAPI packaging → sensitivity sweep. Paper must stand alone on paired-data methodology.

---

## 12. Post-submission

- [ ] Release code + dataset on GitHub (Apache-2.0 + CC-BY-4.0, pending employer clearance)
- [ ] Zenodo DOI for dataset
- [ ] Tweet thread / short blog post summarising findings
- [ ] Hand over System C's FastAPI wrapper to metricHEALTH Phase 4 planning
- [ ] Hand over question bank + adherence metric modules to metricHEALTH Phase 5 planning
- [ ] Plan follow-up paper: extending to *real* de-identified metricHEALTH data post-REB (ties into the full metricHEALTH thesis)

---

## 13. metricHEALTH Integration Map (new for v3)

Concrete artefacts produced by this project that feed into the metricHEALTH research proposal phases:

| Side-project artefact | metricHEALTH phase | Use |
|---|---|---|
| 200 validated FHIR bundles × 3 complexity tiers | Phase 1: R4B validator | Stress-test the pre-write validation layer; report conformance rates as Phase 1 Milestone 1 evidence |
| `mh_integration/case_manager_qa.py` (System C wrapper) | Phase 4: Dashboard | FastAPI endpoint mounts into metricCONNECT; demonstrated on synthetic data here, deployed on real de-identified data post-REB |
| Structured-vs-narrative feature-extraction finding (O6) | Phase 3: Feature engineering | Empirical justification for ML engine feature-representation choice; saves rework cycles |
| `questions/questions.jsonl` + adherence metric modules | Phase 5: Evaluation | `pytest`-style regression harness any metricHEALTH change can be re-run against |
| Domain expertise in PSP adherence indicators (PDC, MPR, persistence) | Phase 3: Feature engineering, Phase 5: Evaluation | Common vocabulary across side-project paper and main thesis |

This table is the single source of truth for what the side project owes metricHEALTH. If any row becomes unviable, the risk register entry for it (R14 for the validator, R15 for O6, R17 for the whole dual-purpose) fires.
