# Clinical RAG literature review (Block 1)

**Scope:** RAG for clinical/medical question answering, prior art most relevant to paired narrative-vs-structured RAG over FHIR EHR data for specialty medication QA. 8 papers selected for defensive coverage of the closest methodological predecessors.

**Bottom line:** Clinical RAG is an active, crowded research area, but **no existing work conducts a paired, same-question comparison of narrative RAG vs structured FHIR-resource RAG on the same EHR corpus**. The closest threats are FHIR-AgentBench (ML4H 2025), LLMonFHIR (JACC Adv 2025), and CLEAR (npj Digital Medicine 2025). Each is narrow in a way that leaves a defensible niche.

---

## Core papers (8)

### 1. Lewis et al. 2020 — original RAG (canonical)
- **Title:** Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks
- **Authors:** Patrick Lewis, Ethan Perez, Aleksandra Piktus, Fabio Petroni, Vladimir Karpukhin, Naman Goyal, Heinrich Küttler, Mike Lewis, Wen-tau Yih, Tim Rocktäschel, Sebastian Riedel, Douwe Kiela
- **Year / venue:** 2020, NeurIPS
- **arXiv:** 2005.11401; **Open access:** Yes (arXiv, NeurIPS proceedings)
- **Summary:** Introduces the RAG paradigm — a sequence-to-sequence generator conditioned on documents retrieved from a dense index (DPR over Wikipedia), trained end-to-end on open-domain QA and other knowledge tasks. The paper establishes **parametric + non-parametric memory** as a canonical design, with two variants (RAG-Sequence and RAG-Token). Not clinical, but the mandatory citation anchor when motivating any RAG system.
- **Relevance:** Cite as the origin of the paradigm; our work specializes its retrieval module to FHIR resources rather than Wikipedia passages.

### 2. Xiong et al. 2024 — MedRAG / MIRAGE (medical RAG benchmark)
- **Title:** Benchmarking Retrieval-Augmented Generation for Medicine
- **Authors:** Guangzhi Xiong, Qiao Jin, Zhiyong Lu, Aidong Zhang
- **Year / venue:** 2024, Findings of ACL
- **arXiv:** 2402.13178; **DOI:** 10.18653/v1/2024.findings-acl.372; **Open access:** Yes (ACL Anthology, arXiv)
- **Summary:** Proposes **MIRAGE** (7,663 multiple-choice biomedical/clinical QA items from MMLU-Med, MedQA-US, MedMCQA, PubMedQA*, BioASQ-Y/N) and **MedRAG** toolkit combining four corpora (PubMed, StatPearls, textbooks, Wikipedia) with retrievers (BM25, Contriever, SPECTER, MedCPT) across six LLMs. Finds up to +18% accuracy over CoT, a log-linear scaling with retrieved-document count, and **lost-in-the-middle effects in medical RAG**. Key sparse-vs-dense comparison reference — MedCPT (domain-tuned dense) and BM25 trade places depending on corpus.
- **Relevance:** The **canonical medical-RAG benchmark paper**; our work differs in that it operates over per-patient FHIR EHR data rather than public literature/exam corpora, and on open-ended specialty medication questions rather than MCQA.

### 3. Zakka et al. 2024 — Almanac (clinical-RAG reference)
- **Title:** Almanac — Retrieval-Augmented Language Models for Clinical Medicine
- **Authors:** Cyril Zakka, Rohan Shad, Akash Chaurasia, Alex R. Dalal, Jennifer L. Kim, Michael Moor, Robyn Fong, Curran Phillips, Kevin Alexander, Euan Ashley, Jack Boyd, Kathleen Boyd, Karen Hirsch, Curt Langlotz, Rita Lee, Joanna Melia, Joanna Nelson, Karim Sallam, Stacey Tullis, Melissa Ann Vogelsong, John Patrick Cunningham, William Hiesinger
- **Year / venue:** 2024, NEJM AI 1(2):AIoa2300068
- **DOI:** 10.1056/AIoa2300068; **Open access:** Paywalled (NEJM AI); preprint accessible
- **Summary:** A **curated retrieval LLM for clinical decision support** grounded in vetted guidelines and literature. On 130 clinician-authored questions across cardiology/nephrology/etc., Almanac materially outperforms base GPT-4 on factuality and safety as rated by a board-certified panel. Establishes that **clinician evaluation is the gold standard for clinical RAG** and that grounding in curated guideline corpora reduces hallucination.
- **Relevance:** Anchor citation for "clinical RAG works and matters"; contrasts with our setting in that Almanac retrieves over *literature/guideline* text, not per-patient EHR data.

