# Open Questions

**Status (v3, 2026-04-19):** All A, B, C, D questions resolved in v2 decisions (see `07_DECISIONS_v2_FREE_STACK.md`). E items in progress. **Block F is new for the v3 dual-purpose pivot** — these are the questions that the pivot itself surfaces and that shape the preprint + metricHEALTH integration.

This document is retained for historical reference and to track the remaining F-block questions. The resolved A–E questions are kept below for audit trail; scan them only if you want the reasoning context.

---

## F. Dual-purpose pivot — new and active **[v3]**

### F1. metricHEALTH R4B validator availability at Week 1 start

**Question:** Is the Phase 1 R4B conformance validator already implemented in the metricHEALTH codebase and accessible to this project at the start of Week 1, or does the side project need a standalone copy?

**Impact:** Risk R14. Drives T1.3 scope in the revised week-1 WBS.

**Resolution path:**
- If mH Phase 1 has started: import the validator from the mH repo into `mh_integration/r4b_validator.py` as a thin wrapper.
- If mH Phase 1 has not started: build a standalone R4B validator in `mh_integration/` using `fhir.resources` R4B pydantic models directly. The mH team reconverges later.

**Decision needed by:** start of Week 1 (Apr 27, 2026).

---

### F2. Feature-extraction arm scope

**Question:** How far does the feature-extraction arm (O6) go in Week 3?

- (a) Minimal: three feature sets × two classifiers × AUC only → 3 days
- (b) Extended: add feature ablations (what happens if we drop PDC? drop temporal features?) → 5 days
- (c) Full: add cross-tier generalisation (train on tier-1, test on tier-3) → 7+ days (does not fit week 3)

**Impact:** O6 is the third-priority objective per the publishable-outcome matrix. Per R17 drop order, this arm is dropped first if the timeline tightens.

**Recommendation:** (a). If there is time at end of week 3, extend to (b). (c) is follow-up work.

**Decision needed by:** end of Week 2 (when evaluator scopes the week 3 runs).

---

### F3. System C FastAPI packaging depth

**Question:** How production-ready should `mh_integration/case_manager_qa.py` be?

- (a) Demo-only: a minimal FastAPI endpoint that runs System C, no auth, no rate limiting, no error handling beyond basic try/except
- (b) Prototype: demo + a proper request/response schema, input validation, structured logging
- (c) Near-production: prototype + auth hooks, rate limiting, async, observability

**Impact:** Per R17 drop order, this is the second thing dropped under timeline pressure. (a) satisfies the preprint's "it runs" claim and gives metricHEALTH Phase 4 a starting point; (c) does work Phase 4 will redo anyway.

**Recommendation:** (b). This is the sweet spot — enough scaffolding that the Phase 4 team doesn't start from scratch, not so much that we're duplicating work they'll redo for hardening.

**Decision needed by:** start of Week 2.

---

### F4. Thesis-chapter scaffold depth

**Question:** In Week 5, how developed should the thesis-chapter scaffold be?

- (a) Outline: headings and one-paragraph sketches, a pointer to the preprint for the rest
- (b) Draft: full prose draft with Phase 0 framing applied, referencing preprint numbers
- (c) Polished: ready for insertion into the main metricHEALTH thesis

**Impact:** The preprint is the primary week-5 deliverable. The thesis-chapter scaffold is insurance — it captures the framing decisions while the project is fresh so the future thesis writeup is easier. Deep polish would trade off preprint time.

**Recommendation:** (a), expanded to (b) only if Week 5 has slack.

**Decision needed by:** Week 5 Day 1.

---

### F5. Synthetic adherence outcome label design

**Question:** For the feature-extraction arm (§4.5 of project plan), what is the exact rule for the synthetic discontinuation-risk label?

Options:
- (a) Hard rule: "≥2 consecutive missed doses in final 60 days" → binary
- (b) Gap-based: "median dose gap in final 90 days > 1.5× prescribed interval" → binary
- (c) Composite: (a) OR (b) → binary
- (d) Continuous: gap-ratio in final 90 days → regression (changes the metric from AUC to MAE)

