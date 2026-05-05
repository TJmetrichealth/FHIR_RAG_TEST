# Literature wiki — index

Catalog of topic pages. Conventions in [`_WIKI_SCHEMA.md`](_WIKI_SCHEMA.md). Chronological history in [`log.md`](log.md). Queries that seeded these pages in [`../02_LITERATURE_REVIEW_QUERIES.md`](../02_LITERATURE_REVIEW_QUERIES.md).

## Topic pages

| Block | Page | Scope (one line) |
|-------|------|------------------|
| 1 | [clinical_rag](clinical_rag.md) | Clinical/medical RAG prior art; closest methodological predecessors to paired narrative-vs-structured EHR RAG |
| 2 | [structured_vs_unstructured](structured_vs_unstructured.md) | Structured vs. unstructured EHR for NLP/QA; paired same-patient views; novelty defence for held-constant information content |
| 3 | [fhir_ml](fhir_ml.md) | FHIR + ML / LLM — prior use of FHIR as substrate for learning and retrieval systems |
| 5 | [synthea](synthea.md) | Synthea as synthetic-EHR substrate; medication-module gap; learned alternatives; justifies the specialty-medication overlay |
| 6 | [psp_adherence_indicators](psp_adherence_indicators.md) | Specialty pharmacy, biologics, LAIs and cyclic regimens — clinical context and why this drug class is NLP-under-studied |
| 7 | [llm_clinical_documentation](llm_clinical_documentation.md) | LLM-generated clinical documentation; narrative fidelity and hallucination prior art |
| 8 | [retrieval_strategies](retrieval_strategies.md) | Retrieval lineage for the resource-aware FHIR retriever — hybrid, graph-augmented, schema-aware |
| 9 | [rag_evaluation](rag_evaluation.md) | RAG evaluation methodology — metrics, ground-truth design, paired comparisons |
| 10 | [canadian_psp](canadian_psp.md) | Canadian patient support programmes and specialty pharmacy — citation verification |
| 11 | [block 11 adherance](block%2011%20adherance.md) | Feature engineering for adherence ML — prior art for PSP adherence indicators |
| cross | [clinical_temporal](clinical_temporal.md) | Clinical LLM temporal reasoning and the FHIR-RAG novelty window — cross-cutting threat analysis |

## Supporting files

- [`bibliography.bib`](bibliography.bib) — BibTeX entries for every cited paper
- [`_WIKI_SCHEMA.md`](_WIKI_SCHEMA.md) — conventions, ingest/query/lint protocols
- [`log.md`](log.md) — append-only chronological record

## Notes

- Block 4 is intentionally absent from this index — no dedicated topic page was created; its queries were absorbed into `fhir_ml.md` and `retrieval_strategies.md`. If Block 4 is later reopened, add its row here.
- The `clinical_temporal` page is a **cross-cutting** threat-landscape summary, not a numbered block. It references papers that also live on the numbered pages; do not duplicate detailed entries across both.
