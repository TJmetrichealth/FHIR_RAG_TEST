# Retrieval strategies related work (Block 8)

This block positions the paper's resource-aware FHIR retriever — typed resource filtering, typed reference traversal, and resource-scoped temporal pre-filter — within the broader retrieval lineage. Coverage is intentionally compact and defensive: three foundational and clinical hybrid retrievers, three graph- and knowledge-graph-augmented RAG systems, one schema-aware structured-data reasoner, and one concurrent FHIR retrieval benchmark. The closing gap analysis argues narrowly that the intersection of (FHIR R4B typed-resource graph) × (reference-chain traversal as a retrieval primitive) × (temporal pre-filter) × (specialty medication QA) is unoccupied in the peer-reviewed literature through 2025.

## Hybrid retrieval foundations and clinical adaptation

**Robertson & Zaragoza (2009) — "The Probabilistic Relevance Framework: BM25 and Beyond."** *Foundations and Trends in Information Retrieval* 3(4), 333–389. DOI: 10.1561/1500000019. Robertson and Zaragoza consolidate the probabilistic relevance framework behind BM25 and BM25F, deriving the canonical term-frequency-saturation plus document-length-normalization ranking from the binary independence model and extending it to non-textual fields and relevance feedback. **Why it matters:** BM25 is the de facto sparse/lexical baseline that every modern RAG paper invokes when motivating hybrid retrieval, and in clinical settings its exact-term matching is especially important for codes and identifiers (RxNorm, NDC, LOINC, SNOMED) that specialty-medication questions depend on. **Cite for:** the sparse leg of the retrieval lineage and the justification for combining exact-match scoring with any dense or structured retriever over FHIR-derived text.

**Karpukhin et al. (2020) — "Dense Passage Retrieval for Open-Domain Question Answering."** *EMNLP 2020*, 6769–6781. arXiv:2004.04906. DOI: 10.18653/v1/2020.emnlp-main.550. DPR trains a dual-encoder over BERT with in-batch contrastive negatives and projects queries and passages into a shared space for maximum-inner-product retrieval, outperforming Lucene BM25 by 9–19 absolute points across five open-domain QA benchmarks. **Why it matters:** DPR is the canonical dense-retrieval reference point and directly motivates the narrative-RAG arm of our three-way comparison, where FHIR resources are serialized to text and embedded for passage retrieval. **Cite for:** the dense leg of the hybrid/narrative-RAG lineage and the reference encoder design against which domain-specific retrievers are benchmarked.

**Jin et al. (2023) — "MedCPT: Contrastive Pre-trained Transformers with large-scale PubMed search logs for zero-shot biomedical information retrieval."** *Bioinformatics* 39(11), btad651. DOI: 10.1093/bioinformatics/btad651. arXiv:2307.00589. MedCPT contrastively trains paired biomedical query and document encoders plus a cross-encoder re-ranker on **255M PubMed click pairs**, achieving zero-shot state-of-the-art on six biomedical IR tasks and outperforming general-domain DPR and GPT-scale embedding baselines. **Why it matters:** MedCPT is the standard domain-adapted dense retriever for clinical/biomedical text and the natural encoder choice for the narrative-RAG arm of our comparison over FHIR-rendered narratives. **Cite for:** the clinical dense-retrieval baseline that any FHIR-narrative retriever must be compared against, and as evidence that domain-specific encoders close only part of the gap structured retrieval is designed to eliminate.

## Graph- and knowledge-graph-augmented generation

**Edge et al. (2024) — "From Local to Global: A Graph RAG Approach to Query-Focused Summarization."** arXiv:2404.16130. Microsoft Research. Edge et al. use an LLM to extract an entity–relation graph from an unstructured corpus, partition it with Leiden community detection, pre-generate hierarchical community summaries, and answer queries by map-reducing partial answers from relevant communities — targeting query-focused summarization rather than fact lookup. **Why it matters:** GraphRAG is the canonical graph-RAG baseline; it defines the dominant design pattern (**LLM-extracted graph, community-summary retrieval**) against which any structured-graph RAG must position. Our FHIR graph is the opposite: schema-defined a priori with typed `Reference` fields from the HL7 specification, and we traverse targeted resource chains rather than summarize communities. **Cite for:** the LLM-generated-graph-RAG lineage and to contrast schema-defined clinical graphs with text-extracted entity graphs.

**Gutiérrez et al. (2024) — "HippoRAG: Neurobiologically Inspired Long-Term Memory for Large Language Models."** *NeurIPS 2024*. arXiv:2405.14831. HippoRAG extracts OpenIE triples with an LLM to build a schema-free knowledge graph and then performs **Personalized PageRank** from query-anchored nodes to retrieve multi-hop contextual passages in a single step, outperforming iterative RAG approaches like IRCoT at 10–30× lower cost. **Why it matters:** HippoRAG is the clearest precedent for *graph-traversal* retrieval rather than community-summary retrieval and is conceptually closest to our reference-traversal primitive. The distinction is provenance and typing: PPR over LLM-extracted, loosely-typed OpenIE edges versus deterministic traversal over FHIR-specification-typed references with fixed cardinality and semantics. **Cite for:** the graph-traversal retrieval lineage and to motivate deterministic typed traversal as a safer alternative for medication-safety QA.

