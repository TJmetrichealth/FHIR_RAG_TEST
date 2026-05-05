# Block 2 literature review: Structured vs. unstructured EHR for NLP and QA

**Bottom line.** No prior work we could identify constructs paired structured and narrative views of the **same patient record from the same underlying source with the same information content** for head-to-head clinical QA/retrieval evaluation. The closest precedents are Moldwin et al. (2021), which runs a same-patient structured-vs-text phenotyping comparison but draws the two views from independently authored MIMIC sources, and DrugEHRQA (Bardhan et al., 2022), which pairs structured tables with discharge notes for medication QA but explicitly acknowledges that information content differs across modalities. Methodologically, TabLLM (Hegselmann et al., 2023) and MEME/pseudo-notes (Lee et al., 2025) establish that serializing structured EHR into natural language is competitive with or superior to numeric/tabular pipelines, supporting the narrative-RAG arm of our design. The **novelty claim — "no prior work holds information content constant across FHIR-structured and LLM-narrative representations in a clinical QA setting" — is defensible** with minor qualification: we must cite Moldwin and DrugEHRQA as the closest same-patient paired-view prior art and differentiate explicitly on "held-constant information content via FHIR-to-narrative rendering from a shared bundle."

The literature also contains a strong methodological pattern worth citing defensively: across MIMIC-based predictive-modeling studies, unstructured notes alone frequently match or beat structured features, and fusion wins most often — a finding that motivates our narrative-RAG arm and justifies why representation (not information content) is the active variable we need to isolate.

---

## The seven papers

### 1. Moldwin, Demner-Fushman, and Goodwin (2021) — closest paired same-patient precedent

- **Citation:** Moldwin A, Demner-Fushman D, Goodwin TR. *Empirical Findings on the Role of Structured Data, Unstructured Data, and their Combination for Automatic Clinical Phenotyping.* AMIA Joint Summits on Translational Science Proceedings 2021;2021:445–454.
- **Link:** https://pmc.ncbi.nlm.nih.gov/articles/PMC8378600/ (PMC8378600; PMID 34457160)
- **Summary:** LSTMs predict 172 CCS phenotypes on MIMIC-III using three configurations of the **same ICU episodes**: 38 structured lab/chart features only; notes only (Bag-of-Words, MetaMap Bag-of-Concepts, Doc2Vec); and combined. Patient episodes are filtered so each patient has both views available, enabling a paired comparison. Doc2Vec text alone outperforms structured features for **145/172 (84%) phenotypes**. Combination beats structured alone for 51 phenotypes (circulatory, injury/poisoning dominate), ties on 120, and loses on 1 (diabetes without complications — glucose labs dominate). Structured alone still wins for in-hospital mortality and decompensation.
- **Category:** **C** (paired same-patient) + **B** (unstructured competitive) + **D** (explicit confound discussion).
- **Why it matters:** This is the single strongest precedent for our paired-view framing and the paper we must differentiate most carefully. It validates the logic of same-patient comparison but **does not hold information content constant** — MIMIC notes and MIMIC coded fields were authored independently. Our FHIR-bundle-derived narrative is a stronger "same information content" design.
- **Key quote (Category D):** *"it is not clear if the performance increase observed ... when adding structured data is due to information that is present in structured data but missing in clinical notes, or if the information is in fact present in clinical notes but is simply not captured."* This is the exact confound our construction resolves.
- **BibTeX key:** `moldwin2021empirical`

### 2. Bardhan, Colas, Roberts, and Wang (2022) — DrugEHRQA, closest paired-view QA dataset

