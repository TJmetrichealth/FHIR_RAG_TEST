# Finalized Decisions — Open Questions Resolved (v2: Free Stack) + v3 Dual-Purpose Addendum

**Status:** v2 supersedes v1 (`06_DECISIONS_ANSWERED.md`). Changes from v1:
1. **Sole-authored** — Dr. Sykes removed as co-author; Ruwindhu Aidi remains in acknowledgements only.
2. **Zero-cost stack** — all paid APIs replaced with free-tier / open-weights / local alternatives. Total project cost: **$0 CAD.**
3. **Timeline** — evaluation wall time stretches due to free-tier rate limits; mitigated by starting eval in Week 2 against System A as soon as its smoke test passes, instead of waiting for all three systems.

Everything else from v1 (start date, licensing, framing, methodology, etc.) is unchanged.

**v3 addendum (appended below, same date):** the dual-purpose pivot — six modifications that turn the side project into a preprint *plus* Phase 0 of the metricHEALTH research proposal. v3 does not change the v2 free-stack technical choices; it layers integration decisions on top.

**Date of decisions:** 19 April 2026
**Supersedes:** `06_DECISIONS_ANSWERED.md` (v1 paid-stack version) — kept for audit trail, not for execution.

---

## Summary Decision Table (v2 + v3)

| # | Question | Decision | Cost | Confidence |
|---|---|---|---|---|
| **A1** | Narrative-generation LLM | **`llama-3.3-70b-versatile` via Groq free tier** | $0 | High |
| **A2** | Answer-generation LLM | **`qwen-3-32b` via Groq free tier** (different training lineage than Llama → vendor separation preserved) | $0 | High |
| **A3** | Embedding model | **`BAAI/bge-large-en-v1.5` via sentence-transformers, local**; **MedCPT** locally for robustness appendix | $0 | High |
| **A4** | Budget ceiling | **$0 CAD** | — | High |
| **A5** | Start date | **Monday 27 April 2026** | — | Confirm |
| **B1** | Authorship | **Sole-authored: Tirthesh Jani.** Ruwindhu Aidi in acknowledgements | — | High |
| **B2** | metricHEALTH relationship | **Light affiliation in preprint abstract**; **v3: parallel thesis-chapter scaffold reframes as Phase 0** (not published externally) | — | High |
| **B3** | Target venue | **arXiv → ML4H 2026 at NeurIPS → JAMIA extended later** | — | High |
| **B4** | Licensing | **Code: Apache-2.0. Dataset: CC-BY-4.0** | — | Subject to employer clearance (v3-expanded scope; see F6) |
| **B5** | Domain realism | **(b) Plausible class-level descriptors** | — | High |
| **C1** | Runs per question | **Single run, temperature 0** | — | High |
| **C2** | Top-k / chunk | **k=5, chunk=500; sensitivity sweep in appendix** | — | High |
| **C3** | Inter-rater taxonomy | **TJ single-rater + triangulation via different LLM as supporting signal only** | — | Medium |
| **C4** | API constraints | **Groq free tier; verify free-tier privacy terms OK for synthetic data (they are)** | — | High |
| **C5** | Reproducibility | **Dockerfile + `make reproduce`** | — | High |
| **D1** | Fidelity threshold | **90% initial gate** | — | High |
| **D2** | Question balance | **Same 120 questions for all patients; N/A is a valid answer**; **v3: five question families reframed as PSP adherence indicators — Next-dose lookup, Dose-history aggregation (MPR numerator), Coverage-window reasoning (PDC), Missed-dose detection, Persistence** | — | High |
| **D3** | Reference date | **Varied per patient (uniform over ±window around regimen start)** | — | High |
| **E1** | REB determination | **Parallel-track in Week 1** | — | Action required |
| **E2** | Employer IP clearance | **Request this week**; **v3 scope addition: handoff of `mh_integration/` artefacts to metricHEALTH codebase** | — | Action required |
| **G1** | R4B validator integration | **`mh_integration/r4b_validator.py`** reuses or prototypes the metricHEALTH Phase 1 validator; every synthetic bundle passes through it | — | High (v3) |
| **G2** | System C productisation | **Packaged as FastAPI endpoint `mh_integration/case_manager_qa.py`** — prototype-level (per F3 recommendation), mounts into metricCONNECT later | — | High (v3) |
| **G3** | Feature-extraction arm (O6) | **Three feature sets × two classifiers × paired bootstrap AUC**; minimum scope per F2 recommendation (3 days); dropped first under R17 | — | High (v3) |
| **G4** | Adherence label design (O6) | **Composite: ≥2 consecutive missed doses in final 60d OR median gap >1.5× prescribed interval** — documented as synthetic proxy (per F5) | — | Medium (v3) |
| **G5** | Question bank reuse | **Packaged as pytest-style harness** for metricHEALTH Phase 5 regression | — | High (v3) |
| **G6** | Thesis-chapter scaffold | **Week 5 deliverable: outline-depth per F4 recommendation**, framing the same experiments as Phase 0 of the metricHEALTH research proposal | — | High (v3) |

