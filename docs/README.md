# FHIR-RAG Preprint — Planning Pack

This folder contains the full planning pack for the paired-data comparison of structured-FHIR RAG versus LLM-narrative RAG on PSP adherence-indicator question answering for long-acting specialty medications.

**Status:** v3 dual-purpose — standalone arXiv preprint **and** Phase 0 of the metricHEALTH research proposal. Technical stack unchanged from v2 (free-tier / $0 budget); see `07_DECISIONS_v2_FREE_STACK.md` for the active configuration including the v3 addendum.

## Reading order

Read in this order — each document builds on the previous one.

| # | File | Purpose | Read when |
|---|---|---|---|
| 0 | `00_PROJECT_PLAN.md` | Comprehensive 5-week project plan with WBS, risks, budget, governance, metricHEALTH integration map (§13) | First — the source of truth |
| 2 | `02_LITERATURE_REVIEW_QUERIES.md` | 11 topic blocks × 3–6 queries each, prioritised, with anti-patterns for the lit review | Week 1 (mandatory blocks) + Week 4 |
| 3 | `03_PAPER_DRAFT_STRUCTURE.md` | Section-by-section paper outline, figure plan, writing principles, review checklist (preprint + thesis-chapter framings) | Week 4–5 |
| 4 | `04_REPO_LAYOUT.md` | Target directory structure and invariants (freeze points, branching), includes `mh_integration/`, `features/`, `thesis_chapter/` | Day 1 of Week 1 |
| 5 | `05_OPEN_QUESTIONS.md` | Questions that block or shape the plan — A–E resolved in v2, Block F is new for v3 dual-purpose pivot | F block: **this week** |
| 6 | `06_DECISIONS_ANSWERED.md` | v1 paid-stack decisions — **SUPERSEDED**, audit trail only | Reference only |
| 7 | `07_DECISIONS_v2_FREE_STACK.md` | v2 free-stack decisions + **v3 dual-purpose addendum** — the active configuration | Active — read first for execution |
| — | `decisions.md` | Append-only decision log with v2 entry + v3 pivot entry | Updated throughout project |

## Immediate next steps

1. Read `07_DECISIONS_v2_FREE_STACK.md` (v3 addendum) for the active configuration
2. Read `05_OPEN_QUESTIONS.md` Block F — resolve F1, F5, F6 this week
3. Set up the repo structure from `04_REPO_LAYOUT.md` (includes new `mh_integration/`, `features/`, `thesis_chapter/` directories)
4. Create Groq account (free, Google sign-in, no credit card)
5. Send the revised employer clearance request (F6 / E2) — scope extended to cover `mh_integration/` handoff
6. Kick off Week 1

## One-sentence summary

Over 5 weeks (+ 4 buffer), produce a preprint and a public dataset that show structured-FHIR RAG beats LLM-narrative RAG on PSP adherence-indicator questions (PDC, MPR, persistence, missed-dose detection, next-dose lookup) about long-acting specialty medications — with the gap widening as regimen complexity increases, extended to a feature-extraction comparison on a synthetic adherence classification task — using a paired-data methodology that holds information content constant, while simultaneously producing four reusable artefacts for the metricHEALTH research proposal (R4B validator stress-test, case-manager Q&A FastAPI prototype, feature-engineering design justification, reusable pytest-style evaluation harness).

## Relationship to metricHEALTH

This project is **Phase 0 of** the metricHEALTH FHIR R4B Interoperability + ML Adherence research proposal — a foundation study that benchmarks representation choices before committing to the ML engine design. It is published as a standalone arXiv preprint *and* produces four concrete artefacts that feed metricHEALTH phases:

| Side-project artefact | metricHEALTH phase | Use |
|---|---|---|
| 200 validated FHIR bundles × 3 complexity tiers | Phase 1 (R4B validator) | Stress-test the pre-write validation layer; conformance rates as Milestone 1 evidence |
| `mh_integration/case_manager_qa.py` (System C FastAPI wrapper) | Phase 4 (Dashboard) | Case-manager Q&A prototype; mounts into metricCONNECT |
| Structured-vs-narrative feature-extraction finding (O6) | Phase 3 (Feature engineering) | Empirical justification for ML engine feature-representation choice |
| `questions/pytest_harness/` + adherence metric modules | Phase 5 (Evaluation) | Reusable regression harness |

**Framing separation (R16 mitigation):** The arXiv preprint itself does not reference metricHEALTH beyond the affiliation line — it stands alone on the paired-data methodology. The Phase 0 framing lives in the parallel thesis-chapter scaffold (`thesis_chapter/phase_0.md`), produced in Week 5 but not externally published. This protects the preprint from reviewer confusion about scope while preserving the integration case for the eventual metricHEALTH thesis.

**Drop order under schedule pressure (R17):** If the timeline tightens, drop in this order: (1) feature-extraction arm, (2) System C FastAPI packaging, (3) sensitivity sweep. The paper must stand alone on paired-data methodology regardless of what metricHEALTH value is preserved.
