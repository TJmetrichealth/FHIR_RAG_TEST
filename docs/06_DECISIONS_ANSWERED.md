# Finalized Decisions — Open Questions Resolved (v1, PAID STACK)

> **⚠️ SUPERSEDED:** This v1 decisions file assumes the paid-stack (Azure OpenAI + Anthropic API + Azure embeddings, CAD $1,000 budget). It was replaced on 2026-04-19 by `07_DECISIONS_v2_FREE_STACK.md` ($0 budget, Groq free tier, local BGE embeddings). That v2 file itself carries a **v3 addendum** reflecting the dual-purpose pivot (preprint + metricHEALTH Phase 0 integration).
>
> **Active configuration:** v2 free stack + v3 dual-purpose addendum (see `07_DECISIONS_v2_FREE_STACK.md`).
>
> **This file is retained only as an audit trail of the original paid-stack reasoning.** Do not execute against it.

---

**Status:** All blockers (A) resolved. Strongly-recommended questions (B) resolved with one item flagged for user confirmation. Week-1 clarifications (C) and structural (D) resolved. Ethical/compliance (E) flagged for parallel action.

**Date of decisions:** 19 April 2026
**Revises:** `05_OPEN_QUESTIONS.md`
**Superseded by:** `07_DECISIONS_v2_FREE_STACK.md` (v2 free stack, currently active; v3 addendum inside)

---

## Summary Decision Table (v1 — historical)

| # | Question | Decision | Confidence |
|---|---|---|---|
| **A1** | Narrative-generation LLM | **GPT-4 via Azure OpenAI (Canadian region) as primary**; Llama 3.1 70B Instruct as secondary robustness check in appendix | High |
| **A2** | Answer-generation LLM | **Claude Sonnet 4.6** (different vendor → breaks self-consistency) | High |
| **A3** | Embedding model | **`text-embedding-3-large` via Azure OpenAI** as primary; **MedCPT** as robustness appendix | High |
| **A4** | Budget ceiling | **CAD $1,000** | High |
| **A5** | Start date | **Monday 27 April 2026** | Confirm with user |
| **B1** | Authorship | **First-author: TJ. Advising co-author: Dr. Ed Sykes (pending his agreement). Acknowledgements: Ruwindhu Aidi** | Confirm with collaborators |
| **B2** | metricHEALTH relationship | **(b) Light — affiliation only** | High |
| **B3** | Target venue | **arXiv first → ML4H 2026 workshop at NeurIPS → JAMIA extended version** | High |
| **B4** | Licensing | **Code: Apache-2.0. Dataset: CC-BY-4.0** | Subject to employer IP clearance |
| **B5** | Domain realism | **(b) Plausible class-level descriptors** | High |
| **C1** | Runs per question | **Single run, temperature 0** | High |
| **C2** | Top-k / chunk size | **k=5, chunk=500 tokens fixed; sensitivity sweep in appendix** | High |
| **C3** | Inter-rater check | **Manual taxonomy on 50-case sample, single rater (TJ); cross-check against second-LLM classification as triangulation only** | Medium |
| **C4** | API constraints | **Azure OpenAI Canadian region for narrative-gen; Anthropic API direct for answer-gen** | Verify employer policy |
| **C5** | Reproducibility | **(b) Dockerfile + `make reproduce`** | High |
| **D1** | Fidelity threshold | **90% initial gate; drop to 85% only after 3 prompt iterations cluster at 87–89%** | High |
| **D2** | Question balance | **Same 120 questions for all patients; "N/A" is a valid answer and scored as its own absence-detection signal** | High |
| **D3** | Reference date | **Vary per patient** — sampled uniformly from 30 days before to 90 days after regimen start | High |
| **E1** | REB determination | **Submit REB-exemption request in Week 1 parallel track** | Action required |
| **E2** | Employer IP clearance | **Request written clearance from metricHEALTH leadership this week** | Action required |

---

## Summary of what changed in v2, and then v3

