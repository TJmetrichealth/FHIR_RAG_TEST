# Block 3 — FHIR + ML / LLM literature review

**File:** `docs/literature/fhir_ml.md`
**Compiled:** April 20, 2026
**Scope:** Prior art grounding the FHIR-native retrieval angle of Project #2 (structured FHIR RAG vs. LLM-generated narrative RAG).

---

## Executive summary

As of April 2026, the FHIR + ML/LLM literature has crystallized into four clusters: (1) **FHIR-native analytics platforms** (KETOS, Pathling, SQL-on-FHIR) that normalize FHIR for batch ML; (2) **LLM-on-FHIR deployment work** (LLM on FHIR, FHIR-Former) that feeds filtered FHIR slices into generative models; (3) **text↔FHIR transformation** (FHIR-GPT, Infherno, FHIR Workbench) using LLMs to extract structured resources from notes; and (4) **FHIR-grounded QA benchmarks** (FHIR-AgentBench, Kothari & Gupta 2025, MedAgentBench) that evaluate LLM agents interacting with FHIR servers. **No paper was found that performs a paired head-to-head comparison of structured FHIR RAG vs. LLM-generated narrative RAG on the same patient cohort for temporally-grounded clinical QA.** The closest threats are Kothari & Gupta (2025), which splits FHIR QA into resource selection + answering on Synthea but lacks a narrative baseline, and FHIR-AgentBench (2025), which ablates FHIR retrieval strategies on MIMIC-IV-FHIR but keeps all arms FHIR-native. Project #2's novelty holds under a narrow, defensible framing.

---

## Per-paper entries (8 papers)

### 1. FHIR-Former — Engelke et al., 2025

**Citation:** Engelke M, Baldini G, Kleesiek J, Nensa F, Dada A. *FHIR-Former: enhancing clinical predictions through Fast Healthcare Interoperability Resources and large language models.* Journal of the American Medical Informatics Association 32(12):1793–1801, December 2025. DOI: 10.1093/jamia/ocaf165. PMCID: PMC12646377. Open Access.

**Summary:** Open-source framework from University Hospital Essen (IKIM) that dynamically processes structured FHIR resources (conditions, medications, labs) alongside unstructured clinical notes for prediction tasks. The pipeline eliminates most manual feature engineering and supports live inference directly against FHIR servers. Reported results span 30-day readmission (F1 70.7%), mortality (F1 51.8%, accuracy 88.1%), imaging study classification (macro-F1 61%), and ICD prediction (94% accuracy).

**Relevance to Project #2:** Most recent flagship JAMIA paper bridging FHIR and LLMs, but focused on prediction not retrieval/QA.

**Cite for:** The "FHIR + LLM for prediction" baseline and to motivate why the same integration question matters for retrieval.

**Concerns:** None — peer-reviewed, open access, code public (UMEssen/fhir-former).

---

### 2. SQL on FHIR v2 — Grimes et al., 2025

**Citation:** Grimes J, Brush R, Ryzhikov N, Szul P, Mandel J, Gottlieb D, Grieve G, Sadjad B, Sanyal A. *SQL on FHIR — Tabular views of FHIR data using FHIRPath.* npj Digital Medicine 8(1):342, 9 June 2025. DOI: 10.1038/s41746-025-01708-w. PMID: 40490535. Open Access.

**Summary:** Documents the 18-month international working group effort producing the HL7 SQL-on-FHIR v2 Implementation Guide. Defines the `ViewDefinition` logical model and a FHIRPath subset that lets a single portable specification execute across multiple ViewRunner implementations (Pathling, Medplum, HL7 IG Publisher, Helios, FlatQuack). Feasibility demonstrated by replicating an oxygen-administration racial-disparity study over MIMIC-IV-FHIR.

**Relevance to Project #2:** Represents the dominant community approach to making FHIR queryable — a foil to Project #2's retrieval-representation approach, which targets semantic retrieval rather than tabular projection.

**Cite for:** The "analytics/query over FHIR" school of thought, and to explain why tabular ViewDefinitions complement but do not replace semantic retrieval for free-form QA.

**Concerns:** One co-author has a disclosed commercial interest in Aidbox (Health Samurai).

---

### 3. Pathling — Grimes et al., 2022

**Citation:** Grimes J, Szul P, Metke-Jimenez A, Lawley M, Loi K. *Pathling: analytics on FHIR.* Journal of Biomedical Semantics 13(1):23, 8 September 2022. DOI: 10.1186/s13326-022-00277-1. PMID: 36076268. Open Access.

