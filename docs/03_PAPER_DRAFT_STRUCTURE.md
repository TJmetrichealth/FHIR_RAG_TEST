# Paper Draft Structure

**Working title:** *Paired-Data Comparison of Structured FHIR and LLM-Narrative Retrieval for Adherence-Indicator Question Answering on Long-Acting Specialty Regimens*

**Target length:** 8 pages main + references + appendix (workshop-style for arXiv; expandable for full venue)

**Target format:** Single column, standard preprint; LaTeX source in `paper/main.tex`.

**v3 update:** Question framing is now the five PSP adherence indicator families (PDC, MPR, persistence, missed-dose detection, next-dose lookup). A new Results subsection (§7.8) covers the feature-extraction arm. The preprint itself does not invoke metricHEALTH beyond affiliation; the Phase-0 framing lives in the parallel thesis-chapter scaffold only (`thesis_chapter/phase_0.md`).

---

## Core message (one paragraph — preprint framing)

When the same clinical facts are expressed in structured FHIR and in LLM-generated clinical narrative, RAG over the structured representation answers adherence-indicator questions about long-acting specialty medications more accurately than RAG over the narrative — and the gap widens with regimen complexity. Features extracted from the structured representation are also more predictive of adherence outcomes than features extracted from the same narratives. This is the first paired-data comparison in this setting, where information content is held constant across representations. A resource-aware retriever that exploits FHIR's typed structure and references extends the gap further.

Every sentence of the paper should serve this core message. If it doesn't, cut it.

## Parallel thesis-chapter framing (Phase 0)

The same experiments, written for the metricHEALTH thesis, frame the work as *"Phase 0: benchmarking representation choices before committing to the ML engine design."* The thesis chapter makes three metricHEALTH-specific claims the preprint does not: the validator stress-test as Phase 1 evidence, the case-manager Q&A endpoint as Phase 4 prototype, and the feature-extraction finding as Phase 3 design justification. See `thesis_chapter/phase_0.md`.

---

## Section plan (preprint)

### 1. Abstract (~200 words)

Standard structure:
- **Context** — LLMs increasingly author clinical documentation; structured standards like FHIR are also growing; unclear which representation is better for retrieval-augmented QA over adherence-critical specialty regimens.
- **Gap** — prior comparisons confound representation with information content and data source.
- **Approach** — paired synthetic dataset where 200 patients are expressed in both FHIR bundles and LLM-generated narratives with verified fidelity; three retrieval systems; programmatic ground truth over 120 adherence-indicator questions across three regimen complexity tiers; feature-extraction arm compares structured-derived, narrative-derived, and resource-aware-derived features on a synthetic adherence classification task.
- **Findings** — structured-FHIR RAG outperforms narrative RAG on QA; gap scales with complexity; resource-aware retrieval extends the gap further; structured-derived features match or exceed narrative-derived features on adherence prediction AUC.
- **Contribution** — paired-data methodology, FHIR-native retrieval baseline, specialty-pharmacy adherence-indicator domain, complexity-stratified result, feature-extraction comparison.

The abstract does not mention metricHEALTH (R16 mitigation).

### 2. Introduction (~1 page)

- Motivate: specialty pharmacy is growing, long-acting regimens are clinically demanding and adherence-critical, PSPs worldwide rely on adherence indicators (PDC, MPR, persistence). [Block 6 citations]
- Motivate: LLMs increasingly generate clinical notes (ambient scribes etc.); these narratives replace structured data in some workflows. [Block 7]
- Question: when the same facts are available in both forms, which should RAG systems retrieve from? And which should ML adherence models consume as features?
- Prior work confounds representation (narrative vs. structured) with dataset (MIMIC vs. proprietary). [Block 2]
- Contributions (numbered):
  1. First paired-data evaluation holding information content constant
  2. FHIR-native retrieval baseline (structured RAG)
  3. Resource-aware retriever exploiting FHIR typed references and temporal structure
  4. PSP adherence-indicator question grounding (5 families: PDC, MPR, persistence, missed-dose detection, next-dose lookup)
  5. Specialty-pharmacy domain with long-acting regimens at three complexity tiers
  6. Feature-extraction comparison on a synthetic adherence prediction task
- Open everything: code + dataset released.

### 3. Related Work (~1 page)