- **Citation:** Bardhan J, Colas A, Roberts K, Wang DZ. *DrugEHRQA: A Question Answering Dataset on Structured and Unstructured Electronic Health Records For Medicine Related Queries.* Proceedings of LREC 2022, pp. 1083–1097.
- **Link:** https://arxiv.org/abs/2205.01290 ; https://aclanthology.org/2022.lrec-1.117/
- **Summary:** DrugEHRQA is the first medication-focused QA dataset drawing paired QA pairs from **both structured tables and unstructured discharge summaries of the same MIMIC-III patients** (~70k pairs). Baselines include RAT-SQL for the structured arm, extractive QA over notes, and a modality-selection network for fusion. The paper explicitly frames the two modalities as offering complementary, duplicative, or contradictory information, motivating cross-modal fusion.
- **Category:** **C** (same-patient paired) — but effectively a negative example for controlled information content.
- **Why it matters:** Topically the nearest prior work (medication QA, paired views, MIMIC). It **partially erodes** the generic "paired same-patient views" framing, so we must sharpen the novelty to the held-constant-information axis. Our arms are three renderings of a single FHIR bundle; theirs are two independently authored sources.
- **Key quote:** *"information across the two modalities is not strictly disjoint: information may be duplicated, contradictory, or provide additional context"* — a clean admission that information content is not held constant, which is precisely our wedge.
- **BibTeX key:** `bardhan2022drugehrqa`

### 3. Hegselmann et al. (2023) — TabLLM, the canonical tabular-to-text serialization precedent

- **Citation:** Hegselmann S, Buendia A, Lang H, Agrawal M, Jiang X, Sontag D. *TabLLM: Few-shot Classification of Tabular Data with Large Language Models.* Proceedings of AISTATS 2023, PMLR 206:5549–5581.
- **Link:** https://arxiv.org/abs/2210.10723 ; https://proceedings.mlr.press/v206/hegselmann23a.html
- **Summary:** Systematic study of nine serialization strategies (templates, table-to-text, LLM-narrative) for zero/few-shot classification with T0, benchmarked against XGBoost, LightGBM, and deep tabular models on nine public datasets plus a healthcare tabular task. Human-readable "text template" serialization generally wins; TabLLM beats prior deep tabular methods and is competitive with gradient-boosted trees in the few-shot regime by exploiting LLM prior knowledge bound to feature names.
- **Category:** **A/B** methodological foundation for serializing structured data to text.
- **Why it matters:** Cite as the origin of principled tabular-to-text serialization. It **does not threaten novelty** — single-row classification, no retrieval, no FHIR, no temporal reasoning — but it grounds our narrative-RAG arm in published methodology rather than ad-hoc prompting.
- **Key quote:** *"this technique outperforms prior deep-learning-based tabular classification methods ... competitive with strong traditional baselines like gradient-boosted trees, especially in the very-few-shot setting."*
- **BibTeX key:** `hegselmann2023tabllm`

### 4. Lee et al. (2025) — MEME, the closest pseudo-notes-from-structured-EHR sibling

- **Citation:** Lee SA, Jain S, Chen A, Ono K, Biswas A, Rudas A, Fang J, Chiang JN. *Clinical decision support using pseudo-notes from multiple streams of EHR data.* npj Digital Medicine 8(1):394, 2025. (Preprint: arXiv:2402.00160, 2024.)
- **Link:** https://arxiv.org/abs/2402.00160 ; https://www.nature.com/articles/s41746-025-01777-x
- **Summary:** Converts tabular EHR streams (diagnoses, meds, vitals, labs, triage) into modality-specific templated **pseudo-notes**, embeds each stream with a pretrained LM, and fuses via self-attention for ED decision tasks on MIMIC-IV-ED. MEME outperforms LR/RF/XGBoost/MLP on raw tabular data, coded-sequence EHR foundation models (EHR-SHOT/CLMBR, BEHRT variants, Clinical Longformer), and direct GPT-4 prompting of the pseudo-notes. Strong few-shot transfer to UCLA ED data because the text interface sidesteps concept harmonization.
- **Category:** **A/B** — structured→text serialization beats native-structured foundation models on classification.
- **Why it matters:** Closest methodological sibling. **Partial threat**: they have already shown that serializing structured EHR to narrative works for downstream use. We differentiate on (a) retrieval/QA vs classification, (b) FHIR resources vs ED tables, (c) three paired renderings of the **same bundle** for controlled representation comparison, and (d) explicit temporal/regimen reasoning questions.
- **Key quote:** *"training structured embedding-based classifiers remains superior to direct prompting approaches, even when instruction tuning is applied ... domain-specific models consistently outperform generalist AI models like GPT in structured clinical tasks."* This finding directly motivates our resource-aware structured RAG arm.
- **BibTeX key:** `lee2025pseudonotes`