**Summary:** CSIRO-built FHIR server that layers analytics operations (aggregate, extract, search) on top of standard FHIR APIs, with FHIRPath expressions and an integrated Terminology Service for SNOMED CT–aware queries. Built on Apache Spark with roots in Cerner's Bunsen library; one of the canonical ViewRunner reference implementations for SQL-on-FHIR v2.

**Relevance to Project #2:** Defines the state of the art for programmatic FHIR analytics without LLMs; useful contrast against retrieval-oriented access.

**Cite for:** The "non-LLM programmatic access to FHIR" alternative that Project #2's retrieval pipelines sit alongside.

**Concerns:** None.

---

### 4. LLM on FHIR — Schmiedmayer et al., 2024

**Citation:** Schmiedmayer P, Rao A, Zagar P, Ravi V, Zahedivash A, Fereydooni A, Aalami O. *LLM on FHIR — Demystifying Health Records.* arXiv:2402.01711 [cs.CY], 25 January 2024. A peer-reviewed follow-on ("LLMonFHIR") is archived at PMC12144420.

**Summary:** Stanford Spezi-based iOS app that lets patients chat with their own FHIR records via GPT-4. The system filters FHIR resources (active/outpatient medications, most-recent labs/observations) to fit context windows, then uses OpenAI function calling to fetch specific resources as JSON on demand. Pilot evaluation on 6 SyntheticMass (Synthea) patients shows mostly 5/5 physician Likert ratings, weakest on lab retrieval.

**Relevance to Project #2:** Direct precursor — the same Synthea + FHIR + LLM stack, same patient-level scope, but delivered as function-calling retrieval rather than RAG and without a narrative comparator or benchmark QA set.

**Cite for:** Prior art on feeding FHIR JSON into LLM prompts for patient QA; motivates a principled retrieval-architecture comparison.

**Concerns:** arXiv version is a pilot with n=6 patients; the peer-reviewed PMC version is the stronger citation where accessible.

---

### 5. FHIR-AgentBench — Lee et al., 2025 ⚠️ closest comparator

**Citation:** Lee G, Bach E, Yang E, Pollard T, Johnson A, Choi E, Jia Y, Lee JH. *FHIR-AgentBench: Benchmarking LLM Agents for Realistic Interoperable EHR Question Answering.* arXiv:2509.19319 [cs.CL], 12 September 2025 (v2: 13 November 2025). Verily × KAIST × MIT.

**Summary:** 2,931 clinician-relevant QA pairs grounded in MIMIC-IV-on-FHIR with ground-truth FHIR resource mappings. Systematically ablates three axes of agent design: retrieval strategy (direct FHIR API vs. specialized tools), interaction pattern (single- vs. multi-turn), and reasoning strategy (NL vs. code generation). Multi-turn iterative search achieves ~71% retrieval recall, and retrieval quality is identified as the dominant bottleneck on answer correctness.

**Relevance to Project #2:** **Closest benchmark** on FHIR QA. All arms operate on FHIR — there is no narrative-note RAG comparator on paired data — so Project #2's structured-vs-narrative axis remains open. Project #2 must explicitly differentiate: FHIR-AgentBench varies agentic strategy within FHIR; Project #2 varies **retrieval representation** across FHIR and narrative.

**Cite for:** The strongest extant benchmark for FHIR QA with LLMs; establishes that FHIR retrieval is a known bottleneck and motivates evaluating retrieval representation.

**Concerns:** None — open arXiv, dataset/code pledged on GitHub, ML4H 2025 venue.

---

### 6. Patient-specific FHIR QA with private fine-tuning — Kothari & Gupta, 2025 ⚠️ second-closest

**Citation:** Kothari S, Gupta A. *Question Answering on Patient Medical Records with Private Fine-Tuned LLMs.* arXiv:2501.13687 [cs.CL], 23 January 2025 (Stanford / Genloop Labs).

**Summary:** Constructs a 5,000-question Synthea-based FHIR QA set and proposes a two-stage pipeline: Task 1 identifies relevant FHIR resources for a query; Task 2 answers from the selected subset. Fine-tunes small private LLMs (Llama-3-class) and benchmarks them against GPT-4/4o. Frames the work in terms of HIPAA-compliant on-premise deployment.

