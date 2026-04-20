# Literature Review Queries

A structured plan for the lit review. The goal is a related-work section that is *defensive* against reviewer critique ("someone already did this") while staying compact. ~45–65 papers total is enough for a preprint; no need to chase exhaustiveness.

**v3 update:** Block 6 reframed and expanded to PSP adherence indicators; Block 11 added for feature-engineering prior art on adherence ML; Block 10 retained but scoped tighter.

Each block gives the motivation, 3–6 search queries, and what we're trying to prove or find.

## How to use this document

- Feed queries to the `researcher` subagent (see `01_CLAUDE_CODE_AGENT_PLAN.md`)
- Record findings in `docs/literature/<topic>.md`
- Target: **maximum 8 papers per topic block**; one paragraph summary each
- Sources in priority order: **arXiv → ACL Anthology / PubMed / PMC → venue proceedings → blog posts (rare, only for industry signals)**
- Date filter: **2019–present** for most topics; **2022–present** for RAG-specific work; no filter for foundational citations (Fellegi-Sunter, PDC/MPR origin papers, etc.)

---

## Block 1 — RAG for clinical / medical question answering

**Motivation:** Establish that clinical RAG is an active area and position our paper within it. Find the closest methodological predecessors.

**Queries:**
- `clinical question answering retrieval augmented generation`
- `medical RAG benchmark MedRAG MIRAGE`
- `retrieval augmented generation EHR question answering`
- `RAG clinical decision support LLM`
- `medical knowledge retrieval large language model evaluation`

**What we want to find:**
- Prior clinical RAG benchmarks (MedRAG, MIRAGE, EmrQA, MedQA-style)
- Methods that use BM25 vs dense retrieval over clinical text
- Any work comparing structured KG retrieval vs text retrieval in medicine (closest prior art)

**What we want to *not* find (but need to verify):**
- A paper that already does paired-data structured-vs-narrative RAG on EHR

---

## Block 2 — Structured vs. unstructured EHR for NLP and QA

**Motivation:** The heart of our contribution. We need to characterise the existing literature's claims and confounds.

**Queries:**
- `structured vs unstructured EHR natural language processing`
- `MIMIC structured data clinical note comparison`
- `EHR tabular text representation machine learning`
- `clinical note structured data information extraction comparison`
- `knowledge graph versus text electronic health record question answering`

**What we want to find:**
- Papers that claim structure helps, to cite
- Papers that claim unstructured is competitive (for the honest review side)
- The confound we call out: prior work doesn't hold information content constant

**Key prior-art target:** any paper with "paired" or "same patient" framing across representations — the more we find, the more we sharpen the novelty claim.

---

## Block 3 — FHIR + machine learning / LLM

**Motivation:** Our FHIR-native retrieval angle needs grounding. The lit review from the metricHEALTH proposal already has some of this — we can reuse entries.

**Queries:**
- `FHIR machine learning clinical prediction`
- `FHIR large language model clinical`
- `SQL on FHIR analytics`
- `FHIR-Former FHIR transformer`
- `FHIR R4B clinical natural language processing`
- `KETOS FHIR FHIRCat analytics platform`

**What we want to find:**
- FHIR-Former (cite — LLM training on FHIR)
- KETOS (cite — FHIR + ML platform)
- SQL on FHIR (cite — enabling tech)
- Any recent (2024–2026) FHIR + LLM papers
- Any work specifically on FHIR retrieval or FHIR-as-context for LLMs

---

## Block 4 — Clinical temporal reasoning in LLMs

**Motivation:** Our core finding is about temporal/adherence-indicator questions. We need to ground the claim that temporal reasoning is hard for LLMs over narrative clinical text.

**Queries:**
- `temporal reasoning clinical text LLM`
- `clinical event temporal extraction large language model`
- `medication timeline extraction natural language processing`
- `temporal question answering medical narrative`
- `longitudinal EHR reasoning benchmark`