### 5. Hashir and Sawhney (2020) — notes-only beats structured for ICU mortality

- **Citation:** Hashir M, Sawhney R. *Towards unstructured mortality prediction with free-text clinical notes.* Journal of Biomedical Informatics, 108:103489, 2020.
- **Link:** https://arxiv.org/abs/1911.08437
- **Summary:** Hierarchical CNN-RNN on minimally preprocessed free-text MIMIC-III notes outperforms structured-data baselines (severity scores and RNN over physiological time series) for in-hospital mortality, despite far less cleaning. Multimodal fusion achieves the highest metrics but the notes-only margin over structured is the headline.
- **Category:** **B**.
- **Why it matters:** Canonical citation for the claim that unstructured narrative contains competitive-to-superior signal for patient-level prediction — motivates including a narrative-RAG arm at all.
- **BibTeX key:** `hashir2020unstructured`

### 6. Lyu et al. (2022) — Multimodal Transformer on MIMIC-III

- **Citation:** Lyu W, Dong X, Wong R, Zheng S, Abell-Hart K, Wang F, Chen C. *A Multimodal Transformer: Fusing Clinical Notes with Structured EHR Data for Interpretable In-Hospital Mortality Prediction.* AMIA Annu Symp Proc 2022:719–728.
- **Link:** https://pmc.ncbi.nlm.nih.gov/articles/PMC10148371/
- **Summary:** Benchmarks structured-only (LSTM/Transformer), notes-only (Clinical BERT/MBERT), and multimodal fusion variants on MIMIC-III in-hospital mortality. Notes-only beats structured-only on AUROC (0.851 vs 0.827) and AUCPR (0.482 vs 0.473). A shared-space Multimodal Transformer wins overall (AUROC 0.877, AUCPR 0.538, F1 0.490).
- **Category:** **A + B** — fusion wins, notes edge structured, structured still carries unique signal.
- **Why it matters:** Representative of the dominant pattern in MIMIC literature (notes competitive, fusion wins) and an implicit Category D example: the two modalities are not information-matched, so the study measures representation plus information-content differences simultaneously. Useful foil for our controlled comparison.
- **BibTeX key:** `lyu2022multimodal`

### 7. Lee et al. (2025) — FHIR-AgentBench, structured-only FHIR QA benchmark

- **Citation:** Lee G, et al. *FHIR-AgentBench: Benchmarking LLM Agents for Realistic Interoperable EHR Question Answering.* arXiv:2509.19319, 2025 (ML4H 2025).
- **Link:** https://arxiv.org/abs/2509.19319
- **Summary:** Grounds 2,931 clinical questions (sourced from EHRSQL) in MIMIC-IV-on-FHIR and systematically compares agentic retrieval strategies over FHIR: direct API vs specialized tools, single- vs multi-turn, natural language vs code generation. All arms use the same FHIR data, so retrieval architectures are compared head-to-head. Reports consistent LLM failures in multi-hop reasoning and reference resolution over FHIR's nested structure.
- **Category:** **A** with partial **D** (reasoning-over-FHIR confounds).
- **Why it matters:** Strongest recent FHIR-QA benchmark, and critically, it **never renders the same bundle as narrative** — it is structured-only. This reinforces our novelty: no one in the FHIR-QA benchmark line of work has paired a narrative arm against typed structured arms on the same bundles. The failure modes it documents (multi-hop, reference resolution) directly motivate our resource-aware structured RAG design (typed filtering plus reference traversal).
- **BibTeX key:** `lee2025fhiragentbench`

---

## Synthesis of the landscape

