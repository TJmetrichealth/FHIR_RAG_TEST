# Clinical LLM temporal reasoning, FHIR RAG, and the shrinking novelty window

**The space you are entering is active but not saturated.** Temporal reasoning over longitudinal electronic health records remains the weakest link in clinical LLM performance, with GPT-4 error rates of 35–65% on MedAlign and zero-shot temporal relation extraction trailing supervised baselines by wide margins. At the same time, three 2025 benchmarks — **LLMonFHIR, MedAgentBench, and FHIR-AgentBench** — have converged on exactly the design space of "RAG-over-FHIR," meaning a project pitched narrowly as "retrieve FHIR resources to answer patient questions" is already partially claimed. The defensible novelty now lies in **temporal-aware retrieval and reasoning over structured FHIR** — a seam that current benchmarks expose but do not solve. This report maps the foundational landscape, the LLM evaluation frontier, and the exact contours of the novelty threat.

## The foundational benchmarks define four distinct evaluation modes

Clinical temporal reasoning evaluation splits into four camps that rarely cross-pollinate, and understanding these boundaries is essential for positioning any new work.

**Temporal relation extraction from narrative text** traces back to the **i2b2 2012 temporal relations challenge** over 310 hospital discharge summaries, where events, time expressions, and TLINK relations were annotated. This tradition continues with MedTem (Tu et al., 2023, BiLSTM-CRF + BERT-CNN), GraphTrex (2025, span-based graph transformer achieving **68.81 end-to-end F1** on TLINKs), and the BioNLP temporal relation shared tasks. These benchmarks are narrative-only, pair-wise, and operate on single documents.

**Longitudinal instruction-following** is anchored by **MedAlign** (Fleming et al., AAAI 2024): 983 clinician-curated instructions grounded in 275 longitudinal OMOP EHRs, with 303 clinician-written reference responses. GPT-4 at 32k context achieves **60.1% correctness versus 51.8% at 2k** — a crucial finding that context length alone explains ~8.3 points, but a 40% error rate persists even with full context. Over 70% of MedAlign questions are simple retrieval, and **55.3% target the final 25% of patient timelines**, a severe recency bias.

**Structured few-shot prediction** is covered by **EHRSHOT** (Wornow et al., NeurIPS 2023): 6,739 Stanford patients, 41.6 million clinical events, 15 classification tasks, and released weights of CLMBR-T-base (141M parameter foundation model on 2.57M patient timelines). EHRSHOT is coded-data only, non-ICU-inclusive, and targets foundation model transfer — not LLM reasoning.

**Patient-specific QA** includes **EHRNoteQA** (MIMIC-IV, 962 multi-choice questions spanning multiple discharge summaries) where GPT-4 reaches **97.16% multi-choice / 91.02% free-text**, suggesting that when questions are well-scoped the ceiling is high.

## Temporal reasoning is where frontier models still fail

The evidence across 2023–2025 is consistent: **LLMs are substantially worse at temporal reasoning than at factual retrieval**, both in the general and clinical domains.

In general-domain benchmarks (**TRAM, ACL Findings 2024; TimeBench, ACL 2024; Test of Time**), GPT-4 trails human performance across frequency, duration, arithmetic, and relation tasks. Test of Time shows GPT-4 accuracy swings from **40.25% on complete temporal graphs to 92.00% on AWE-structured graphs**, revealing that performance depends heavily on how temporal structure is presented rather than on raw reasoning. RoBERTa-large surprisingly beats Llama2 on average — a signal that scale alone does not fix temporal deficits.

Clinical temporal relation extraction tells the same story. **Yuan et al. (BioNLP 2023)** showed ChatGPT zero-shot TempRE has a large gap versus supervised methods, with the model **unable to maintain consistency during temporal inference and failing on long-dependency relations**. The follow-up study (Knez & Žitnik, arXiv 2406.11486) tested GPT-3.5, Mixtral, Llama2-70B, Gemma-7B, and PMC-LLaMA across both Batch-of-Questions and Chain-of-Thought prompts on clinical notes; all underperformed fine-tuned models on F1, and all violated uniqueness and transitivity properties, meaning the models produced temporally contradictory answers for the same event pair.

**TIMER** (Cui et al., npj Digital Medicine 2025) is the most direct prior work on temporal-aware EHR evaluation. It introduces TIMER-Bench with timestamp-grounded instruction-response pairs and TIMER-Instruct tuning, reporting a **6.6% completeness improvement** over conventional medical instruction tuning. Critically, the paper documents that existing benchmarks "fail to evaluate models' capabilities to synthesize data over longitudinal records" and that physicians curating instructions default to isolated retrieval rather than multi-visit synthesis. This is a clear, published statement of the temporal synthesis gap.

Quantitative benchmarks on EHR reasoning outside QA reinforce the gap: Noroozizadeh et al. (arXiv 2504.10340) found prompted LLMs reach only **0.460 F1 at 24-hour clinical risk prediction versus 0.653 for fine-tuned encoders**, with prompting substantially worse than structured approaches. Hager et al. (Nature Medicine 2024) showed current LLMs fail to follow diagnostic or treatment guidelines and cannot interpret laboratory results when forced into realistic autonomous clinical decision-making on a 2,400-case curated dataset.

## The FHIR + RAG novelty window has closed on the naive formulation

Three 2025 papers have claimed the base "RAG over FHIR" territory, and any project must differentiate against them explicitly.