Five sub-paragraphs, aligned with the literature blocks:
- **Clinical RAG** — MedRAG, MIRAGE, etc. [Block 1]
- **Structured vs. unstructured EHR** — prior claims and their confounds [Block 2]
- **FHIR + ML / LLM** — FHIR-Former, KETOS, SQL on FHIR [Block 3]
- **Clinical temporal reasoning** — known hard for LLMs over narrative [Block 4]
- **Adherence metrics and adherence ML** — canonical PDC/MPR/persistence definitions and the adherence-prediction ML lineage [Blocks 6, 11]

End the section with: "To our knowledge, no prior work evaluates structured-FHIR vs. LLM-narrative RAG on paired data for adherence-indicator questions, nor compares these representations as feature sources for adherence classification." Back this claim up in Section 9 limitations if a reviewer pushes.

### 4. Dataset (~1.5 pages)

- **4.1 Base population** — 200 Synthea-generated patients, deterministic seed.
- **4.2 Specialty regimen overlay** — custom generator assigning one of three complexity tiers:
  - T1: single long-acting injectable on fixed schedule
  - T2: cyclic (on-for-N, off-for-M) with cycle position
  - T3: multi-drug (biologic + oral adjunct + PRN) with staggered schedules
  - *Include a figure showing a timeline for one patient at each tier.*
- **4.3 R4B conformance** — all 200 bundles validate against a reference pre-write R4B validator; per-tier conformance rates reported.
- **4.4 Narrative generation** — fixed LLM (Llama 3.3 70B), fixed prompt, fixed temperature; auditable.
- **4.5 Fidelity audit** — programmatic recovery rate of medications, dose events, and critical dates. Final fidelity distribution plotted.
- **4.6 Templated narratives (ablation)** — deterministic template rendering as a "maximum fidelity" narrative ceiling.
- **4.7 Question bank — five PSP adherence indicator families** (24 each × 5 = 120 total):
  - Next-dose lookup (schedule adherence)
  - Dose-history aggregation (MPR numerator)
  - Coverage-window reasoning (PDC)
  - Missed-dose detection (gap detection)
  - Persistence / discontinuation signal (persistence)
  - Programmatic ground truth (pure-Python functions over FHIR bundle)
  - 2 paraphrases per question, verified to preserve answer
  - The adherence metric functions (PDC, MPR, persistence) are shared code between the ground-truth generator and the feature-extraction arm — they are unit-tested against known-case fixtures.

### 5. Systems (~0.75 page)

- **5.1 Narrative RAG (A)** — chunk, embed, top-k, answer LLM (Qwen 3 32B).
- **5.2 Structured RAG, naive (B)** — serialise each FHIR resource to text, embed, top-k, same answer LLM.
- **5.3 Structured RAG, resource-aware (C)** — typed filtering + reference traversal + temporal pre-filter + semantic search.
- *Include a small diagram showing the three retrieval paths side-by-side.*
- **5.4 Controlled variables** — explicit table listing what's held constant across A, B, C (k=5, chunk=500 tokens, BGE-large-v1.5 embeddings, Qwen 3 32B answer LLM at T=0).

### 6. Evaluation (~0.75 page)

- Accuracy (programmatic exact match, set equality, tolerance bands for numeric proportion answers like PDC and MPR)
- Retrieval recall@k — decoupled from answer quality
- Latency + token count per call
- Stratification by complexity tier and question family
- Statistical testing — paired bootstrap CIs, McNemar
- Explicit statement: **no LLM-as-judge.**
- **Feature-extraction arm protocol**: same 200-patient split across feature sets; three feature sets (FS-Structured, FS-Narrative, FS-Aware); LightGBM and logistic regression classifiers; AUC-ROC with paired bootstrap CIs.

### 7. Results (~1.75 pages)

- **7.1 Main results table** — accuracy by system, overall. *The paper's headline number lives here.*
- **7.2 Complexity gradient** — the core plot: accuracy by system × tier. If the gap widens, this is the figure people will share.
- **7.3 By adherence indicator family** — which PSP question families benefit most from structure?
- **7.4 Retrieval recall vs. answer accuracy** — decompose failure: is it retrieval's fault or generation's?
- **7.5 Cost / latency** — practical trade-offs.
- **7.6 Error taxonomy** — 3–4 categories of temporal / adherence-reasoning failure with representative examples.
- **7.7 Ablation: templated narratives** — how much of the gap is LLM-narrative weakness vs. intrinsic representation?
- **7.8 Feature-extraction arm** — AUC-ROC for FS-Structured vs. FS-Narrative vs. FS-Aware on the synthetic adherence task. Paired bootstrap CIs. *New for v3.*

### 8. Discussion (~0.75 page)

