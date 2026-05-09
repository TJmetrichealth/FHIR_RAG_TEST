# arXiv Submission Package

**Title:** Representation Wins on QA, Not on ML: A Paired-Data Comparison of Structured FHIR and LLM-Narrative Retrieval for Adherence-Indicator Question Answering on Long-Acting Specialty Regimens

**Author:** Tirthesh Jani

**Submission category:** cs.CL (primary), cs.IR, cs.LG (cross-list candidates)

## Files

```
arxiv_submission/
├── 00README.XXX            arXiv build hints (toplevelfile, engine)
├── main.tex                Document root
├── main.bbl                Pre-compiled bibliography (arXiv-friendly)
├── main.pdf                Reference compiled output (22 pages)
├── refs.bib                BibTeX source (kept for reproducibility)
├── sections/
│   ├── 00_abstract.tex
│   ├── 01_introduction.tex
│   ├── 02_related_work.tex
│   ├── 03_methods.tex
│   ├── 04_results.tex
│   ├── 05_discussion.tex
│   ├── 06_limitations.tex
│   ├── 07_reproducibility.tex
│   └── 08_conclusion.tex
└── figures/
    ├── accuracy_by_tier.png
    ├── accuracy_heatmap.png
    ├── error_rate_by_complexity.png   (kept; not currently referenced)
    ├── error_taxonomy_distribution.png
    ├── feature_arm_auc.png
    ├── partial_vs_exact.png
    └── recall_at_k_curve.png
```

## Build

Local reproduction:

```bash
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

arXiv runs the same sequence automatically. The `main.bbl` is included so a successful arXiv build does not require BibTeX to re-run.

## Figures referenced in the paper

| Section | Figure | File |
|---|---|---|
| 4.1 Overall accuracy | Fig. partial-vs-exact | `figures/partial_vs_exact.png` |
| 4.3 By question family | Fig. accuracy heatmap | `figures/accuracy_heatmap.png` |
| 4.4 Retrieval recall | Fig. recall@k curves | `figures/recall_at_k_curve.png` |
| 4.7 Feature arm | Fig. feature-arm AUC | `figures/feature_arm_auc.png` |
| 4.7 Feature arm | Fig. accuracy by tier | `figures/accuracy_by_tier.png` |
| 4.7 Feature arm | Fig. error taxonomy | `figures/error_taxonomy_distribution.png` |

`error_rate_by_complexity.png` is included in the source tree but not referenced; it is kept for reproducibility against the analysis scripts.

## License

- Code: Apache-2.0
- Manuscript / figures / dataset: CC-BY-4.0 (pending employer IP clearance)