**LLMonFHIR** (Schmiedmayer et al., JACC Advances, May 2025) is the first-of-its-kind, physician-validated, open-source mHealth application that uses **function-calling RAG to dynamically retrieve only relevant FHIR resources** for patient-directed queries on SyntheticMass data. It is patient-facing rather than clinician-facing, iOS/HealthKit-based, and pilot-validated on chronic cardiovascular patients with multi-language and text-to-speech features. **The core retrieval abstraction — query-specific FHIR resource selection via function calling — is the default RAG pattern now.**

**MedAgentBench** (Jiang et al., NEJM AI 2025) provides a **FHIR-compliant Docker environment with 100 Stanford STARR patient profiles (700,000+ records) and 300 clinician-authored tasks across 10 categories**. It evaluates 12 LLMs and reports **Claude 3.5 Sonnet v2 at 69.67% success**, GPT-4o at 64%, DeepSeek-V3 at 62.67%. Task categories include retrieval, documentation, ordering, referrals, and medication management. Models fail primarily on action-based multi-step tasks, instruction adherence (invalid API calls, wrong JSON), and output format mismatch.

**FHIR-AgentBench** (Lee et al., ML4H 2025, arXiv 2509.19319) is the most recent and most overlapping: **2,931 real-world clinical questions grounded in MIMIC-IV-FHIR**, constructed by translating EHRSQL questions into FHIR-native queries. It explicitly names **temporal reasoning, navigating thousands of records, handling case-sensitive terminologies, and no-result queries** as its four challenge dimensions. It compares direct FHIR API calls vs. specialized tools and single- vs. multi-agent patterns, with error analysis showing retrieval failures from search-space misidentification and generation failures from FHIR complexity parsing. This benchmark alone absorbs much of the obvious contribution space.

Two additional adjacent systems compress the window further: **FHIR-GPT** (medRxiv 2023, updated) converts clinical narratives to FHIR resources (limited to MedicationStatement), and standards-integration pipelines (medRxiv 2025.02.25.25322898) map unstructured EHR data through NER + relation extraction into FHIR R4 / OMOP with validated outputs.

## Structured versus narrative retrieval shows a large performance gradient

The structured-vs-narrative comparison is one of the clearest signals in the RAG literature. A 20,000-question evidence-based clinical QA evaluation spanning GPT-4 and DeepSeek-v3 reported **90% accuracy on structured guidelines, 70% on narrative sources, and 50–60% on systematic reviews** — a 20–40 point swing driven purely by source format. This strongly supports the hypothesis that **converting narrative EHR content into FHIR-structured form before retrieval** yields accuracy gains independent of any temporal-reasoning innovation, but the published benchmarks above already lean on this insight.

Surgical fitness evaluations (Ge et al., npj Digital Medicine 2025) with 10 LLM-RAG configurations on 58 guidelines and 3,234 responses found the **GPT-4 LLM-RAG model exceeded human-generated answers (96.4% vs 86.6%, p = 0.016)** with zero hallucinations in the retrieved-guideline condition — but this is guideline retrieval, not patient-record retrieval.

## Where genuine novelty still lives

Given the saturation of base FHIR-RAG, the defensible research seams are narrower but real:

| Seam | Why it's open | Benchmark to target |
|---|---|---|
| Temporal-aware FHIR retrieval (time-window reasoning over Encounter, Observation, MedicationAdministration) | FHIR-AgentBench flags temporal reasoning as unsolved; MedAgentBench measures task completion but not temporal fidelity | FHIR-AgentBench temporal subset + MedAlign |
| Cross-visit synthesis (multi-encounter trajectory questions) | TIMER shows 55% of MedAlign targets final 25% of timeline; synthesis across visits is under-evaluated | TIMER-Bench + custom longitudinal split |
| Temporal consistency verification (uniqueness, transitivity of model outputs) | Knez & Žitnik 2024 show LLMs violate these properties; no production system checks them | Clinical TempRE datasets with consistency scoring |
| Hybrid structured-narrative retrieval (FHIR + note passages linked by timestamp) | DrugEHRQA and quEHRy handle one modality each; no unified retrieval | DrugEHRQA, custom MIMIC-IV mixed-modality |
| Tool-use for temporal arithmetic (age, duration, gap calculation) | MedAgentBench errors concentrate in action tasks requiring computation | MedAgentBench calculation subset |

The combination most defensible against prior art is **time-windowed, consistency-verified retrieval over FHIR resources with explicit temporal arithmetic tooling**, evaluated on multi-visit synthesis rather than single-fact retrieval. This position sidesteps LLMonFHIR (patient-facing, no temporal focus), MedAgentBench (action tasks, no temporal validity check), and FHIR-AgentBench (evaluates temporal reasoning but does not propose a temporal-aware retriever).

## Key takeaways

Clinical LLM temporal reasoning is a live, high-value failure mode with at least three converging lines of quantitative evidence: 35–65% MedAlign error rates, zero-shot TempRE trailing supervised by double-digit F1, and prompted LLMs losing to fine-tuned encoders on 24-hour risk prediction (0.460 vs 0.653). The FHIR + RAG architectural pattern is no longer novel in 2026 — LLMonFHIR, MedAgentBench, and FHIR-AgentBench collectively cover retrieval strategies, agent architectures, and clinical question authenticity at scale. The productive research frontier has shifted from "can we use RAG on FHIR" to "can we make FHIR-grounded reasoning temporally reliable," and TIMER plus FHIR-AgentBench's error analyses explicitly point toward this gap. Any new project should frame its contribution in the temporal-fidelity or cross-visit-synthesis lane, cite these three 2025 benchmarks as the immediate prior art to outperform, and validate on TIMER-Bench plus FHIR-AgentBench's temporal subset to demonstrate incremental value.