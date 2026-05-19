# Block 9 — Evaluation methodology for RAG

## Executive summary

RAG evaluation circa 2024–2026 has split into two uneasy camps. **LLM-as-judge is the de facto standard for scalable automated scoring**, popularized by MT-Bench (Zheng et al., 2023) and productized in frameworks such as RAGAS, ARES, and TruLens that decompose quality into a retrieval/faithfulness/answer-relevance triad. But a parallel body of work has documented that these judges carry systematic positional, verbosity, self-preference, and expertise-alignment biases, with recent empirical evidence showing LLM–expert agreement falls well below expert–expert agreement in health-adjacent tasks (Szymanski et al., 2025). A second concern is **component entanglement**: retrieval recall and end-to-end answer correctness dissociate — readers saturate well before retrieval recall does (Liu et al., 2024) — making single-metric end-to-end scores unreliable diagnostics. In clinical NLP specifically, the longer-running tradition is **reference-based, programmatic evaluation** over structured sources: emrQA derives ground truth from i2b2 annotations, and EHRSQL scores predictions by SQL execution against MIMIC-III/eICU. Our work inherits the latter tradition and ports it to FHIR-grounded RAG, which — based on our search — appears to be an unoccupied niche.

## LLM-as-judge: reliability and bias concerns

Zheng et al. (2023), the paper that formalized the LLM-as-a-judge paradigm around MT-Bench and Chatbot Arena, also provided the canonical internal critique. On controlled probes they documented **position bias** (weaker judges flip verdicts when response order swaps; even GPT-4 shifts non-trivially), **verbosity bias** (longer answers are preferred even when not more accurate, demonstrated via a repetitive-list attack), and **self-enhancement bias** (models favor their own generations). Their headline claim — ~80% agreement with humans on non-math prompts — is pro-judge overall, but the documented failure modes are now the standard reference for why LLM-judge scores need mitigation (swap, few-shot, reference-guided) and still remain imperfect. We **cite as the foundational acknowledgment that LLM-as-judge carries position, verbosity, and self-enhancement biases**, motivating alternatives in high-stakes settings.

Szymanski et al. (2025, ACM IUI) move the critique into expert territory. They compared GPT-4-class judges against registered dietitians and clinical psychologists on pairwise response preferences and found **LLM–SME overall agreement of 68% (dietetics) and 64% (mental health), below the SME–SME baseline of ~72–75%**. Aspect-level decomposition showed the largest gaps on accuracy, actionability, personalization, and adherence to professional standards — exactly the dimensions that matter for clinical correctness. An "expert persona" prompt only partially helped, and hurt on some dimensions. The authors explicitly conclude LLM judges "cannot be trusted with final adjudication in fields like law or medicine." One caveat to note honestly: their domains are dietetics and clinical psychology, which are health-adjacent but not physician medical QA, so we frame this as *expert knowledge tasks including health domains* rather than as a direct specialty-medication-QA finding. We **cite as the strongest open-access empirical evidence that LLM judges systematically under-agree with domain experts in health-adjacent tasks**, directly justifying programmatic ground truth in a clinical context.

## Standard RAG evaluation frameworks

RAGAS (Es et al., EACL 2024) introduced a **reference-free automated RAG evaluation suite** built around three LLM-judged metrics: faithfulness (extract atomic claims from the answer, check NLI-style entailment against retrieved context), answer relevance (back-generate questions from the answer and score cosine similarity to the original), and context relevance (are retrieved passages only what is needed?). The authors validated correlations against human judgments on WikiEval and argued the approach enables iteration without ground-truth answers. **This is precisely the axis we diverge from**: our FHIR setting allows deterministic ground truth, so we can report reference-based correctness where RAGAS must estimate it. We cite RAGAS as the canonical automated framework whose triad decomposition we adopt conceptually while replacing its LLM-judged metrics with programmatic ones.

ARES (Saad-Falcon et al., NAACL 2024) targets the same triad as RAGAS — context relevance, answer faithfulness, answer relevance — but replaces heuristic prompts with **fine-tuned lightweight judges** trained on synthetic queries/passages and then uses **prediction-powered inference** over a few hundred human annotations to produce statistically valid confidence intervals on the estimated metrics. Across eight KILT/SuperGLUE/AIS tasks, ARES shows stronger human-agreement than prompt-only baselines (including RAGAS) and remains robust to domain shift. ARES also explicitly separates retrieval (context relevance) from generation (faithfulness, answer relevance) metrics, so it doubles as a component-wise framework. We **cite as the successor framework that introduced statistical rigor to automated RAG evaluation** and as a component-wise precedent; we note in passing that production tools such as TruLens operationalize the same triad without a peer-reviewed paper.