### 4. Wu et al. 2024/2025 — MedGraphRAG (graph RAG in medicine)
- **Title:** Medical Graph RAG: Towards Safe Medical Large Language Model via Graph Retrieval-Augmented Generation
- **Authors:** Junde Wu, Jiayuan Zhu, Yunli Qi, Jingyi Chen, Min Xu, Filippo Menolascina, Vicente Grau
- **Year / venue:** 2024 arXiv preprint; 2025 ACL
- **arXiv:** 2408.04187; **Open access:** Yes (arXiv + GitHub ImprintLab/Medical-Graph-RAG)
- **Summary:** Builds a **triple-linked hierarchical graph** connecting (i) private user documents (MIMIC-IV as the private-data tier), (ii) medical literature/textbooks (MedC-K/S2ORC), and (iii) controlled vocabularies (UMLS). Retrieval uses a "U-Retrieve" strategy (top-down precise + bottom-up refinement). Evaluated on 9 medical QA benchmarks and health fact-checking; reports consistent gains over text-RAG baselines and supports evidence-based citations.
- **Relevance:** Most-cited example of **structured/graph retrieval beating flat text RAG in medicine**. Its "private tier" uses MIMIC-IV but the graph is over unstructured notes, not FHIR resources, and it does not do a paired narrative-vs-structured head-to-head on the same EHR corpus.

### 5. Soman et al. 2024 — KG-RAG over SPOKE
- **Title:** Biomedical Knowledge Graph-Optimized Prompt Generation for Large Language Models
- **Authors:** Karthik Soman, Peter W. Rose, John H. Morris, Rabia E. Akbas, Brett Smith, Braian Peetoom, Catalina Villouta-Reyes, Gabriel Cerono, Yongmei Shi, Angela Rizk-Jackson, Sharat Israni, Charlotte A. Nelson, Sui Huang, Sergio E. Baranzini
- **Year / venue:** 2024, Bioinformatics 40(9):btae560 (arXiv preprint 2023)
- **arXiv:** 2311.17330; **DOI:** 10.1093/bioinformatics/btae560; **Open access:** Yes (Oxford OA + PMC11441322)
- **Summary:** A **task-agnostic KG-RAG framework** that extracts entities from queries, matches them to SPOKE biomedical KG nodes, prunes context via embedding similarity, and feeds a minimal subgraph to Llama-2-13b/GPT-3.5/GPT-4. Reports **>50% token reduction vs naive graph-RAG without accuracy loss** on biomedical knowledge-intensive tasks (MCQ benchmarks, true-false, drug-disease). Establishes that **schema-aware structured retrieval can match dense text retrieval at lower cost**.
- **Relevance:** Direct prior art for the "resource-aware structured retrieval beats naive" thesis, but in a literature-KG setting rather than per-patient FHIR data — a useful methodological analogue, not a direct competitor.