**Relevance to Project #2:** **Second-closest prior art.** The Task 1 → Task 2 decomposition is structurally similar to Project #2's resource-aware FHIR RAG, and both use Synthea. Critical differences: (a) no narrative-RAG baseline, (b) no naive flat-FHIR-JSON baseline, (c) no temporal/regimen focus, (d) the study's axis is fine-tuning, not retrieval representation.

**Cite for:** The nearest published prior art on structured FHIR QA over Synthea; explicitly differentiate on the three missing arms.

**Concerns:** arXiv-only as of April 2026; should be monitored for a peer-reviewed venue.

---

### 7. FHIR-GPT — Li et al., 2024

**Citation:** Li Y, Wang H, Yerebakan HZ, Shinagawa Y, Luo Y. *FHIR-GPT Enhances Health Interoperability with Large Language Models.* NEJM AI, 2024. DOI: 10.1056/AIcs2300301. Preprint: medRxiv 10.1101/2023.10.17.23297028. PMCID: PMC12312630.

**Summary:** Applies GPT-4 via 5 few-shot prompts to convert 3,671 clinical text snippets into FHIR MedicationStatement resources across drug, route, timing, dose, and reason-for-use fields. Achieves >90% exact-match across fields and outperforms prior rule-based and ML NLP pipelines by 3–50% per field.

**Relevance to Project #2:** Canonical demonstration that LLMs can produce well-formed FHIR from text — the **inverse** direction of Project #2's retrieval pipeline, and a useful anchor for discussing the LLM-FHIR interface in either direction.

**Cite for:** LLMs as FHIR producers (text → FHIR), to bracket Project #2's LLMs-as-FHIR-consumers angle (FHIR → answers).

**Concerns:** Scope limited to MedicationStatement; NEJM AI paywall, though medRxiv preprint and PMC version are open.

---

### 8. FHIR Workbench — Idrissi-Yaghir et al., 2025

**Citation:** Idrissi-Yaghir A, Arzideh K, Schäfer H, Eryilmaz B, Bahn M, Wen Y, Borys K, Hartmann E, Schmidt C, Pelka O, Haubold J, Friedrich CM, Nensa F, Hosch R. *Using a Diverse Test Suite to Assess Large Language Models on Fast Health Care Interoperability Resources Knowledge: Comparative Analysis.* Journal of Medical Internet Research 27:e73540, 12 August 2025. DOI: 10.2196/73540. PMID: 40795315. PMCID: PMC12360669.

**Summary:** Introduces the FHIR Workbench — a comparative benchmark over three task families: multiple-choice FHIR-concept questions, FHIR-resource reasoning, and a Note2FHIR generation task. Evaluates GPT-4, DeepSeek, and other LLMs, finding significant heterogeneity across FHIR resource types and persistent gaps between LLM and expert performance on nuanced FHIR semantics.

**Relevance to Project #2:** Establishes that LLMs have non-trivial but incomplete FHIR competence — directly motivates why FHIR-aware retrieval architectures matter (the LLM will not invent correct FHIR semantics unprompted).

**Cite for:** LLMs' baseline FHIR understanding; justifies why retrieval design, not just model scale, should drive FHIR QA quality.

**Concerns:** None — peer-reviewed JMIR, open access.

---

## Gap analysis

No prior work performs a **paired** head-to-head evaluation of (a) narrative RAG over LLM-generated clinical notes, (b) naive flat FHIR-JSON RAG, and (c) resource-aware FHIR RAG on the **same** patient cohort with a **temporally- and regimen-focused** QA set. The nearest analogs partition across three orthogonal axes: FHIR-AgentBench (Lee 2025) ablates **agentic strategy** within FHIR only, with no narrative baseline; Kothari & Gupta (2025) ablate **fine-tuning regime** on Synthea FHIR QA without narrative baselines or naive-JSON controls; LLM on FHIR (Schmiedmayer 2024) is a Synthea + FHIR deployment pilot without a benchmark comparison; and TIMER (Cui 2025) addresses **temporal reasoning via instruction tuning** rather than retrieval representation.