## Component-wise vs end-to-end evaluation

Liu et al. (2024, TACL) establish the empirical case for separating retrieval and answer metrics. Across multi-document QA and key–value retrieval experiments on GPT-3.5-Turbo-16k, Claude-1.3-100k, LongChat, and Flan-T5/UL2, they documented a **U-shaped accuracy curve**: models attend best to information at context start or end and degrade in the middle. The finding most relevant to us is their open-domain QA case study showing **"reader performance saturates far before retriever recall"** — adding more retrieved documents raises recall without proportional gains in answer accuracy. This empirical dissociation is the cleanest justification for reporting retrieval and end-to-end metrics as **independent axes rather than a single score**. Later work has contested the universality of the U-shape on newer long-context models, so we cite specifically for the reader-saturation finding, which has held up robustly. **Cite as motivation for reporting retrieval (recall@k, MRR) and answer correctness separately in our three-system comparison.**

## Faithfulness and groundedness evaluation

Gao et al. (ALCE, EMNLP 2023) introduced the first reproducible benchmark for **citation-grounded generation**, covering ASQA (factoid long-form), QAMPARI (list-style), and ELI5 (long-form explanations). Their evaluation decomposes into fluency (MAUVE), correctness (task-specific claim recall), and a dedicated **citation quality** axis: *citation recall* (fraction of generated statements fully supported by their cited passages, judged via an NLI model operationalizing the AIS attribution framework) and *citation precision* (fraction of citations actually relevant). Experiments with ChatGPT, LLaMA, and Vicuna under various prompting/retrieval strategies show that even state-of-the-art systems fall short of human citation quality, and that citation recall correlates strongly with factual correctness — making citation-level support a tractable proxy for groundedness. **Cite as precedent for claim-level, citation-grounded faithfulness evaluation**, which we adapt by checking whether each answer claim is supported by the retrieved FHIR resource it references.

## Programmatic and reference-based evaluation in clinical/medical domains

This subsection carries the most weight for our framing. Two papers establish the precedent we extend.

emrQA (Pampari et al., EMNLP 2018) is the **foundational programmatic EHR-QA dataset**. Rather than write QA pairs from scratch or have an LLM judge them post hoc, Pampari et al. **reused existing i2b2 expert annotations** (medications, relations, risk factors, coreference, smoking/obesity) and templatized them into ~1M question–logical-form pairs and 400k+ question–answer–evidence pairs. Because answers are mechanically derived from the underlying structured annotations, evaluation proceeds via exact match and F1 over evidence spans — fully reference-based. Every later structured EHR-QA benchmark descends from this pattern. We **cite as the canonical precedent for deriving clinical QA ground truth programmatically from structured clinical annotations** rather than from human or model adjudication.

EHRSQL (Lee et al., NeurIPS 2022) is the **closest structural analog** to our work. The authors collected 1,742 real information-need utterances from 222 hospital staff at three sites, templatized them into 230 question templates (174 answerable, 56 unanswerable), and hand-annotated executable SQL against MIMIC-III and eICU. **Evaluation is programmatic via SQL execution accuracy** — a prediction is scored by running the generated SQL against the database and comparing to the execution result of the gold SQL — and the benchmark further tests abstention on unanswerable questions (RS@k), which is itself programmatically verifiable. This is the most direct precedent for what we do with FHIR: treat the structured clinical record as the oracle and use deterministic lookup (rather than LLM-judge) at evaluation time. **Cite as the NeurIPS-grade precedent for execution-based evaluation over structured clinical data**, which we port from relational schemas to FHIR resources.

## Gap and positioning