**v2 (2026-04-19, free stack):** All A-row API decisions flipped to free-tier open-weights alternatives. Budget went from CAD $1,000 to $0. Authorship narrowed to sole-author TJ (Dr. Sykes removed as co-author). Everything else in the table above carried forward unchanged.

**v3 (2026-04-19, dual-purpose addendum):** Six new decisions layered on top of v2, none of which change v2's technical stack:
1. Question families reframed as PSP adherence indicators (PDC, MPR, persistence, missed-dose detection, next-dose lookup) — affects D2 interpretation only, not the number of questions.
2. Every bundle validated via a `mh_integration/r4b_validator.py` that is reused (or prototypes) the metricHEALTH Phase 1 R4B validator.
3. System C packaged as a FastAPI endpoint at `mh_integration/case_manager_qa.py` — seeds metricHEALTH Phase 4.
4. Feature-extraction arm added as O6 — compares FS-Structured / FS-Narrative / FS-Aware on a synthetic adherence-classification task.
5. Question bank structured as a pytest-style harness reusable as metricHEALTH Phase 5 regression suite.
6. Parallel thesis-chapter scaffold in `thesis_chapter/phase_0.md` framing the work as Phase 0 of the metricHEALTH research proposal.

v3 is documented inside `07_DECISIONS_v2_FREE_STACK.md`.

---

## A. Blockers — detailed rationale (v1 paid stack, historical)

### A1 — Narrative-generation LLM

**Decision:** GPT-4 via **Azure OpenAI, Canadian region** as primary narrative generator. Model snapshot `gpt-4-0613` or `gpt-4-turbo-2024-04-09` (whichever is still fixed and available in your Azure tenant). Add **Llama 3.1 70B Instruct** (open-weights, via Together AI or Azure AI Foundry) as a secondary narrative-gen model, used only in an appendix robustness check.

**Why:**
- GPT-4 on Azure gives you a pinned snapshot and Canadian data residency in one package — the natural choice for a Canadian healthcare-adjacent researcher.
- Adding *one* open-weights model as an appendix strengthens the paper's robustness claim ("structure beats narrative across narrative-gen model families") without doubling the main experimental matrix.
- If Week 1 slips, the open-weights appendix moves to the 4-week buffer. The primary claim is never held hostage to it.

**Superseded by v2:** Groq free tier Llama 3.3 70B.

---

### A2 — Answer-generation LLM

**Decision:** **Claude Sonnet 4.6** (exact model string `claude-sonnet-4-6`) as the sole answer LLM across all three retrieval systems (A, B, C) and the templated-narrative ablation.

**Why:**
- Using a *different vendor* than the narrative generator kills the self-consistency confound — GPT-4 recognising its own narrative is a real threat to the main claim, and this eliminates it cleanly.
- Sonnet 4.6 is materially cheaper than GPT-4-class models while being strong at structured extraction and temporal reasoning — both central to the evaluation.
- Single-vendor answer LLM simplifies the reproducibility story and keeps the paper's experimental variable count minimal.

**Superseded by v2:** Groq free tier Qwen 3 32B (different training lineage than Llama → vendor separation preserved for free).

---

### A3 — Embedding model

**Decision:**
- **Primary:** `text-embedding-3-large` via Azure OpenAI (Canadian region), 3072 dimensions.
- **Appendix robustness:** **MedCPT** (PubMed-trained dual-encoder) *or* domain-tuned BGE-Medical. Used only in a sensitivity analysis.

**Superseded by v2:** `BAAI/bge-large-en-v1.5` local via sentence-transformers; MedCPT locally for robustness.

---

### A4 — Budget ceiling

**Decision:** **CAD $1,000** comfortable ceiling for the project.

**Superseded by v2:** $0 CAD.

---

### A5 — Start date

**Decision:** **Monday 27 April 2026** (one week from today).

**Unchanged in v2 and v3.**

---

### B1 — Authorship

**Decision (v1):** First-author: TJ. Advising co-author: Dr. Ed Sykes (pending his agreement). Acknowledgements: Ruwindhu Aidi.