- What the paired-data result means: structure wins on adherence-indicator questions, even against high-quality narratives.
- Why: typed access, temporal grounding in schema, resource references preserve relational structure.
- Where narrative might still win (interpretive / qualitative questions, patient-reported symptom context) — an honest caveat.
- Practical implication: LLM-generated clinical notes should be treated as *summaries*, not as drop-in replacements for the structured record, for downstream adherence-indicator retrieval or adherence-outcome prediction.
- Implication for system designers building RAG over clinical data: if adherence indicators are in the question distribution, budget for structured-representation retrieval — a naive serialise-to-text approach leaves measurable accuracy on the table.

### 9. Limitations (~0.3 page)

- Synthetic data — no claims about real clinical-text variation; the adherence labels are themselves synthetic.
- Single narrative-LLM and single answer-LLM — generalisation across models not tested; mitigated by templated-narrative ablation.
- Three tiers don't cover all real-world complexity.
- Programmatic ground truth means some clinically-meaningful but less-determinate questions are out of scope.
- Specialty-medication adherence domain may not generalise to primary care or acute-care QA.
- Feature-extraction arm uses a single synthetic outcome label; real discontinuation dynamics are richer and noisier.

Pick up any risk from the risk register that materialised (R1–R17).

### 10. Conclusion (~0.2 page)

One paragraph. Restate the core message; point to code + dataset; flag follow-up direction (real de-identified data, larger question families, multi-LLM, richer outcome labels).

### References

Built from `docs/literature/bibliography.bib`. ~45–65 entries.

### Appendix

- A.1 Prompt templates (narrative generation, answer generation, narrative feature extraction)
- A.2 Question bank (full list, in supplementary)
- A.3 Adherence metric function specifications (PDC, MPR, persistence)
- A.4 Fidelity audit methodology
- A.5 Feature-extraction arm hyperparameters
- A.6 Hyperparameter sweeps (if run)
- A.7 Reproducibility instructions
- A.8 R4B conformance per-tier breakdown

---

## Figures plan (7–8 total)

1. **System diagram** — the three retrieval paths
2. **Regimen complexity examples** — one timeline per tier
3. **Fidelity distribution** — histogram of narrative fidelity scores
4. **Main results** — bar chart, accuracy per system, overall
5. **Complexity gradient** — line or grouped bar: accuracy × system × tier (the money plot)
6. **Retrieval vs. answer** — decomposition plot (recall@k vs. answer accuracy)
7. **Error taxonomy** — stacked bar per system showing error category distribution
8. **Feature-extraction AUC** — grouped bar: AUC × feature-set × classifier with error bars *(new for v3)*

Optional if space:
- Latency / cost table
- By-adherence-indicator results

---

## Writing principles

1. **State the contribution precisely.** "First paired-data comparison on PSP-adherence-indicator questions over FHIR vs. LLM-narrative, extended to feature-extraction for adherence prediction" — each qualifier earns its place.
2. **Numbers come from source files.** Never retype; `\input` from generated tables where possible.
3. **Calibrate claims.** "outperforms" + CI + test is fine; "significantly outperforms" without a test is not; "dramatically outperforms" is almost never fine.
4. **The limitations section is a strength, not a weakness.** Reviewers respect authors who beat them to the critique.
5. **Every figure has a self-contained caption.** A reader should understand the figure without reading the body.
6. **No "as shown in Figure X" without saying what the figure shows.** The sentence should carry the finding; the figure is evidence.
7. **The preprint does not reference metricHEALTH beyond affiliation.** The thesis-chapter scaffold makes the Phase 0 case; the preprint is tightly scoped to the paired-data methodology.

---

## Review pass checklist (before arXiv)

- [ ] Every number in the text matches a row in `results/*.csv` or `results/feature_extraction/*.csv`
- [ ] Every citation in the text exists in `bibliography.bib`
- [ ] Every citation in `bibliography.bib` is actually used
- [ ] Abstract reproduces the core message in ~200 words
- [ ] Abstract does NOT reference metricHEALTH (R16 mitigation)
- [ ] Introduction contributions list matches the results section
- [ ] The five adherence-indicator families appear consistently throughout (Intro, §4.7, §7.3, Discussion)
- [ ] PDC and MPR are cited to distinct source papers (not conflated)
- [ ] Figures are colorblind-safe and readable at print size
- [ ] Limitations names at least one materialised risk from the R1–R17 register
- [ ] Reproducibility section points to the one-command repro
- [ ] Licence statement on dataset release
- [ ] Thesis-chapter scaffold in `thesis_chapter/phase_0.md` exists and is consistent with the preprint numbers