Our search surfaced **no peer-reviewed primary paper that performs RAG over FHIR bundles and evaluates it with ground truth derived programmatically from those FHIR resources**. The adjacent work falls short of this specific combination on each dimension we care about: emrQA is programmatic but pre-RAG and over narrative notes; EHRSQL is programmatic but semantic parsing, not RAG, and uses custom relational schemas rather than FHIR; CLEAR (Lopez et al., *npj Digital Medicine* 2025) does retrieval over FHIR `DocumentReference` attachments but only evaluates with F1 against human-labeled extractions on 18 variables, and retrieves unstructured narrative rather than structured FHIR resources; recent medical RAG benchmarks such as MIRAGE, Almanac, and RAG² evaluate multiple-choice QA (MedQA, PubMedQA, MMLU-Med, BioASQ) over textual corpora and do not index FHIR. Informal demonstrations (e.g., the "RAG on FHIR" Medium blog using Synthea + LlamaIndex) exist but lack programmatic evaluation and are not peer-reviewed. We therefore position our work as combining **the programmatic-ground-truth rigor of the emrQA/EHRSQL tradition with a RAG setting over synthetic FHIR bundles**, comparing narrative, naive-structured, and resource-aware-structured retrieval under a single deterministic evaluation harness. The LLM-as-judge literature (Zheng, Szymanski) motivates why this deterministic harness matters; the framework literature (RAGAS, ARES, ALCE, Liu et al.) gives us the vocabulary (triad decomposition, retrieval/answer separation, citation-level grounding) that we translate into the FHIR setting.

---

## BibTeX

```bibtex
@inproceedings{zheng2023judging,
  title     = {Judging {LLM}-as-a-Judge with {MT}-Bench and Chatbot Arena},
  author    = {Zheng, Lianmin and Chiang, Wei-Lin and Sheng, Ying and
               Zhuang, Siyuan and Wu, Zhanghao and Zhuang, Yonghao and
               Lin, Zi and Li, Zhuohan and Li, Dacheng and Xing, Eric P. and
               Zhang, Hao and Gonzalez, Joseph E. and Stoica, Ion},
  booktitle = {Advances in Neural Information Processing Systems 36 (NeurIPS 2023) Datasets and Benchmarks Track},
  year      = {2023},
  eprint    = {2306.05685},
  archivePrefix = {arXiv},
  primaryClass  = {cs.CL},
  url       = {https://arxiv.org/abs/2306.05685}
}

@inproceedings{szymanski2025limitations,
  title     = {Limitations of the {LLM}-as-a-Judge Approach for Evaluating {LLM} Outputs in Expert Knowledge Tasks},
  author    = {Szymanski, Annalisa and Ziems, Noah and Eicher-Miller, Heather A. and
               Li, Toby Jia-Jun and Jiang, Meng and Metoyer, Ronald A.},
  booktitle = {Proceedings of the 30th International Conference on Intelligent User Interfaces (IUI '25)},
  year      = {2025},
  publisher = {Association for Computing Machinery},
  address   = {Cagliari, Italy},
  doi       = {10.1145/3708359.3712091},
  eprint    = {2410.20266},
  archivePrefix = {arXiv},
  primaryClass  = {cs.HC},
  url       = {https://arxiv.org/abs/2410.20266}
}

@inproceedings{es-etal-2024-ragas,
  title     = {{R}agas: Automated Evaluation of Retrieval Augmented Generation},
  author    = {Es, Shahul and James, Jithin and Espinosa-Anke, Luis and Schockaert, Steven},
  booktitle = {Proceedings of the 18th Conference of the European Chapter of the Association for Computational Linguistics: System Demonstrations},
  year      = {2024},
  address   = {St.\ Julians, Malta},
  publisher = {Association for Computational Linguistics},
  url       = {https://aclanthology.org/2024.eacl-demo.16/},
  eprint    = {2309.15217},
  archivePrefix = {arXiv},
  primaryClass  = {cs.CL}
}

@inproceedings{saadfalcon-etal-2024-ares,
  title     = {{ARES}: An Automated Evaluation Framework for Retrieval-Augmented Generation Systems},
  author    = {Saad-Falcon, Jon and Khattab, Omar and Potts, Christopher and Zaharia, Matei},
  booktitle = {Proceedings of the 2024 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies (Volume 1: Long Papers)},
  year      = {2024},
  pages     = {338--354},
  address   = {Mexico City, Mexico},
  publisher = {Association for Computational Linguistics},
  url       = {https://aclanthology.org/2024.naacl-long.20/},
  eprint    = {2311.09476},
  archivePrefix = {arXiv},
  primaryClass  = {cs.CL}
}

@article{liu-etal-2024-lost,
  title     = {Lost in the Middle: How Language Models Use Long Contexts},
  author    = {Liu, Nelson F. and Lin, Kevin and Hewitt, John and Paranjape, Ashwin
               and Bevilacqua, Michele and Petroni, Fabio and Liang, Percy},
  journal   = {Transactions of the Association for Computational Linguistics},
  volume    = {12},
  pages     = {157--173},
  year      = {2024},
  publisher = {MIT Press},
  doi       = {10.1162/tacl_a_00638},
  url       = {https://aclanthology.org/2024.tacl-1.9/},
  eprint    = {2307.03172},
  archivePrefix = {arXiv},
  primaryClass  = {cs.CL}
}

@inproceedings{gao-etal-2023-enabling,
  title     = {Enabling Large Language Models to Generate Text with Citations},
  author    = {Gao, Tianyu and Yen, Howard and Yu, Jiatong and Chen, Danqi},
  booktitle = {Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing},
  year      = {2023},
  pages     = {6465--6488},
  address   = {Singapore},
  publisher = {Association for Computational Linguistics},
  url       = {https://aclanthology.org/2023.emnlp-main.398/},
  doi       = {10.18653/v1/2023.emnlp-main.398},
  eprint    = {2305.14627},
  archivePrefix = {arXiv},
  primaryClass  = {cs.CL}
}

@inproceedings{pampari-etal-2018-emrqa,
  title     = {emr{QA}: A Large Corpus for Question Answering on Electronic Medical Records},
  author    = {Pampari, Anusri and Raghavan, Preethi and Liang, Jennifer and Peng, Jian},
  booktitle = {Proceedings of the 2018 Conference on Empirical Methods in Natural Language Processing},
  month     = oct # {-} # nov,
  year      = {2018},
  address   = {Brussels, Belgium},
  publisher = {Association for Computational Linguistics},
  url       = {https://aclanthology.org/D18-1258/},
  doi       = {10.18653/v1/D18-1258},
  pages     = {2357--2368},
  eprint    = {1809.00732},
  archivePrefix = {arXiv}
}

@inproceedings{lee2022ehrsql,
  title     = {{EHRSQL}: A Practical Text-to-{SQL} Benchmark for Electronic Health Records},
  author    = {Lee, Gyubok and Hwang, Hyeonji and Bae, Seongsu and Kwon, Yeonsu and
               Shin, Woncheol and Yang, Seongjun and Seo, Minjoon and
               Kim, Jong-Yeup and Choi, Edward},
  booktitle = {Advances in Neural Information Processing Systems 35 (NeurIPS 2022) Datasets and Benchmarks Track},
  pages     = {15589--15601},
  year      = {2022},
  url       = {https://proceedings.neurips.cc/paper_files/paper/2022/hash/643e347250cf9289e5a2a6c1ed5ee42e-Abstract-Datasets_and_Benchmarks.html},
  eprint    = {2301.07695},
  archivePrefix = {arXiv}
}
```