**Wu et al. (2024) — "Medical Graph RAG: Towards Safe Medical Large Language Model via Graph Retrieval-Augmented Generation."** arXiv:2408.04187; ACL 2025. MedGraphRAG extends GraphRAG to medicine with a **three-tier graph** linking entities extracted from private clinical documents, credible medical literature, and controlled vocabularies, together with a U-Retrieval procedure that balances global and local context and emits source-attributed answers. **Why it matters:** MedGraphRAG is the most direct medical analogue of GraphRAG and therefore the clearest competitor to position against; however, its patient-side graph is still LLM-extracted from free-text notes. Our paper removes the extraction step on the patient side entirely by retrieving directly over the already-typed FHIR resource graph, eliminating a class of extraction errors that are particularly dangerous for specialty medication regimens. **Cite for:** medical graph-RAG prior art and the argument that structured FHIR avoids extraction-error risk on patient-level data.

## Schema-aware retrieval over structured data

**Jiang et al. (2023) — "StructGPT: A General Framework for Large Language Model to Reason over Structured Data."** *EMNLP 2023*, 9237–9251. arXiv:2305.09645. StructGPT proposes an **Iterative Reading-then-Reasoning** framework in which the LLM never sees the full structured store; instead it invokes typed interface functions (get-relation, get-neighbor, extract-column) that return schema-aware slices of KGs, tables, or databases, which the LLM then linearizes and reasons over — evaluated across KGQA, TableQA, and text-to-SQL benchmarks. **Why it matters:** StructGPT is the strongest peer-reviewed precedent for the general principle behind our approach — typed, schema-aware interfaces expose selective views of structured data to the LLM rather than dumping everything — but it is evaluated on generic schemas (Freebase, Wikidata, WebTables) with no notion of FHIR resources, polymorphic references, code-system bindings, patient timelines, or temporal pre-filters. **Cite for:** the schema-aware / typed-interface retrieval lineage and as the conceptual template our FHIR-specific retriever specializes.

## Retrieval and RAG directly on FHIR

**Lee et al. (2025) — "FHIR-AgentBench: Benchmarking LLM Agents for Realistic Interoperable EHR Question Answering."** arXiv:2509.19319. Presented at ML4H 2025. FHIR-AgentBench grounds 2,931 clinician-authored questions (derived from EHRSQL) in MIMIC-IV-FHIR and systematically varies agent design along three axes — retrieval strategy (direct FHIR API calls vs. specialized tools), interaction pattern (single- vs. multi-turn), and reasoning strategy (natural language vs. code). Its headline finding is that **retrieval precision is the dominant driver of answer correctness** on realistic FHIR questions. **Why it matters:** This is concurrent and complementary work that empirically validates the thesis of our paper — that retrieval primitives, not generation, separate good from bad FHIR QA systems. It differs in that it is a benchmark and agent-architecture study over real MIMIC-IV-FHIR rather than a controlled ablation of a specific retrieval primitive, does not isolate typed filtering + reference traversal + temporal pre-filter as a distinct condition, and does not focus on specialty medication or regimen-aware question classes. **Cite for:** the only contemporaneous peer-reviewed-adjacent evidence that retrieval design dominates on FHIR, positioning our paper as a controlled ablation of the specific retrieval primitives FHIR-AgentBench leaves under-investigated.

## Gap analysis

The literature we surveyed leaves a narrow but well-defined gap that our paper occupies. First, **FHIR-specific retrieval primitives are essentially absent from the peer-reviewed record**: FHIR-AgentBench (Lee et al. 2025) evaluates agents over FHIR but does not propose or ablate a typed-filter-plus-reference-traversal-plus-temporal-prefilter module as a first-class retrieval component; Schmiedmayer et al.'s *LLM on FHIR* (arXiv:2402.01711, 2024) uses function-calling to fetch one resource type at a time without reference-chain traversal, typed pre-filters, or temporal scoping; and most recent "FHIR + LLM" work targets **generating** FHIR from text rather than **retrieving** over existing FHIR for QA. Second, structured-EHR QA benchmarks (EHRSQL, MIMICSQL, emrKBQA, EHRAgent) operate on flattened MIMIC-III/eICU/MIMIC-IV relational schemas that erase FHIR's defining features — polymorphic `Reference` fields, code-system bindings, and the typed resource topology — so their retrieval semantics cannot be transferred. Third, schema-aware structured reasoning (StructGPT, graph-prompting variants) is evaluated on generic KGs and tables rather than clinical resource graphs. Fourth, graph-RAG systems (GraphRAG, LightRAG, HippoRAG, MedGraphRAG) infer their graphs with an LLM at ingestion time, whereas FHIR already **is** a schema-typed graph in production EHRs; the closest philosophical match, Soman et al.'s SPOKE-based KG-RAG (Bioinformatics 2024), traverses a pre-built biomedical KG but encodes population-level drug–gene–disease knowledge rather than patient-level clinical state. Finally, **temporal pre-filtering as an explicit retrieval primitive** — windowing the resource graph by encounter or medication dates before retrieval — is not isolated or ablated in any work we found, despite temporal reasoning being the most-cited failure mode on both EHRSQL and FHIR-AgentBench. The intersection of these axes, evaluated on specialty-medication regimen and temporal questions with programmatically verifiable ground truth, is the narrow slice this paper claims.