Project #2 fills a specific, narrow gap: **isolating the effect of retrieval representation** (narrative text vs. flat FHIR JSON vs. resource-aware FHIR) on temporally-grounded clinical QA, holding model scale, retriever, prompts, and patient cohort constant. A defensible one-sentence novelty claim is: *"To our knowledge, this is the first head-to-head evaluation of narrative-note RAG, naive flat FHIR-JSON RAG, and resource-aware FHIR RAG on a single paired cohort of Synthea-generated patients, using a programmatically-verified temporal and specialty-medication-regimen question set, isolating the effect of retrieval representation — rather than model scale, fine-tuning, or agentic orchestration — on patient-specific clinical question answering."* The related-work section must explicitly differentiate on two fronts: the **paired-data construct** (same patients rendered as both narrative and FHIR) and the **retrieval-representation axis** (not tuning, not agentic loops).

---

## BibTeX entries (append to `docs/literature/bibliography.bib`)

```bibtex
@article{engelke2025fhirformer,
  author  = {Engelke, Moritz and Baldini, Giulia and Kleesiek, Jens and Nensa, Felix and Dada, Amin},
  title   = {{FHIR-Former}: enhancing clinical predictions through {Fast Healthcare Interoperability Resources} and large language models},
  journal = {Journal of the American Medical Informatics Association},
  volume  = {32},
  number  = {12},
  pages   = {1793--1801},
  year    = {2025},
  month   = dec,
  doi     = {10.1093/jamia/ocaf165},
  pmcid   = {PMC12646377}
}

@article{grimes2025sqlonfhir,
  author  = {Grimes, John and Brush, Ryan and Ryzhikov, Nikolai and Szul, Piotr and Mandel, Joshua and Gottlieb, Daniel and Grieve, Grahame and Sadjad, Bashir and Sanyal, Aditi},
  title   = {{SQL on FHIR} --- Tabular views of {FHIR} data using {FHIRPath}},
  journal = {npj Digital Medicine},
  volume  = {8},
  number  = {1},
  pages   = {342},
  year    = {2025},
  month   = jun,
  doi     = {10.1038/s41746-025-01708-w},
  pmid    = {40490535}
}

@article{grimes2022pathling,
  author  = {Grimes, John and Szul, Piotr and Metke-Jimenez, Alejandro and Lawley, Michael and Loi, Kayvan},
  title   = {{Pathling}: analytics on {FHIR}},
  journal = {Journal of Biomedical Semantics},
  volume  = {13},
  number  = {1},
  pages   = {23},
  year    = {2022},
  month   = sep,
  doi     = {10.1186/s13326-022-00277-1},
  pmid    = {36076268}
}

@article{schmiedmayer2024llmonfhir,
  author  = {Schmiedmayer, Paul and Rao, Adrit and Zagar, Philipp and Ravi, Vishnu and Zahedivash, Aydin and Fereydooni, Arash and Aalami, Oliver},
  title   = {{LLM} on {FHIR} --- Demystifying Health Records},
  journal = {arXiv preprint arXiv:2402.01711},
  year    = {2024},
  doi     = {10.48550/arXiv.2402.01711},
  note    = {Peer-reviewed version: PMC12144420}
}

@article{lee2025fhiragentbench,
  author  = {Lee, Gyubok and Bach, Elea and Yang, Eric and Pollard, Tom J. and Johnson, Alistair E. W. and Choi, Edward and Jia, Yugang and Lee, Jong Ha},
  title   = {{FHIR-AgentBench}: Benchmarking {LLM} Agents for Realistic Interoperable {EHR} Question Answering},
  journal = {arXiv preprint arXiv:2509.19319},
  year    = {2025},
  doi     = {10.48550/arXiv.2509.19319}
}

@article{kothari2025patientqa,
  author  = {Kothari, Sara and Gupta, Ayush},
  title   = {Question Answering on Patient Medical Records with Private Fine-Tuned {LLMs}},
  journal = {arXiv preprint arXiv:2501.13687},
  year    = {2025},
  doi     = {10.48550/arXiv.2501.13687}
}

@article{li2024fhirgpt,
  author  = {Li, Yikuan and Wang, Hanyin and Yerebakan, Halid Ziya and Shinagawa, Yoshihisa and Luo, Yuan},
  title   = {{FHIR-GPT} Enhances Health Interoperability with Large Language Models},
  journal = {NEJM AI},
  year    = {2024},
  doi     = {10.1056/AIcs2300301},
  note    = {Preprint: medRxiv 10.1101/2023.10.17.23297028; PMCID PMC12312630}
}

@article{idrissiyaghir2025fhirworkbench,
  author  = {Idrissi-Yaghir, Ahmad and Arzideh, Kamyar and Sch{\"a}fer, Henning and Eryilmaz, Bahadir and Bahn, Maximilian and Wen, Yufan and Borys, Kevin and Hartmann, Eva and Schmidt, Christoph and Pelka, Obioma and Haubold, Johannes and Friedrich, Christoph M. and Nensa, Felix and Hosch, Ren{\'e}},
  title   = {Using a Diverse Test Suite to Assess Large Language Models on {Fast Health Care Interoperability Resources} Knowledge: Comparative Analysis},
  journal = {Journal of Medical Internet Research},
  volume  = {27},
  pages   = {e73540},
  year    = {2025},
  month   = aug,
  doi     = {10.2196/73540},
  pmid    = {40795315},
  pmcid   = {PMC12360669}
}
```