**What we want to find:**
- Benchmarks on clinical temporal reasoning (i2b2 Temporal Relations etc.)
- Recent (2023+) LLM evaluations on clinical time
- Error patterns: what kinds of temporal questions do LLMs fail on?

---

## Block 5 — Synthetic EHR / Synthea and its limitations

**Motivation:** We use Synthea; we need to be honest about what it does and doesn't cover, and cite the generator.

**Queries:**
- `Synthea synthetic patient generator`
- `synthetic electronic health record machine learning`
- `synthetic EHR specialty medication limitations`
- `benchmark dataset synthetic clinical data evaluation`

**What we want to find:**
- The Synthea paper (Walonoski et al.) — standard citation
- Critiques of Synthea's medication module (supports our overlay decision)
- Other synthetic EHR generators we should mention (e.g. MIMIC-IV derivatives with synthesis)

---

## Block 6 — PSP adherence indicators (PDC, MPR, persistence) **[v3 expanded]**

**Motivation:** The preprint's questions are now explicitly grounded in the five adherence indicator families a Canadian PSP case manager uses in practice. We need to cite the canonical definitions of PDC (proportion-of-days-covered), MPR (medication-possession-ratio), and persistence/discontinuation, and to establish why these matter clinically for specialty regimens.

**Queries:**
- `proportion of days covered PDC medication adherence definition`
- `medication possession ratio MPR calculation methodology`
- `medication persistence discontinuation specialty pharmacy`
- `adherence metrics pharmacy claims administrative data`
- `ISPOR medication compliance persistence consensus`
- `specialty medication adherence long-acting injectable biologics`

**What we want to find:**
- Karve et al. (2009) and Hess et al. (2006) type papers on PDC/MPR equivalence and thresholds
- ISPOR Medication Compliance and Persistence Special Interest Group consensus papers
- Evidence that 80% PDC is the canonical adherence threshold
- Specialty-specific adherence studies (biologics, long-acting injectables)
- Anything specific to Canadian PSP data feeds (rare but valuable if found)

**What we want to cite (minimum):**
- One PDC definition paper
- One MPR definition paper
- One persistence-vs-adherence distinction paper
- One specialty-pharmacy-specific adherence paper

---

## Block 7 — LLM-generated clinical documentation

**Motivation:** Our narrative baseline is LLM-generated. As LLMs increasingly write clinical docs, the structured-vs-LLM-narrative comparison becomes practically urgent.

**Queries:**
- `LLM generated clinical note quality evaluation`
- `ambient AI scribe clinical documentation`
- `GPT clinical note accuracy hallucination`
- `large language model medical documentation fidelity`
- `automated clinical note generation evaluation`

**What we want to find:**
- Evidence that LLM clinical documentation is being deployed
- Evidence of fidelity / hallucination problems in LLM notes
- Methodology for fidelity evaluation (to strengthen our fidelity audit design)

---

## Block 8 — Retrieval strategies: typed / graph / hybrid

**Motivation:** Our resource-aware retriever does typed filtering + reference traversal + temporal pre-filter. We should cite the retrieval lineage.

**Queries:**
- `hybrid retrieval dense sparse clinical`
- `knowledge graph retrieval augmented generation`
- `structured retrieval query rewriting LLM`
- `typed retrieval schema aware RAG`
- `metadata filtering vector search retrieval`