## BibTeX

```bibtex
@article{robertson2009probabilistic,
  title={The Probabilistic Relevance Framework: {BM25} and Beyond},
  author={Robertson, Stephen and Zaragoza, Hugo},
  journal={Foundations and Trends in Information Retrieval},
  volume={3},
  number={4},
  pages={333--389},
  year={2009},
  publisher={Now Publishers},
  doi={10.1561/1500000019}
}

@inproceedings{karpukhin2020dpr,
  title     = {Dense Passage Retrieval for Open-Domain Question Answering},
  author    = {Karpukhin, Vladimir and Oguz, Barlas and Min, Sewon and Lewis, Patrick and Wu, Ledell and Edunov, Sergey and Chen, Danqi and Yih, Wen-tau},
  booktitle = {Proceedings of the 2020 Conference on Empirical Methods in Natural Language Processing (EMNLP)},
  pages     = {6769--6781},
  year      = {2020},
  publisher = {Association for Computational Linguistics},
  url       = {https://aclanthology.org/2020.emnlp-main.550/},
  doi       = {10.18653/v1/2020.emnlp-main.550}
}

@article{jin2023medcpt,
  title={{MedCPT}: Contrastive Pre-trained Transformers with large-scale {PubMed} search logs for zero-shot biomedical information retrieval},
  author={Jin, Qiao and Kim, Won and Chen, Qingyu and Comeau, Donald C and Yeganova, Lana and Wilbur, W John and Lu, Zhiyong},
  journal={Bioinformatics},
  volume={39},
  number={11},
  pages={btad651},
  year={2023},
  publisher={Oxford University Press},
  doi={10.1093/bioinformatics/btad651}
}

@article{edge2024graphrag,
  title={From Local to Global: A Graph {RAG} Approach to Query-Focused Summarization},
  author={Edge, Darren and Trinh, Ha and Cheng, Newman and Bradley, Joshua and Chao, Alex and Mody, Apurva and Truitt, Steven and Metropolitansky, Dasha and Ness, Robert Osazuwa and Larson, Jonathan},
  journal={arXiv preprint arXiv:2404.16130},
  year={2024},
  url={https://arxiv.org/abs/2404.16130}
}

@inproceedings{gutierrez2024hipporag,
  title     = {Hippo{RAG}: Neurobiologically Inspired Long-Term Memory for Large Language Models},
  author    = {Guti{\'e}rrez, Bernal Jim{\'e}nez and Shu, Yiheng and Gu, Yu and Yasunaga, Michihiro and Su, Yu},
  booktitle = {Advances in Neural Information Processing Systems (NeurIPS)},
  year      = {2024},
  eprint    = {2405.14831},
  archivePrefix = {arXiv},
  url       = {https://arxiv.org/abs/2405.14831}
}

@article{wu2024medgraphrag,
  title={Medical Graph {RAG}: Towards Safe Medical Large Language Model via Graph Retrieval-Augmented Generation},
  author={Wu, Junde and Zhu, Jiayuan and Qi, Yunli and Chen, Jingkun and Xu, Min and Menolascina, Filippo and Grau, Vicente},
  journal={arXiv preprint arXiv:2408.04187},
  year={2024},
  note={Accepted at ACL 2025},
  url={https://arxiv.org/abs/2408.04187}
}

@inproceedings{jiang2023structgpt,
  title     = {{StructGPT}: A General Framework for Large Language Model to Reason over Structured Data},
  author    = {Jiang, Jinhao and Zhou, Kun and Dong, Zican and Ye, Keming and Zhao, Wayne Xin and Wen, Ji-Rong},
  booktitle = {Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing (EMNLP)},
  pages     = {9237--9251},
  year      = {2023},
  publisher = {Association for Computational Linguistics},
  address   = {Singapore},
  eprint    = {2305.09645},
  archivePrefix = {arXiv},
  url       = {https://aclanthology.org/2023.emnlp-main.574/}
}

@article{lee2025fhiragentbench,
  title   = {{FHIR-AgentBench}: Benchmarking {LLM} Agents for Realistic Interoperable {EHR} Question Answering},
  author  = {Lee, Gyubok and Bach, Elea and Yang, Eric and Pollard, Tom and Johnson, Alistair and Choi, Edward and Jia, Yugang and Lee, Jong Ha},
  journal = {arXiv preprint arXiv:2509.19319},
  year    = {2025},
  note    = {Presented at Machine Learning for Healthcare (ML4H) 2025},
  url     = {https://arxiv.org/abs/2509.19319}
}
```