### 6. Lopez et al. 2025 — CLEAR (structured-entity vs embedding RAG on clinical notes)
- **Title:** Clinical Entity Augmented Retrieval for Clinical Information Extraction
- **Authors:** Iván López, Akshay Swaminathan, Karthik Vedula, Sanjana Narayanan, Fateme Nateghi Haredasht, Stephen P. Ma, April S. Liang, Steven Tate, Manoj Maddali, Robert J. Gallo, Nigam H. Shah, Jonathan H. Chen
- **Year / venue:** 2025, npj Digital Medicine 8:45
- **DOI:** 10.1038/s41746-024-01377-1; **PMID:** 39828800; **Open access:** Yes (Nature OA + PMC11743751)
- **Summary:** CLEAR is a RAG pipeline that retrieves by **matched clinical entities (problems, drugs, labs)** rather than embedding chunks. Evaluated on **20,000 clinical notes across 18 extraction variables with 6 LLMs** against (a) full-note prompting and (b) embedding RAG. Reports F1 **0.90 (CLEAR) vs 0.86 (embedding RAG) vs 0.79 (full-note)**, with 71% token reduction and 72% faster inference. **This is the closest methodological sibling** to our paired comparison, but (a) it operates on narrative notes, not FHIR structured resources, and (b) the task is information extraction, not open-ended QA.
- **Relevance:** Must cite as the strongest precedent for "entity/structure-aware retrieval beats embedding RAG on EHR-adjacent data." Our contribution moves the same comparison axis (naive vs structure-aware) onto the structured-FHIR side.

### 7. Schmiedmayer et al. 2025 — LLMonFHIR
- **Title:** LLMonFHIR: A Physician-Validated, Large Language Model–Based Mobile Application for Querying Patient Electronic Health Data
- **Authors:** Paul Schmiedmayer, Adrit Rao, Philipp Zagar, Lauren Aalami, Vishnu Ravi, Aydin Zahedivash, Dong-han Yao, Arash Fereydooni, Oliver Aalami
- **Year / venue:** 2025, JACC: Advances 4(6 Pt 1):101780
- **DOI:** 10.1016/j.jacadv.2025.101780; **PMID:** 40373519; **PMC:** PMC12144420; **Open access:** Yes (CC BY)
- **Summary:** Open-source mobile app that uses **GPT-4 function-calling as a query-specific retrieval abstraction over FHIR resources** (Patient, Condition, Observation, MedicationRequest, etc.) exposed via Apple HealthKit and standard FHIR endpoints. Evaluated by physicians (5-point Likert accuracy/understandability/relevance) on 6 SyntheticMass FHIR patient datasets. Authors explicitly note **weaknesses in summarizing conditions and retrieving lab results**, citing need for precise pre-processing of FHIR data.
- **Relevance:** The **closest functional predecessor** — uses RAG over live FHIR resources for patient-facing QA. Critical differences: (i) evaluates only structured function-calling retrieval, not a narrative baseline; (ii) small physician-rated pilot, not programmatic QA scoring; (iii) synthetic data; (iv) patient-facing general queries, not specialty-medication clinical QA. Our paired comparison on a larger automated benchmark is the natural next step.

### 8. Lee et al. 2025 — FHIR-AgentBench (biggest novelty threat)
- **Title:** FHIR-AgentBench: Benchmarking LLM Agents for Realistic Interoperable EHR Question Answering
- **Authors:** Gyubok Lee, Elea Bach, Eric Yang, Tom Pollard, Alistair Johnson, Edward Choi, Yugang Jia, Jong Ha Lee
- **Year / venue:** 2025, ML4H (PMLR Vol. 297)
- **arXiv:** 2509.19319; **Open access:** Yes (arXiv + github.com/glee4810/FHIR-AgentBench)
- **Summary:** A **2,931-question benchmark grounded in MIMIC-IV-FHIR** with clinician-sourced questions from EHRSQL-2024, plus ground-truth FHIR resource IDs enabling resource-level precision/recall. Systematically compares agent architectures — single-turn vs multi-turn, natural-language vs code reasoning, **FHIR query generator vs specialized retriever tools** — using o4-mini, Gemini-2.5-Flash, Qwen3-32B, Llama-3.3-70B. Best configuration (multi-turn + retriever + code) reaches only **50% answer correctness**. Retrieval precision stays low across all configurations, and **medication questions are the single worst-performing resource type** (answer correctness 5–14%), attributed to the `MedicationRequest → Medication` reference-following gap.
- **Relevance:** This is the single **most dangerous prior work** for reviewer novelty challenges. Verified differences that preserve our niche:
  1. FHIR-AgentBench compares **retrieval mechanisms within structured FHIR** (FHIR API calls vs typed-retriever tools vs code-augmented) — it does **not** include a narrative-RAG arm where FHIR bundles are serialized to text and retrieved by BM25/dense embeddings. This is the exact axis our paper adds.
  2. It is an **agentic, multi-turn, code-executing** benchmark; our framing is simpler, paired retrieval pipelines with matched generator.
  3. General point-of-care questions on MIMIC-IV — **not specialty-medication QA**; the authors' own results flag medication questions as the weakest class, which is the exact gap our specialty-medication focus targets.
  4. Evaluation is LLM-judge (o4-mini) on free-text answers with 97% human agreement on 500 samples — a useful methodological precedent we can follow.