---

## Why this stack is free — and why that's fine

### The free stack

| Component | Free option | Alternative (no credit card required) |
|---|---|---|
| Narrative gen LLM | Groq Llama 3.3 70B | Google AI Studio Gemini 2.5 Flash; Cerebras free tier; HF Inference API |
| Answer LLM | Groq Qwen 3 32B | Groq GPT-OSS 20B; local Llama 3.1 8B via Ollama |
| Embeddings | `BAAI/bge-large-en-v1.5` local | `all-mpnet-base-v2`, `all-MiniLM-L6-v2` local |
| Medical-embedding robustness | MedCPT local via HuggingFace | ClinicalBERT variants local |
| Vector store | ChromaDB local | FAISS local |
| Templated-narrative ablation | Deterministic Python (no LLM) | — |
| Feature-extraction classifiers (v3) | LightGBM + scikit-learn, all local | xgboost local as sanity check |

**Signup requirements:** Groq account (Google sign-in, **no credit card**), HuggingFace account (free, for downloading model weights).

**Local hardware required:** Any laptop with ≥8 GB RAM. Embeddings run on CPU (slow but fine for 200 patients × 46 FHIR resource types). If you have any GPU at all, use it for embedding indexing to cut time to minutes. Feature-extraction arm runs comfortably on CPU for 200 patients.

### Scientific integrity check — does going free weaken the paper?

**No, and arguably strengthens it.** Three reasons:

1. **Reproducibility becomes a strength, not a footnote.** Anyone in the world can re-run this study for $0. Closed-model snapshots (GPT-4, Claude) get deprecated and pull the rug from under preprints. Open-weights models on Groq are archived by Meta and Alibaba and will be reproducible for years.

2. **Vendor separation is actually cleaner.** Llama 3.3 (Meta) for narrative vs. Qwen 3 (Alibaba) for answering removes the self-consistency confound *and* crosses two independent training pipelines from different continents. A skeptical reviewer cannot argue "both models share training data."

3. **The paper's claim is about representations, not model strength.** The core finding — structured FHIR RAG beats LLM-narrative RAG on adherence-indicator questions — does not depend on the narrative generator being the strongest possible LLM. It depends on the narrative generator being *good enough* to clear the 90% fidelity gate. Llama 3.3 70B is demonstrably good enough; if it isn't on this domain, the fidelity audit will catch it in Week 1 and we fall back to templated narratives.

4. **(Minor honesty note for Methods section):** A paragraph in limitations should acknowledge that a more powerful narrative generator (GPT-4, Claude) *might* produce higher-fidelity narratives that partially close the gap. The reader will be satisfied by the ablation against templated narratives (which are "maximum fidelity" narratives by construction) — if structured beats even templated, the conclusion survives any LLM strength argument.

### Free-tier privacy terms — checked and OK

Groq's free-tier terms of service permit use of prompt data for service improvement. **This is irrelevant here because the dataset is fully synthetic.** No real PHI ever touches the API. Still document this explicitly in the repo README and the REB exemption request (§E1) for full transparency.

Google AI Studio free tier has a more aggressive 3-year retention-for-review clause. We are not using it, but worth noting why: if you *were* using real de-identified data in a follow-up study, Google's free tier would be disqualified and Groq would remain acceptable.

---

## Timeline impact — rate limits stretch Week 3

### The math

Groq free tier (per API key):
- **30 requests/minute** for both Llama 3.3 70B and Qwen 3 32B
- **6,000 tokens/minute** (the real bottleneck for our ~650-token calls)
- **14,400 requests/day** per model (separate counters)

For our workload:
- Narrative generation: 200 calls → ~20 minutes. Trivial.
- Full evaluation: 3 systems × 120 questions × 200 patients = **72,000 answer-LLM calls**
- At ~9 calls/min effective throughput (TPM-bound) = ~134 hours = **~5.6 days continuous**
- Templated-narrative ablation adds ~24,000 calls = **~1.9 days**
- Hyperparameter sweep (appendix) adds ~14,000 calls = **~1.1 days**
- **v3 feature-extraction narrative extractor** adds ~200 calls (one extraction per patient, not per question) = ~25 minutes. Trivial addition.

**Total answer-LLM runtime if serialised: ~8.6 days.** This doesn't fit cleanly in Week 3 alone.

### Mitigation (built into revised plan)

**Start evaluation in Week 2, not Week 3.** As soon as System A's smoke test passes mid-Week 2, start its full evaluation running in background. Same for B and C. By end of Week 3, all runs are complete and all results are frozen.

Revised Week 2–3 overlap:

| Day | Week 2 primary work | Background evaluation |
|---|---|---|
| Mon W2 | Common infrastructure (shared wrappers) | — |
| Tue W2 | System A (Narrative RAG) built | — |
| Wed W2 | System A smoke test passes | **System A evaluation starts (runs ~2 days)** |
| Thu W2 | System B (Naive Structured RAG) built | System A eval running |
| Fri W2 | System B smoke test, System C started, `mh_integration/case_manager_qa.py` scaffolded | **System B evaluation starts** |
| Mon W3 | System C completed | System A done, System B running |
| Tue W3 | System C smoke test passes; feature extractors built | **System C evaluation starts** |
| Wed W3 | Templated-narrative ablation starts | System B done, System C running |
| Thu W3 | Hyperparameter sweep starts; feature-extraction arm runs (CPU, parallel to LLM runs) | System C done, templated running |
| Fri W3 | All runs complete — results frozen | All done |

If the rate limits are worse in practice than advertised (Reddit threads suggest occasional throttling), the scope fallback is: **reduce to 100 patients × 120 questions** (36,000 total answer calls → ~2.8 days). Statistical power for paired tests at 100 patients is still comfortable for detecting meaningful effect sizes.

### Optional speedup (skip unless needed)

If you have access to a laptop or desktop GPU (even an 8 GB consumer card), you can add **local Llama 3.1 8B inference via Ollama** as a fourth parallel worker. This is genuinely free, has no rate limit, and gives you an independent answer-LLM channel. *Only do this if Groq free tier proves too slow — it adds setup overhead.*

---

## What changes in the pack (v2, originally listed)

### `00_PROJECT_PLAN.md`
- **§6 Dependencies table:** swap GPT-4 Azure → Groq Llama 3.3 70B; swap Claude Sonnet → Groq Qwen 3 32B; swap text-embedding-3-large → local BGE-large
- **§8 Budget:** total = $0
- **§5 Week 2/3 WBS:** note the evaluation-starts-in-Week-2 overlap
- **§7 Risk register:** added R13 "Groq free tier throttled or deprecated mid-project"

### `01_CLAUDE_CODE_AGENT_PLAN.md`
- `retrieval-engineer` system prompt: reference Qwen 3 32B via Groq; all clients retry on HTTP 429 with exponential backoff
- `evaluator` system prompt: schedule evaluation runs to start as soon as each system's smoke test passes

### `03_PAPER_DRAFT_STRUCTURE.md`
- Methods section explicitly names the open-weights models and positions the choice as a **reproducibility decision**, not a cost-cutting one
- Limitations section: "Our narrative generator is Llama 3.3 70B, a strong but not frontier-class model. A more powerful commercial LLM might produce higher-fidelity narratives. The templated-narrative ablation, which represents maximum achievable fidelity, addresses this concern."

---

## v3 Addendum — Dual-Purpose Pivot (2026-04-19)

**What changed:** The project was originally framed as "adjacent but independent" of the metricHEALTH research proposal. On review, that framing was too conservative — the same 5–9 weeks of work can produce a preprint *and* four concrete artefacts that drop into metricHEALTH (validator stress-test, case-manager Q&A prototype, feature-extraction justification for Phase 3, reusable Phase 5 harness).

v3 layers six modifications on top of v2 without changing v2's technical stack or its $0 budget.

### G1 — R4B validator integration

