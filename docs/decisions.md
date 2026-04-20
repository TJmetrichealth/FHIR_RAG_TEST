# Decisions Log

**Append-only.** Earlier entries are never edited — only superseded by later entries. Every material choice (model, k, chunk size, temperature, fidelity threshold, dataset freeze, etc.) must appear here with a timestamp and rationale.

Format per entry:
```
## YYYY-MM-DD — <short title>
**Decision:** ...
**Alternatives considered:** ...
**Rationale:** ...
**Supersedes:** (optional) prior entry date/title
```

---

## 2026-04-19 — v2 Free-Stack Decisions (from docs/07_DECISIONS_v2_FREE_STACK.md)

Seeded from the finalised decisions table. Full rationale lives in `docs/07_DECISIONS_v2_FREE_STACK.md`.

| # | Question | Decision |
|---|---|---|
| A1 | Narrative-generation LLM | `llama-3.3-70b-versatile` via Groq free tier |
| A2 | Answer-generation LLM | `qwen-3-32b` via Groq free tier |
| A3 | Embedding model | `BAAI/bge-large-en-v1.5` local via sentence-transformers; MedCPT local for robustness appendix |
| A4 | Budget ceiling | $0 CAD |
| A5 | Start date | Monday 27 April 2026 |
| B1 | Authorship | Sole-authored: Tirthesh Jani; Ruwindhu Aidi in acknowledgements |
| B2 | metricHEALTH relationship | Light — affiliation only |
| B3 | Target venue | arXiv → ML4H 2026 at NeurIPS → JAMIA extended |
| B4 | Licensing | Code: Apache-2.0; Dataset: CC-BY-4.0 (pending employer clearance) |
| B5 | Domain realism | Plausible class-level descriptors (no real drug names) |
| C1 | Runs per question | Single run, temperature 0 |
| C2 | Top-k / chunk | k=5, chunk=500 tokens; sensitivity sweep in appendix (k ∈ {3,5,10}, chunk ∈ {300,500,800}) |
| C3 | Inter-rater taxonomy | TJ single-rater; triangulation via different LLM as supporting signal only |
| C4 | API constraints | Groq free tier (synthetic data; privacy terms OK) |
| C5 | Reproducibility | Dockerfile + `make reproduce` |
| D1 | Fidelity threshold | 90% initial gate; drop to 85% only after 3 prompt iterations cluster at 87–89% |
| D2 | Question balance | Same 120 questions for all patients; "N/A" is a valid, scored answer |
| D3 | Reference date | Varied per patient, uniform over [regimen_start − 30d, regimen_start + 90d] |

**Supersedes:** v1 paid-stack table in `docs/06_DECISIONS_ANSWERED.md` (kept for audit trail only).

**Pending user confirmation:** B4 licence (employer IP clearance), A5 start date.

---

## 2026-04-19 — v3 Dual-Purpose Pivot

**Decision:** Reframe the side project as both a standalone arXiv preprint *and* Phase 0 of the metricHEALTH research proposal. Six concrete modifications layered on top of v2 without changing v2's technical stack or $0 budget. Full rationale lives in `docs/07_DECISIONS_v2_FREE_STACK.md` (v3 addendum section).

| Ref | Modification | Decision |
|---|---|---|
| G1 | R4B validator integration | Every synthetic bundle validated via `mh_integration/r4b_validator.py` — reuses metricHEALTH Phase 1 pre-write R4B validator where available; standalone copy if Phase 1 not yet started. Per-tier conformance rates reported in paper + reused as Phase 1 Milestone 1 evidence. |
| G2 | System C for metricCONNECT | System C (resource-aware structured RAG) packaged as FastAPI endpoint at `mh_integration/case_manager_qa.py`. Prototype-level depth (per F3 recommendation): proper schema, input validation, structured logging; no auth/rate-limiting (Phase 4 team hardens). |
| G3 | Feature-extraction arm (O6) | Added as new research objective. Three feature sets (FS-Structured, FS-Narrative, FS-Aware) × two classifiers (LightGBM, logistic regression) × paired bootstrap AUC on a synthetic adherence classification task. Minimum-scope version per F2. |
| G4 | Synthetic adherence label | Composite rule per F5: `(≥2 consecutive missed doses in final 60d) OR (median dose gap in final 90d > 1.5× prescribed interval)`. Documented as synthetic proxy, not validated clinical outcome. |
| G5 | Question bank as harness | Question bank structured as pytest-style suite with FHIR-bundle fixtures in `questions/pytest_harness/`. Reusable as metricHEALTH Phase 5 regression harness. |
| G6 | Thesis-chapter scaffold | Week 5 deliverable: `thesis_chapter/phase_0.md` — outline-depth scaffold per F4, framing same experiments as "Phase 0: benchmarking representation choices before committing to the ML engine design." Not published externally. |