---

## Summary table

| # | Paper | Retrieval type | Data domain | Evaluation | Type |
|---|-------|----------------|-------------|------------|------|
| 1 | Lewis 2020 (RAG) | Dense (DPR) | Wikipedia / open-domain | Programmatic | Methods |
| 2 | Xiong 2024 (MedRAG/MIRAGE) | Sparse + dense + hybrid (BM25, Contriever, SPECTER, MedCPT) | Literature + guidelines (PubMed, StatPearls, textbooks) | Programmatic (MCQ) | Benchmark |
| 3 | Zakka 2024 (Almanac) | Dense (curated) | Guidelines + literature | Human (clinician panel) | Methods + eval |
| 4 | Wu 2024 (MedGraphRAG) | Structured (hierarchical KG, triple graph) | MIMIC-IV notes + literature + UMLS | Programmatic (9 QA benchmarks) | Methods |
| 5 | Soman 2024 (KG-RAG/SPOKE) | Structured (biomedical KG) | SPOKE KG (literature-derived) | Programmatic | Methods |
| 6 | Lopez 2025 (CLEAR) | Structured (clinical entities) vs dense (embedding RAG) | Clinical notes (narrative EHR) | Programmatic (F1 on 18 variables) | Methods |
| 7 | Schmiedmayer 2025 (LLMonFHIR) | Structured (function-calling over FHIR) | FHIR EHR (SyntheticMass) | Human (physician Likert) | Application |
| 8 | Lee 2025 (FHIR-AgentBench) | Structured: FHIR API vs typed-retriever vs code-augmented | FHIR EHR (MIMIC-IV-FHIR) | LLM-judge + retrieval P/R | Benchmark |

---

## Gap analysis

**Defensible novelty claim (narrow, precise):**

> To our knowledge, this is the first paired, same-question comparison of (i) narrative RAG over serialized FHIR bundles, (ii) naive structured FHIR-resource retrieval, and (iii) resource-aware structured retrieval, evaluated on specialty-medication clinical question answering grounded in FHIR EHR data.

**What is NOT claimed (to keep defence tight):**
- Not the first clinical RAG system (Zakka 2024, Almanac).
- Not the first medical RAG benchmark (Xiong 2024, MIRAGE).
- Not the first structured/graph retrieval in medicine (Soman 2024; Wu 2024).
- Not the first RAG over FHIR (Schmiedmayer 2025, LLMonFHIR; Lee 2025, FHIR-AgentBench).
- Not the first structured-vs-dense comparison on EHR data (Lopez 2025, CLEAR — but on narrative notes).

**What IS novel (four-part intersection, each part verified against prior art):**
1. **Paired comparison of narrative vs structured retrieval on identical FHIR data and identical question set.** FHIR-AgentBench ablates retrieval mechanisms but all within the structured-FHIR paradigm; LLMonFHIR evaluates only the function-calling structured variant; CLEAR does the paired comparison but on narrative notes, not FHIR.
2. **Resource-aware vs naive structured retrieval within FHIR.** FHIR-AgentBench's "specialized retriever" is resource-type-typed (closest precedent) but does not explicitly frame or evaluate the naive-vs-resource-aware axis as a controlled contrast — and in fact their medication results (5–14% correctness) show this is an unsolved axis.
3. **Specialty medication QA as the target domain.** All listed prior work targets either general medical MCQA (MIRAGE), general clinical guidelines (Almanac), or general EHR point-of-care questions (FHIR-AgentBench, LLMonFHIR). The applied-ML-at-a-Patient-Support-Program framing and specialty-medication narrowing are genuinely unoccupied.
4. **Programmatic + LLM-judge evaluation on open-ended answers** (as opposed to MCQ accuracy or physician Likert scales), following FHIR-AgentBench's methodological precedent.