**Decision:** Every synthetic bundle passes through `mh_integration/r4b_validator.py`, which either imports the metricHEALTH Phase 1 R4B pre-write conformance validator (preferred) or prototypes one using `fhir.resources` R4B pydantic models (fallback if Phase 1 hasn't started at W1 start).

**Output artefact:** `results/conformance_rates.csv` — per-tier R4B conformance statistics, reported in paper appendix and reused as metricHEALTH Phase 1 Milestone 1 evidence.

**Cost:** $0 (local validator, no API calls).

---

### G2 — System C packaged for metricCONNECT

**Decision:** System C (resource-aware structured RAG) is packaged as a FastAPI endpoint at `mh_integration/case_manager_qa.py` — prototype-level depth per F3 recommendation (proper request/response schema, input validation, structured logging; no auth/rate-limiting — that's for the metricHEALTH Phase 4 team to harden).

**Output artefact:** A mountable FastAPI app the Phase 4 dashboard can integrate. Demonstrated on synthetic data in the preprint; deployed on real de-identified data post-REB in metricHEALTH.

**Cost:** $0.

---

### G3 — Feature-extraction arm (new objective O6)

**Decision:** Add a fourth measurement to the preprint — how well features derived from each representation predict a synthetic adherence outcome. Minimum scope per F2:
- Three feature sets: FS-Structured (direct from FHIR bundle), FS-Narrative (extracted from LLM narrative via extraction prompt), FS-Aware (extracted via System C's resource-aware retrieval).
- Two classifiers: LightGBM and logistic regression.
- Paired design: same 200-patient split across feature sets.
- Metric: AUC-ROC with paired bootstrap CIs.

**Output artefact:** `results/feature_extraction/*.csv` + `analysis/feature_extraction.md`. Paper Results §7.8. Direct Phase 3 design justification ("structured features beat narrative-derived features on adherence prediction AUC" OR honestly "they tie — either works").

**Cost:** ~200 additional narrative-extraction LLM calls (~25 minutes Groq wall time, still $0). Classifiers run locally on CPU.

---

### G4 — Synthetic adherence outcome label

**Decision:** Composite rule per F5 recommendation — a patient is labelled "discontinuation-risk positive" if they have ≥2 consecutive missed doses in the final 60 days OR a median dose gap in the final 90 days exceeding 1.5× the prescribed interval. Documented in methods as a synthetic proxy, not a validated clinical outcome.

**Cost:** $0 (label is deterministic from the FHIR bundle).

---

### G5 — Question bank as reusable harness

**Decision:** Question bank packaged as a pytest-style suite in `questions/pytest_harness/` with FHIR-bundle fixtures, so any change to the metricHEALTH FHIR gateway, ML adherence engine, or case-manager QA endpoint can be re-run against the same 120 questions to check for performance drift. This is the metricHEALTH Phase 5 evaluation harness.

**Cost:** $0 (packaging only, no new experiments).

---

### G6 — Thesis-chapter scaffold

**Decision:** In Week 5, produce `thesis_chapter/phase_0.md` — same experiments and results, framed as "Phase 0: benchmarking representation choices before committing to the ML engine design." Not published externally. The preprint abstract remains metricHEALTH-free (R16 mitigation).

**Outline-depth per F4 recommendation**; expanded to draft-depth only if Week 5 has slack. This is insurance — it captures the framing decisions while the project is fresh so the future thesis writeup is easier.

**Cost:** $0. Adds 0.5 days to Week 5 (T5.5 in the revised WBS).

---

### v3 new risks (appended to §7 of `00_PROJECT_PLAN.md`)

| # | Risk | L | I | Mitigation |
|---|---|---|---|---|
| R14 | mH R4B validator not yet implemented or unstable at W1 start | M | M | Standalone validator copy in `mh_integration/`; reconverge with Phase 1 later |
| R15 | Feature-extraction arm (O6) produces null result | M | L | O6 is lowest priority; null is honest, still informs Phase 3 ("either works"); drop first if timeline tightens |
| R16 | Dual-framing creates confused reviewer expectations | L | M | Preprint is tightly scoped to paired-data methodology; metricHEALTH framing lives in thesis chapter only, not arXiv abstract |
| R17 | Project serves two masters and schedule slips hurt both | M | M | Pre-committed drop order: (1) feature-extraction arm, (2) System C FastAPI packaging, (3) sensitivity sweep. Paper must stand alone on paired-data methodology |

---

### v3 new open questions (now in `05_OPEN_QUESTIONS.md` Block F)

- F1: R4B validator availability at Week 1 start
- F2: Feature-extraction arm scope (resolved → minimum / F2(a))
- F3: System C FastAPI packaging depth (resolved → prototype / F3(b))
- F4: Thesis-chapter scaffold depth (resolved → outline / F4(a), upgrade if slack)
- F5: Synthetic adherence label design (resolved → composite / F5(c) per G4)
- F6: Employer clearance scope extension (action required — revise E2 request)

---

## Action items (v2 + v3)

| Item | Action |
|---|---|
| **A5** | Confirm start date Monday 27 April 2026, or shift |
| **B4 / F6** | Employer IP clearance before licence commitment — **revise scope under v3** to include `mh_integration/` handoff |
| **C4** | Confirm employer policy allows free-tier API use for synthetic-data research (should be trivial approval) |
| **F1** | Confirm whether Phase 1 R4B validator is accessible at Week 1 start |
| **Groq signup** | Create account at [console.groq.com](https://console.groq.com) before Week 1 |
| **Hardware check** | Confirm you have at least 8 GB RAM for local embeddings; any GPU is a bonus |

---

## One-line summary (v2 + v3)

> *"Fully free, zero-cost, open-weights stack: Llama 3.3 70B (narrative) + Qwen 3 32B (answer) on Groq + local BGE-large embeddings. Sole-authored TJ. Preprint scoped as standalone paired-data methodology + parallel thesis-chapter scaffold reframing as metricHEALTH Phase 0. Question bank grounded in five PSP adherence indicator families. Every bundle passes through the mH R4B validator; System C packaged as a FastAPI endpoint for metricCONNECT; new feature-extraction arm compares structured / narrative / aware features on adherence prediction. Start 27 April 2026, arXiv 31 May 2026, $0 CAD."*