**What we want to find:**
- Hybrid retrieval papers (BM25 + dense)
- KG-RAG / graph-RAG work (Microsoft's GraphRAG is an obvious citation)
- Schema-aware retrieval or "retrieval with metadata filtering" prior art
- Anything that specifically does reference-traversal retrieval over FHIR / structured clinical data

---

## Block 9 — Evaluation methodology for RAG

**Motivation:** Our programmatic ground truth is a design choice against a landscape where LLM-as-judge is common. We should cite this debate.

**Queries:**
- `LLM as judge evaluation reliability`
- `RAG evaluation benchmark methodology`
- `retrieval recall answer accuracy decomposition`
- `programmatic evaluation question answering`
- `faithfulness evaluation RAG hallucination`

**What we want to find:**
- Citations for why LLM-as-judge is problematic in sensitive domains
- Alternative evaluation methodologies (reference-based, programmatic)
- RAGAS, TruLens, other standard RAG eval frameworks — cite even if we don't use them

---

## Block 10 — Canadian PSP context **[v3 scoped tighter]**

**Motivation:** Reframed under v3 dual-purpose — PSP framing is now the *question grounding* of the paper (Block 6 covers the metrics; this block covers the institutional context). Still light — one or two citations; the preprint is not a health-services paper.

**Queries:** (reuse from the existing metricHEALTH literature review doc)
- `Canadian patient support program specialty medication`
- `PSP adherence Canada outcome`
- `pharmaceutical patient support program digital health`

**What we want to find:** One or two citations for "specialty pharmacy and PSPs are important in Canada," nothing more. The heavier PSP context lives in the thesis chapter, not the arXiv preprint.

---

## Block 11 — Feature engineering for adherence ML **[v3 new]**

**Motivation:** The feature-extraction arm (O6) compares structured-FHIR-derived features, narrative-derived features, and resource-aware-retrieved features as inputs to an adherence classifier. We need prior art on what features have historically worked for adherence ML, both to position the extraction design and to cite standard baselines.

**Queries:**
- `medication adherence prediction machine learning features`
- `XGBoost LightGBM adherence prediction pharmacy`
- `EHR feature engineering adherence prediction`
- `LLM feature extraction clinical tabular prediction`
- `adherence prediction deep learning claims data`

**What we want to find:**
- Steiner et al. (2020) type adherence-prediction AUC benchmarks (already cited in metricHEALTH proposal — reuse)
- Choi et al. (2016) type temporal-pattern ML on EHR (already cited — reuse)
- Recent (2023+) work using LLMs as feature extractors for tabular clinical prediction
- Standard feature sets for adherence prediction (PDC-style temporal aggregates, gap statistics, demographic covariates)

**What we want to cite (minimum):**
- One reference-AUC adherence-prediction paper
- One paper using LLMs as tabular-feature extractors
- One paper on temporal-feature engineering for adherence

---

## Prioritisation

If time is tight and only some blocks can be done:
- **Must-do (Week 1):** Blocks 1, 2, 3, 4, 6 (adherence metrics definitions are load-bearing for the question bank)
- **Should-do (Week 4):** Blocks 5, 7, 8, 9, 11
- **Nice-to-have:** Block 10

---

## Expected output structure

At the end of the lit review, `docs/literature/` contains:
```
docs/literature/
├── clinical_rag.md
├── structured_vs_unstructured.md
├── fhir_ml.md
├── clinical_temporal.md
├── synthea.md
├── psp_adherence_indicators.md        # Block 6 (renamed)
├── llm_clinical_documentation.md
├── retrieval_strategies.md
├── rag_evaluation.md
├── canadian_psp.md                    # Block 10 (light)
└── adherence_ml_features.md           # Block 11 (new for v3)
```

Plus `docs/literature/bibliography.bib` — BibTeX entries for everything cited, built incrementally as papers are read.

---

## Anti-patterns for the researcher agent

1. **Do not cite abstracts alone.** If the paper isn't open-access, say so and either fetch the preprint or drop the citation.
2. **Do not trust Google Scholar snippets.** Fetch the PDF / abstract directly.
3. **Do not overclaim novelty.** The lit review should be written defensively: "no prior work has done X in Y context" — where both X and Y are narrow enough to be true.
4. **Do not cite a survey when the underlying paper exists.** Go to the source.
5. **Do not conflate PDC and MPR.** These are distinct metrics with distinct definitions — Block 6 papers will make this clear; the writer agent must preserve the distinction.