**Impact:** The label shape affects interpretability of the feature-extraction arm. A binary label with a simple, published-concordant definition is the easiest to defend.

**Recommendation:** (c). Documented as "synthetic discontinuation-risk label" in the paper's methods, with explicit caveat that this is a methodological proxy, not a validated clinical outcome.

**Decision needed by:** Week 1 (ground-truth generator and feature extractors both depend on it).

---

### F6. Employer clearance scope for the dual-purpose framing

**Question:** The v2 decision B4 assumed light metricHEALTH affiliation only. v3 increases the metricHEALTH integration surface (validator code reuse, case-manager QA prototype, feature-extraction justification, reusable harness). Does this increase require a revised employer clearance request?

**Impact:** E2 action item. Originally scoped for "preprint publication with methodology from this paper." Under v3, the employer may need to explicitly clear the handoff of `mh_integration/` artefacts back into the metricHEALTH codebase post-preprint, or at minimum confirm that this handoff is considered internal work.

**Recommendation:** Revise the clearance request draft (E2) to list:
- Preprint publication (as before, per v2)
- Release of code under Apache-2.0 (as before)
- Release of synthetic dataset under CC-BY-4.0 (as before)
- **Internal handoff of `mh_integration/` artefacts from preprint repo to metricHEALTH codebase** (new for v3 — should be trivial internal approval)
- **Explicit confirmation that the preprint does not disclose metricHEALTH proprietary infrastructure** (as before, but re-emphasise under v3 because the integration surface is larger)

**Decision needed by:** This week, in parallel with v2's E2 action.

---

## Resolution workflow for F block

1. **This week (pre-Week 1):** Resolve F1, F5, F6.
2. **End of Week 1:** Resolve F3.
3. **End of Week 2:** Resolve F2.
4. **Start of Week 5:** Resolve F4.

---

## A–E (historical — resolved in v2)

All A–D blocks resolved in `06_DECISIONS_ANSWERED.md` (v1 paid stack, now audit-trail only) and re-resolved in `07_DECISIONS_v2_FREE_STACK.md` (v2 free stack, currently active). E block partly resolved, in-progress items flagged below.

### A. Blocking — resolved
All five blockers (A1–A5) resolved in v2: Groq free tier for LLMs (Llama 3.3 70B narrative, Qwen 3 32B answer), BGE-large-v1.5 local embeddings, $0 CAD budget, start date Monday 27 April 2026.

### B. Strongly recommended — resolved
- B1: Sole-authored TJ; Ruwindhu Aidi in acknowledgements.
- B2: Light affiliation in the preprint; v3 extends this into a parallel thesis-chapter framing without changing the preprint's affiliation-only treatment.
- B3: arXiv → ML4H 2026 → JAMIA extended.
- B4: Apache-2.0 (code) + CC-BY-4.0 (dataset), pending employer clearance (see F6).
- B5: Plausible class-level descriptors.

### C. Week-1 clarifications — resolved
- C1: Single run, temperature 0.
- C2: k=5, chunk=500 tokens; sweep in appendix.
- C3: TJ single-rater with second-LLM triangulation.
- C4: Groq free tier (synthetic data; privacy terms verified).
- C5: Dockerfile + `make reproduce`.

### D. Structural — resolved
- D1: 90% fidelity gate; drop to 85% only after 3 iterations cluster at 87–89%.
- D2: Same 120 questions for all patients; N/A is a valid answer. **v3 note:** the five question families are now PSP adherence indicators, not the original generic categories.
- D3: Reference date varied per patient.

### E. Ethical / compliance — in progress
- E1: REB determination letter — submit in Week 1 parallel track (original action still live).
- E2: Employer IP clearance — **must be revised under v3** (see F6).

---

## One-line v3 summary

> *"v2 free stack still holds. v3 adds the six-modification dual-purpose pivot: PSP adherence-indicator question framing, R4B validator hookup, System C FastAPI packaging for metricCONNECT, feature-extraction arm for the ML engine, reusable pytest harness, and parallel thesis-chapter scaffold. New questions are in Block F; A–E are either resolved (v2) or in progress (E)."*