**Superseded by v2:** Sole-authored TJ. Ruwindhu Aidi in acknowledgements only.

---

### B2 — metricHEALTH relationship

**Decision (v1 and v2):** Light — affiliation only.

**v3 refinement:** Preprint abstract remains metricHEALTH-free; light affiliation only. A parallel thesis-chapter scaffold extends the framing to "Phase 0 of the metricHEALTH research proposal" — but that scaffold is not published externally. The preprint stands alone on the paired-data methodology. This carries R16 as an explicit risk to manage in Week 5 writing.

---

### B3 — Target venue

**Decision:** arXiv → ML4H 2026 → JAMIA extended. **Unchanged in v2 and v3.**

---

### B4 — Licensing

**Decision:** Apache-2.0 (code), CC-BY-4.0 (dataset). **Unchanged in v2 and v3**, pending employer clearance (which v3 extends — see F6 in `05_OPEN_QUESTIONS.md`).

---

### B5 — Domain realism

**Decision:** Plausible class-level descriptors. **Unchanged in v2 and v3.**

---

## C. Week-1 clarifications — detailed (v1, carried forward unchanged through v3)

### C1 — Runs per question
**Single run at temperature 0** across all systems. Defensible for a preprint; 3× cheaper than self-consistency voting.

### C2 — Top-k / chunk size
**Fixed: k=5, chunk=500 tokens.** Sensitivity sweep in appendix: k ∈ {3, 5, 10}, chunk ∈ {300, 500, 800}.

### C3 — Inter-rater check on error taxonomy
**Primary approach:** TJ manually categorises 50 failure cases per system into 3–4 categories. Single-rater, no inter-rater coefficient.
**Triangulation:** Run a different LLM with a constrained structured-output prompt on the same 50 cases, compare categorisations.

### C4 — API / institutional constraints
**v1:** Azure OpenAI (Canadian region) + Anthropic API direct.
**Superseded by v2:** Groq free tier.

### C5 — Reproducibility
**Option (b) — Dockerfile + `make reproduce`.** Unchanged in v2 and v3.

---

## D. Structural — confirmed recommendations (v1, carried forward unchanged through v3)

### D1 — Fidelity threshold
**90% initial gate**, drop to 85% if three iterations cluster at 87–89%.

### D2 — Question balance
**Same 120 questions for all patients.** "N/A" is valid.

**v3 note:** The five question families are now PSP adherence indicators — Next-dose lookup, Dose-history aggregation, Coverage-window reasoning, Missed-dose detection, Persistence. Same count, same balance; renamed and clinically grounded.

### D3 — Reference date
**Varied per patient**, sampled uniformly from `[regimen_start − 30d, regimen_start + 90d]`.

---

## E. Ethical / compliance — actions initiated (v1, updated in v3)

### E1 — REB determination
**Action (this week):** Submit REB-exemption request. **Unchanged in v2 and v3.**

### E2 — Employer IP clearance
**v1 and v2 scope:** Preprint publication, Apache-2.0 code, CC-BY-4.0 dataset, affiliation line, non-disclosure of mH proprietary infrastructure.

**v3 scope addition:** Internal handoff of `mh_integration/` artefacts from preprint repo back to metricHEALTH codebase. See F6 in `05_OPEN_QUESTIONS.md`.

---

## Items still requiring user confirmation (v1, carried through)

| Item | Why it still needs you |
|---|---|
| **A5 start date** | Proposed Monday 27 April 2026 — confirm or shift |
| **B4 licence** | Contingent on E2 employer clearance (v3-expanded scope) |

Everything else above is a committed decision.

---

## One-line summary (v1, historical)

> *"Main narrative LLM: GPT-4 on Azure. Main answer LLM: Claude Sonnet 4.6. Embedding: text-embedding-3-large. Budget: CAD $1,000. Start date: Monday 27 April 2026. arXiv target: 31 May 2026. Paper framed as independent research with light metricHEALTH affiliation."*

**See v2 in `07_DECISIONS_v2_FREE_STACK.md` for the active configuration.**