**Question-family reframe (refines D2 from v2):** The five question families are reframed from generic categories (temporal lookup, temporal comparison, regimen compliance, regimen aggregation, cross-resource reasoning) to the five PSP adherence indicator families case managers actually ask about:
1. Next-dose lookup (schedule adherence)
2. Dose-history aggregation (MPR numerator)
3. Coverage-window reasoning (PDC)
4. Missed-dose detection (gap detection)
5. Persistence / discontinuation signal (persistence)

Adherence metric functions (PDC, MPR, persistence) live in `features/adherence_metrics.py` as shared code between ground-truth generation and feature-extraction arm.

**New risks added to register (project plan §7):**
- R14: mH R4B validator not yet implemented at Week 1 start — standalone copy mitigation
- R15: Feature-extraction arm null result — still informs Phase 3 ("either works"); lowest-priority objective
- R16: Dual-framing confuses reviewers — preprint abstract does not reference metricHEALTH (thesis chapter only)
- R17: Project serves two masters — pre-committed drop order under schedule pressure: (1) feature-extraction arm, (2) System C FastAPI packaging, (3) sensitivity sweep. Paper must stand alone on paired-data methodology.

**B2 clarification (refines v2 B2):** The preprint itself retains "light affiliation only" framing — metricHEALTH does not appear in the abstract. The v3 pivot adds a *parallel* thesis-chapter scaffold (G6) that reframes the same experiments under a Phase 0 framing. The scaffold is not externally published; it is insurance for the eventual metricHEALTH thesis.

**E2 scope extension (refines v2 E2):** Employer clearance request extended to cover handoff of `mh_integration/` artefacts from the preprint repo back into the metricHEALTH codebase. See F6 in `05_OPEN_QUESTIONS.md`.

**Alternatives considered:**
- **Keep v2 "adjacent but independent" framing.** Rejected because the same 5–9 weeks of work can produce a preprint *plus* four concrete metricHEALTH artefacts at minimal extra cost. Leaving the integration on the table was more conservative than defensible.
- **Fold the side project entirely into the metricHEALTH thesis proposal (no preprint).** Rejected because the paired-data methodology is strong enough to stand alone, early preprint publication establishes a track record independent of the thesis outcome, and arXiv publication can precede and support the thesis rather than compete with it.
- **Full-production FastAPI packaging for System C (F3(c)).** Rejected per F3 recommendation: prototype depth (F3(b)) is the sweet spot — enough scaffolding that Phase 4 does not start from scratch, not so much that we duplicate work Phase 4 will redo for hardening.
- **Extended feature-extraction arm with cross-tier generalisation (F2(c)).** Rejected per F2 recommendation: does not fit Week 3; saved as follow-up work. Minimum scope (F2(a)) suffices for the preprint's O6 objective.

**Rationale:** The six modifications turn a ~$0 side project into (a) a preprint with a stronger claim (QA + feature-extraction), (b) a partial Phase 1 completion (R4B validator stress-tested), (c) a Phase 4 prototype (case-manager Q&A FastAPI endpoint), (d) a Phase 3 design justification (representation choice for ML features), and (e) a Phase 5 regression harness. Scope increase ~10–15%; risk managed by R17 drop order.

**Supersedes:** Does not supersede v2 technical decisions (A–E remain active). Refines B2 (scope of metricHEALTH framing) and D2 (question families). Adds G1–G6 as new decision rows.

**Pending user confirmation:**
- F1: R4B validator availability at Week 1 start (drives standalone-copy vs. import path)
- F6: Revised employer clearance request scope (for mh_integration handoff)

---

## (Future entries append below this line)