---

## Notes on reusable citations from prior metricHEALTH lit review

- **Mandel et al. 2016 (SMART on FHIR)** — **REUSE.** Canonical foundational FHIR citation; needed in the introduction to motivate why FHIR is the right substrate. No re-research needed.
- **Ayaz et al. 2021 (FHIR systematic review)** — **REUSE selectively.** Good for one sentence on FHIR's breadth of adoption across clinical domains in the introduction. Do not cite in related work — prefer primary sources (FHIR-Former, SQL-on-FHIR, Pathling) there.
- **Walonoski et al. 2018 (Synthea)** — **REUSE, mandatory.** This is the Synthea synthetic-patient-generator citation; required in the Dataset/Methods section to describe paired-data construction. Already in context.
- **Gabriel et al. 2025 (ASTP Data Brief)** — **DEPRIORITIZE** for Project #2. Adoption/policy signal better fits Project #1 or #3 framing; Project #2 is a methods paper where FHIR ubiquity can be cited in one sentence via Ayaz 2021 instead.
- **HL7 / Firely 2025 (State of FHIR)** — **DEPRIORITIZE** for Project #2 for the same reason; optional single-sentence cite if needed to justify FHIR as the retrieval substrate but not central to the methods contribution.

### Secondary-mention-only papers (not full entries, but worth keeping in the BibTeX for optional cites)

- **Gruendner et al. 2019 — KETOS** (PLoS ONE 14(10):e0223010, DOI 10.1371/journal.pone.0223010) — Foundational FHIR + ML platform; mention in one sentence on the analytics-platform lineage if space permits.
- **Prud'hommeaux et al. 2021 — FHIR RDF** (J Biomed Inform 117:103755, DOI 10.1016/j.jbi.2021.103755) — The closest thing to a "FHIRCat" canonical paper; cite only if discussing semantic/RDF FHIR representations.
- **Frei et al. 2025 — Infherno** (arXiv:2507.12261, EACL 2026 Demo) — Text-to-FHIR agent; cite alongside FHIR-GPT if expanding the text→FHIR direction.
- **Xiong et al. 2024 — MedRAG/MIRAGE** (arXiv:2402.13178, ACL Findings 2024) — Canonical clinical RAG benchmark, though over literature not EHRs; cite in one sentence to situate Project #2 as the patient-record analog.
- **Kweon et al. 2024 — EHRNoteQA** (arXiv:2402.16040, NeurIPS D&B 2024) — Narrative-note EHR QA benchmark; directly comparable to the narrative arm of Project #2.
- **Cui et al. 2025 — TIMER** (arXiv:2503.04176) — Temporal instruction tuning on longitudinal EHRs; cite to justify the temporal-QA emphasis.

### Flagged items from the task brief

- **"FHIRCat" as a system** — partially a misnomer. FHIRCat is an NIH-funded project (R01 EB030529, PI Guoqian Jiang, Mayo Clinic), not a single ML analytics platform. The primary peer-reviewed anchor is Prud'hommeaux et al. 2021 (J Biomed Inform) on FHIR RDF tooling. Safe to omit from Project #2 unless RDF/semantic FHIR becomes relevant to the resource-aware RAG design.
- **"Arzideh/Tabari et al." for Infherno** — authorship was miscoded in the brief. Infherno is Frei, Feldhus, Raithel, Roller, Meyer, Kramer (arXiv:2507.12261). Arzideh co-authored the FHIR Workbench (entry 8); Tabari leads a separate 2025 SHTI FHIR-validation paper. Corrected in the BibTeX above.
- **HL7 SQL-on-FHIR Implementation Guide** — cite `sql-on-fhir.org/ig/latest/` as the normative spec if needed in the Methods section; the Grimes 2025 npj paper (entry 2) is the preferred peer-reviewed citation for most arguments.