**Papers to cite prominently in the novelty paragraph (in order of threat):**
1. Lee et al. 2025 (FHIR-AgentBench) — cite and differentiate on the narrative-arm axis and specialty-medication scope.
2. Schmiedmayer et al. 2025 (LLMonFHIR) — cite as closest functional precedent; differentiate on paired comparison and programmatic evaluation.
3. Lopez et al. 2025 (CLEAR) — cite as methodological sibling; differentiate on structured FHIR vs narrative notes.

**Recommended reviewer-proofing actions:**
- Read FHIR-AgentBench in full before submission and pre-register the exact retrieval arms to ensure the narrative-RAG arm is genuinely absent from their setup (verified here: it is).
- Add a one-line comparison table in the paper positioning our three arms against FHIR-AgentBench's five agentic configurations.
- In the limitations, explicitly note that we do not claim superiority to agentic multi-turn systems — only that we establish the narrative-vs-structured baseline gap they omit.

---

## BibTeX

```bibtex
@inproceedings{lewis2020retrieval,
  title        = {Retrieval-Augmented Generation for Knowledge-Intensive {NLP} Tasks},
  author       = {Lewis, Patrick and Perez, Ethan and Piktus, Aleksandra and Petroni, Fabio and Karpukhin, Vladimir and Goyal, Naman and K{\"u}ttler, Heinrich and Lewis, Mike and Yih, Wen-tau and Rockt{\"a}schel, Tim and Riedel, Sebastian and Kiela, Douwe},
  booktitle    = {Advances in Neural Information Processing Systems (NeurIPS)},
  volume       = {33},
  year         = {2020},
  eprint       = {2005.11401},
  archivePrefix= {arXiv},
  primaryClass = {cs.CL}
}

@inproceedings{xiong2024benchmarking,
  title        = {Benchmarking Retrieval-Augmented Generation for Medicine},
  author       = {Xiong, Guangzhi and Jin, Qiao and Lu, Zhiyong and Zhang, Aidong},
  booktitle    = {Findings of the Association for Computational Linguistics: ACL 2024},
  pages        = {6233--6251},
  year         = {2024},
  publisher    = {Association for Computational Linguistics},
  address      = {Bangkok, Thailand},
  doi          = {10.18653/v1/2024.findings-acl.372},
  eprint       = {2402.13178},
  archivePrefix= {arXiv}
}

@article{zakka2024almanac,
  title        = {Almanac --- Retrieval-Augmented Language Models for Clinical Medicine},
  author       = {Zakka, Cyril and Shad, Rohan and Chaurasia, Akash and Dalal, Alex R. and Kim, Jennifer L. and Moor, Michael and Fong, Robyn and Phillips, Curran and Alexander, Kevin and Ashley, Euan and Boyd, Jack and Boyd, Kathleen and Hirsch, Karen and Langlotz, Curt and Lee, Rita and Melia, Joanna and Nelson, Joanna and Sallam, Karim and Tullis, Stacey and Vogelsong, Melissa Ann and Cunningham, John Patrick and Hiesinger, William},
  journal      = {NEJM AI},
  volume       = {1},
  number       = {2},
  pages        = {AIoa2300068},
  year         = {2024},
  doi          = {10.1056/AIoa2300068}
}

@article{wu2024medgraphrag,
  title        = {Medical Graph {RAG}: Towards Safe Medical Large Language Model via Graph Retrieval-Augmented Generation},
  author       = {Wu, Junde and Zhu, Jiayuan and Qi, Yunli and Chen, Jingyi and Xu, Min and Menolascina, Filippo and Grau, Vicente},
  journal      = {arXiv preprint arXiv:2408.04187},
  year         = {2024},
  note         = {Also ACL 2025},
  eprint       = {2408.04187},
  archivePrefix= {arXiv},
  primaryClass = {cs.CL}
}

@article{soman2024biomedical,
  title        = {Biomedical Knowledge Graph-Optimized Prompt Generation for Large Language Models},
  author       = {Soman, Karthik and Rose, Peter W. and Morris, John H. and Akbas, Rabia E. and Smith, Brett and Peetoom, Braian and Villouta-Reyes, Catalina and Cerono, Gabriel and Shi, Yongmei and Rizk-Jackson, Angela and Israni, Sharat and Nelson, Charlotte A. and Huang, Sui and Baranzini, Sergio E.},
  journal      = {Bioinformatics},
  volume       = {40},
  number       = {9},
  pages        = {btae560},
  year         = {2024},
  doi          = {10.1093/bioinformatics/btae560},
  eprint       = {2311.17330},
  archivePrefix= {arXiv}
}

@article{lopez2025clinical,
  title        = {Clinical Entity Augmented Retrieval for Clinical Information Extraction},
  author       = {L{\'o}pez, Iv{\'a}n and Swaminathan, Akshay and Vedula, Karthik and Narayanan, Sanjana and Nateghi Haredasht, Fateme and Ma, Stephen P. and Liang, April S. and Tate, Steven and Maddali, Manoj and Gallo, Robert Joseph and Shah, Nigam H. and Chen, Jonathan H.},
  journal      = {npj Digital Medicine},
  volume       = {8},
  number       = {1},
  pages        = {45},
  year         = {2025},
  doi          = {10.1038/s41746-024-01377-1}
}

@article{schmiedmayer2025llmonfhir,
  title        = {{LLMonFHIR}: A Physician-Validated, Large Language Model--Based Mobile Application for Querying Patient Electronic Health Data},
  author       = {Schmiedmayer, Paul and Rao, Adrit and Zagar, Philipp and Aalami, Lauren and Ravi, Vishnu and Zahedivash, Aydin and Yao, Dong-han and Fereydooni, Arash and Aalami, Oliver},
  journal      = {JACC: Advances},
  volume       = {4},
  number       = {6 Pt 1},
  pages        = {101780},
  year         = {2025},
  doi          = {10.1016/j.jacadv.2025.101780}
}

@inproceedings{lee2025fhiragentbench,
  title        = {{FHIR-AgentBench}: Benchmarking {LLM} Agents for Realistic Interoperable {EHR} Question Answering},
  author       = {Lee, Gyubok and Bach, Elea and Yang, Eric and Pollard, Tom and Johnson, Alistair and Choi, Edward and Jia, Yugang and Lee, Jong Ha},
  booktitle    = {Proceedings of Machine Learning for Health (ML4H)},
  series       = {Proceedings of Machine Learning Research},
  volume       = {297},
  year         = {2025},
  eprint       = {2509.19319},
  archivePrefix= {arXiv},
  primaryClass = {cs.CL}
}
```

---

## Notes for the author

- **Second-pass reading priority before submission:** (1) FHIR-AgentBench §2 Related Works + §5.2 error analysis (medication reference-following is their documented weakness — a strong motivating hook for our paper); (2) LLMonFHIR's limitations section (same theme); (3) CLEAR's methods for their entity-based retrieval pipeline, since this is the closest methodological analogue for the "resource-aware" arm.
- **Papers deliberately excluded** despite appearing in searches: i-MedRAG, RAG²/Rationale-Guided, TC-RAG, HyKGE, MedAgentBench, Health-LLM — all add detail without changing the novelty picture and would bloat the review past the 8-paper cap. Mention only if a reviewer cites them.
- **Evaluation methodology precedent:** FHIR-AgentBench's LLM-judge (o4-mini) with 97% human agreement on a 500-sample manual audit is directly transferable and is now a defensible evaluation protocol in the ML4H community.
- **Date coverage:** All verified through direct fetches or full abstracts; Lewis 2020 is the only pre-2022 citation (canonical, as instructed).