The literature splits into three functional groups. **Group one — predictive modeling on MIMIC** (Hashir & Sawhney 2020, Lyu 2022, and many adjacent MIMIC fusion papers) — establishes that notes are competitive with structured data, that fusion wins, and that the two modalities are information-complementary. This work is **Category B-dominant with Category D bleeding in**: none of it holds information content constant, but several papers acknowledge the confound in passing. **Group two — serialization methodology** (Hegselmann TabLLM 2023, Lee MEME 2025) — establishes that LLM-friendly natural-language restatement of tabular data is a competitive interface, which legitimizes our narrative-RAG arm. **Group three — clinical QA and RAG benchmarks** (Bardhan DrugEHRQA 2022, Lee FHIR-AgentBench 2025, plus Moldwin 2021 which straddles groups one and three) — contains the closest precedents for our QA setup. Moldwin explicitly constructs a paired same-patient comparison for phenotyping. DrugEHRQA pairs structured tables and notes for medication QA. FHIR-AgentBench benchmarks structured-only FHIR retrieval strategies. **None of the three derives both views from a single shared source with identical information content.**

A distinctive feature of the target paper is therefore not the use of paired views per se — Moldwin and DrugEHRQA have this — but the **construction discipline**: because all three retrieval systems (narrative, naive structured, resource-aware structured) are built from the same FHIR bundles, any performance delta is attributable to representation and retrieval strategy, not to which source documented more facts. This control is what Moldwin explicitly wished for and did not have, and it is what DrugEHRQA explicitly disavows.

## Novelty-claim assessment

**The claim "no prior work holds information content constant across FHIR-structured and LLM-narrative representations in a clinical QA setting" is defensible**, provided the paper:

1. Cites **Moldwin 2021** as the closest paired same-patient precedent and explicitly notes that their structured and text views come from independently authored MIMIC sources, so information content is not controlled.
2. Cites **Bardhan 2022 (DrugEHRQA)** as the closest paired-view medication-QA dataset and quotes their admission that cross-modal information content differs.
3. Cites **Lee 2025 (MEME)** as the closest structured-to-narrative serialization sibling and differentiates on task (classification vs RAG/QA), scope (ED tables vs full FHIR bundles), and the paired-controlled-comparison design.
4. Cites **Lee 2025 (FHIR-AgentBench)** to show that the state-of-the-art FHIR QA benchmark line has no narrative arm.
5. Avoids the unsupported stronger claim "first paired structured-vs-unstructured clinical QA evaluation" — that is blocked by DrugEHRQA. The correct framing is **"first paired structured-vs-narrative clinical QA evaluation with held-constant information content via shared-source rendering."**

Write this defensively in the related-work section: the novelty is the methodological control (same bundle → three renderings), not the paired-view concept.

## Suggested BibTeX keys

- `moldwin2021empirical` — AMIA Joint Summits 2021
- `bardhan2022drugehrqa` — LREC 2022
- `hegselmann2023tabllm` — AISTATS 2023
- `lee2025pseudonotes` — npj Digital Medicine 2025 (arXiv:2402.00160 as `lee2024meme` for preprint)
- `hashir2020unstructured` — J Biomed Inform 2020
- `lyu2022multimodal` — AMIA 2022
- `lee2025fhiragentbench` — arXiv:2509.19319, ML4H 2025

## Gaps and flags for the coordinator

- **No standalone Category D paper** surfaced. The information-content confound is discussed inside Moldwin's introduction and implicitly throughout the MIMIC fusion literature, but no paper we located frames the confound as its primary methodological critique. If desired, the paper can make this critique itself and anchor it with the Moldwin quote above. An IPCI-cohort overlap study (medRxiv 2024) reportedly found 42% of structured concepts have unstructured matches vs 13% in the reverse direction — a striking quantification of the confound — but we did not independently verify the preprint and recommend the coordinator pull it directly before citing.
- **Several arXiv IDs surfaced during search had forward-dated formats** (e.g., `2602.*`, `2603.*`, `2604.*`) corresponding to very recent or unverifiable 2026 preprints (MediGRAF, FHIRPath-QA, an unnamed early-disease-prediction paper). We deliberately excluded these per the "do not cite unverified / abstract-only" constraint. If any become important, verify them individually before inclusion.
- **RAG-on-FHIR ecosystem papers** (LLMonFHIR, EHRAgent, MedAlign) are adjacent and belong in a different block focused on clinical RAG systems rather than the structured-vs-unstructured representation question treated here.