---

## Notes on choices (for the author)

- **8 papers, exactly the cap.** Trimmed from a 10-candidate shortlist.
- **Cut "Large Language Models are not Fair Evaluators" (Wang et al., ACL 2024)** despite its canonical positional-bias finding, because Zheng et al. already establishes positional bias with authoritative weight. If you want a sharper rhetorical hit on positional bias specifically (the Vicuna-beats-ChatGPT-by-reordering result), add Wang et al. arXiv:2305.17926 / `2024.acl-long.511`.
- **Cut the RGB benchmark (Chen et al., AAAI 2024)** because its component-wise story overlaps with ARES and Liu et al.
- **Optional additions if space opens up later**: FActScore (Min et al., EMNLP 2023, arXiv:2305.14251) for atomic-fact faithfulness; Williams et al. medRxiv 2025 (10.1101/2025.10.27.25338910) for direct physician-vs-LLM-judge clinical evidence (but preprint only — not yet peer-reviewed).
- **TruLens** is an industry framework with no peer-reviewed primary paper; mention in-text without a bib entry.
- **Szymanski caveat**: domains are dietetics and clinical psychology, not specialty medication QA — frame as "expert knowledge tasks including health domains" to avoid overclaim.
- **Lost-in-the-Middle caveat**: the U-shape itself has been partially contested on newer long-context models; cite specifically for the reader-saturation-before-retrieval-recall finding, which remains robust.
- **RAGAS caveat**: ARES authors (and others) have critiqued RAGAS's heuristic prompts as lacking statistical guarantees; note this honestly if positioning RAGAS as a gold-standard evaluator.
- **Gap claim is defensible**: no peer-reviewed primary paper found that does RAG over FHIR bundles with programmatically FHIR-derived ground truth. CLEAR (Lopez et al., *npj Digital Medicine* 2025) is the nearest adjacent work worth a one-line mention in the gap paragraph to sharpen the contrast.