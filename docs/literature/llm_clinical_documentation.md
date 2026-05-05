# Block 7: LLM-Generated Clinical Documentation — Literature Review

*File: `docs/literature/llm_clinical_documentation.md`*
*Compiled: April 2026 · Target venue: arXiv preprint (submission target 2026-05-31)*
*Scope: ~8 papers grounding deployment urgency, fidelity failure modes, and evaluation methodology for LLM-generated clinical narratives — the baseline condition against which structured FHIR RAG is compared.*

---

## 1. Tierney et al. 2024 — First large-scale ambient AI scribe deployment (Kaiser Permanente / TPMG)

**Citation:** Tierney AA, Gayre G, Hoberman B, Mattern B, Ballesca M, Kipnis P, Liu V, Lee K. Ambient Artificial Intelligence Scribes to Alleviate the Burden of Clinical Documentation. *NEJM Catalyst Innovations in Care Delivery*. 2024;5(3). doi:10.1056/CAT.23.0404. URL: https://catalyst.nejm.org/doi/full/10.1056/CAT.23.0404

**Addresses:** Deployment

**Summary:** This is the landmark early-deployment report describing how The Permanente Medical Group (TPMG) enabled an LLM-powered ambient AI scribe for **10,000 physicians and staff** across Northern California beginning October 2023. In the first 10 weeks alone, **3,442 physicians used the tool in up to 303,266 patient encounters** across diverse specialties, with one physician using it in 1,210 encounters. The authors report favorable physician feedback, positive early patient surveys, high-quality LLM-generated draft notes, and statistically significant reductions in documentation and EHR time. This is the most-cited primary evidence that LLM-based ambient documentation has moved from prototype to enterprise scale, and it is the clearest single citation for the claim that LLM-generated clinical documentation is already routine practice at a major integrated delivery system.

---

## 2. Shah et al. 2025 — Stanford DAX Copilot pilot with burnout outcomes

**Citation:** Shah SJ, Devon-Sand A, Ma SP, Jeong Y, Crowell T, Smith M, Liang AS, Delahaie C, Hsia C, Shanafelt T, Pfeffer MA, Sharp C, Lin S, Garcia P. Ambient artificial intelligence scribes: physician burnout and perspectives on usability and documentation burden. *Journal of the American Medical Informatics Association*. 2025;32(2):375–380. doi:10.1093/jamia/ocae295. URL: https://doi.org/10.1093/jamia/ocae295

**Addresses:** Deployment

**Summary:** A prospective quality-improvement study reporting Stanford Health Care's Epic-integrated pilot of **Microsoft Nuance DAX Copilot** across 48 physicians in multiple specialties over three months. Paired survey analysis (n=38) showed large, statistically significant reductions in task load (−24.42) and burnout (−1.94), with improved System Usability Scale scores (+10.9) (all p < .001). A companion paper (Ma et al. JAMIA 2025, doi:10.1093/jamia/ocae304) quantifies **55.25% encounter utilization (9,629/17,428)** and ≈20-min/day median reductions in EHR time. Together these provide a named-product (DAX Copilot) deployment citation at a flagship academic medical center, establishing that ambient LLM scribes are not confined to integrated delivery systems like Kaiser.

---

## 3. Rotenstein et al. 2026 — Multi-site JAMA evaluation of AI scribes at scale

**Citation:** Rotenstein L, Holmgren AJ, Thombley R, Sriram A, Dbouk RH, Jost M, et al. Changes in Clinician Time Expenditure and Visit Quantity With Adoption of Artificial Intelligence–Powered Scribes: A Multisite Study. *JAMA*. 2026. doi:10.1001/jama.2026.2253. URL: https://jamanetwork.com/journals/jama/fullarticle/10.1001/jama.2026.2253

**Addresses:** Deployment

**Summary:** The most recent and largest multi-site real-world evaluation, covering **8,581 ambulatory clinicians (1,809 adopters vs. 6,771 non-adopters) across five U.S. academic health systems** — Mass General Brigham, UCSF Health, Yale, UCSD, and NYU Langone — between June 2023 and August 2025. The evaluated products span **Abridge, Microsoft/Nuance DAX Copilot, and Ambience Healthcare**, all Epic-integrated. AI scribe adoption was associated with a **13.4-min reduction in total daily EHR time, 16.0-min reduction in documentation time, and 0.49 additional visits/week per clinician**. This paper is the definitive recent citation that multiple LLM-scribe vendors are in simultaneous enterprise production across top U.S. academic centers, closing any remaining argument that LLM clinical documentation is hypothetical or vendor-specific.

---

## 4. Williams et al. 2025 — GPT-4 ED encounter summary error audit

**Citation:** Williams CYK, Bains J, Tang T, Patel K, Lucas AN, Chen F, Miao BY, Butte AJ, Kornblith AE. Evaluating large language models for drafting emergency department encounter summaries. *PLOS Digital Health*. 2025;4(6):e0000899. doi:10.1371/journal.pdig.0000899. URL: https://doi.org/10.1371/journal.pdig.0000899

**Addresses:** Fidelity problems

**Summary:** A UCSF cross-sectional study in which two emergency-medicine physicians rated GPT-4 and GPT-3.5-turbo encounter summaries for 100 randomly sampled ED clinician notes across three fidelity axes: inaccuracy, hallucination, and omission. **Only 33% of GPT-4 summaries and 10% of GPT-3.5-turbo summaries were error-free**; GPT-4 summaries contained **inaccuracies in 10%, hallucinations in 42%, and omissions in 47%**. Hallucinations concentrated in the Plan section (fabricated follow-up referrals, invented return precautions; one case substituted a fabricated stroke diagnosis for a true migraine, rated harm 6/7); omissions clustered in Physical Exam and History of Presenting Complaint. This is the cleanest recent empirical demonstration that free-text LLM generation from clinical source material produces clinically meaningful fabrications and omissions at high rates — precisely the failure mode structured FHIR retrieval is designed to avoid.

---

## 5. Asgari et al. 2025 — CREOLA sentence-level hallucination audit (largest to date)

**Citation:** Asgari E, Montaña-Brown N, Dubois M, Khalil S, Balloch J, Au Yeung J, Pimenta D. A framework to assess clinical safety and hallucination rates of LLMs for medical text summarisation. *npj Digital Medicine*. 2025;8(1):274. doi:10.1038/s41746-025-01670-7. URL: https://doi.org/10.1038/s41746-025-01670-7

**Addresses:** Fidelity problems

**Summary:** The Tortus AI group built CREOLA, a clinician-annotation platform, and had 50 physicians evaluate sentence-by-sentence every GPT-4 generated consultation note against its source transcript across 18 experimental configurations — **450 note pairs, 49,590 transcript sentences, 12,999 generated sentences**, described as the largest manual evaluation of LLM clinical note generation to date. They measured a **1.47% sentence-level hallucination rate (44% "major" — capable of altering diagnosis or management) and a 3.45% omission rate (17% major)**. Hallucinations were taxonomized as fabricated (43%), negation flips (30% — asserting a symptom is absent when the transcript says it is present), contextual (17%), and causal (10%), and clustered in Plan (21%) and Assessment (10.5%) sections. Critically, these residuals persisted after iterative prompt engineering, substantiating that narrative-fidelity failures are intrinsic to free-text LLM generation — not a prompt-tuning artifact.

---

## 6. Moramarco et al. 2022 — Error taxonomy and automatic-metric validation (ACL)

**Citation:** Moramarco F, Papadopoulos Korfiatis A, Perera M, Juric D, Flann J, Reiter E, Belz A, Savkov A. Human Evaluation and Correlation with Automatic Metrics in Consultation Note Generation. In: *Proceedings of the 60th Annual Meeting of the Association for Computational Linguistics (ACL 2022)*, Vol. 1: Long Papers, pp. 5739–5754. doi:10.18653/v1/2022.acl-long.394. URL: https://aclanthology.org/2022.acl-long.394/

**Addresses:** Fidelity problems **and** evaluation methodology (dual)

**Summary:** The canonical prior-art paper on evaluating generated clinical notes. Five clinicians listened to 57 mock primary-care consultations (the PriMock57 corpus), wrote reference notes, post-edited automatically generated SOAP notes, and extracted every error, producing a **fine-grained taxonomy of incorrect statements, omissions, unnecessary additions/hallucinations, incorrect patient-attribute attribution, and temporal errors** — precisely the error classes this project targets. The authors then correlated 18 automatic metrics against the clinician-derived error counts and showed that **character-level edit distance and SNOMED entity-level F1 track clinician judgment on par with or better than BERTScore, while ROUGE and BLEU correlate weakly**. This is the single most useful citation for justifying both the error taxonomy and the choice of entity-level precision/recall as an automated fidelity proxy.

---

## 7. Croxford et al. 2025 — PDSQI-9, the PDQI-9 successor validated for LLMs

**Citation:** Croxford E, Gao Y, Pellegrino N, Wong KK, Wills G, First E, et al. Development and Validation of the Provider Documentation Summarization Quality Instrument for Large Language Models (PDSQI-9). *arXiv:2501.08977*; also *JAMIA* 2025 (PMID 40323321). URL: https://arxiv.org/abs/2501.08977

**Addresses:** Evaluation methodology

**Summary:** The direct LLM-era successor to Stetson/Kahn's PDQI-9, reworked as a **9-item Likert rubric** (accuracy, organization, succinctness, clarity, utility, and four others) and psychometrically validated on **779 summaries generated by GPT-4o, Mixtral 8×7B, and Llama 3-8B**, rated by 7 physicians answering 8,329 questions. Reliability statistics are strong: Cronbach's α = 0.879, ICC = 0.867, Krippendorff's α = 0.575, with 4-factor structure explaining 58% of variance and discriminant validity p < .001. This is the strongest modern validated instrument for clinician spot-review of LLM-generated narratives; its "accuracy" subscale gives a defensible anchor for a fidelity gate, and its lineage to the broadly accepted PDQI-9 makes it the path-of-least-resistance rubric for a reviewer-facing audit protocol.

---

## 8. Chung et al. 2025 — VeriFact: LLM-as-judge with RAG for clinical fact-checking

**Citation:** Chung P, Swaminathan A, Goodell AJ, Kim Y, Reincke SM, Han L, et al. VeriFact: Verifying Facts in LLM-Generated Clinical Text with Electronic Health Records. *arXiv:2501.16672*; also *NEJM AI*, doi:10.1056/AIdbp2500418. URL: https://arxiv.org/abs/2501.16672

**Addresses:** Evaluation methodology

**Summary:** VeriFact is an automated fidelity checker that **decomposes LLM-generated clinical narratives into atomic claim or sentence propositions using Llama 3.1-70B**, retrieves supporting evidence from a per-patient EHR vector store (BGE-M3 hybrid dense+sparse with reranking, top-50), and has an LLM-as-judge label each proposition as *Supported*, *Not Supported*, or *Not Addressed*. The authors released **VeriFact-BHC**, 13,290 propositions from MIMIC-III Brief Hospital Course narratives each labeled by 3 of 25 clinicians (1,618 clinician-hours). VeriFact achieved **up to 92.7% agreement with denoised clinician ground truth**, exceeding average inter-clinician agreement (88.5% on atomic claims), with Gwet's AC1 up to 0.88. This is the most directly applicable template for a >90% fidelity gate on LLM narratives generated over FHIR bundles: the atomic-claim Subject–Predicate–Object decomposition maps cleanly onto structured FHIR content, and its 92.7% headline number empirically justifies a >90% threshold as both attainable and meaningful.

---

## Synthesis: state of the field and where our work fits

The literature establishes three uncontested findings. **First, LLM-generated clinical documentation is not hypothetical** — as of 2026, ambient AI scribes from Abridge, Nuance DAX Copilot, and Ambience Healthcare are in simultaneous enterprise use across Kaiser Permanente, Stanford, Mass General Brigham, UCSF, and peer institutions, with documented use in millions of encounters (Tierney 2024/2025, Shah 2025, Rotenstein 2026). **Second, free-text LLM generation from clinical source material produces clinically meaningful fabrications and omissions at non-trivial rates**: 42% of GPT-4 ED summaries contained hallucinations in one UCSF study (Williams 2025), and sentence-level audit of 12,999 generated sentences found residual major hallucinations even after prompt tuning (Asgari 2025), with Moramarco et al.'s (2022) error taxonomy remaining the canonical reference. **Third, evaluation methodology has recently matured**: PDSQI-9 (Croxford 2025) provides a psychometrically validated clinician rubric, and VeriFact (Chung 2025) demonstrates that LLM-as-judge over patient-specific retrieved evidence can reach 92.7% clinician agreement. The gap our work targets is narrow and specific: none of these studies compare **structured FHIR retrieval** against **LLM-generated narrative retrieval** as alternative RAG substrates for **temporally-grounded specialty medication QA**. Our fidelity gate directly inherits entity-level and atomic-claim methodologies from Moramarco, Chung, and Croxford, rather than reinventing them.

---

## Consolidated BibTeX

```bibtex
@article{tierney2024ambient,
  title   = {Ambient Artificial Intelligence Scribes to Alleviate the Burden of Clinical Documentation},
  author  = {Tierney, Aaron A. and Gayre, Gregg and Hoberman, Brian and Mattern, Britt and Ballesca, Manuel and Kipnis, Patricia and Liu, Vincent and Lee, Kristine},
  journal = {NEJM Catalyst Innovations in Care Delivery},
  volume  = {5},
  number  = {3},
  year    = {2024},
  doi     = {10.1056/CAT.23.0404},
  url     = {https://catalyst.nejm.org/doi/full/10.1056/CAT.23.0404}
}

@article{shah2025ambient,
  title   = {Ambient artificial intelligence scribes: physician burnout and perspectives on usability and documentation burden},
  author  = {Shah, Shreya J. and Devon-Sand, Anna and Ma, Stephen P. and Jeong, Yejin and Crowell, Trevor and Smith, Margaret and Liang, April S. and Delahaie, Clarissa and Hsia, Caroline and Shanafelt, Tait and Pfeffer, Michael A. and Sharp, Christopher and Lin, Steven and Garcia, Patricia},
  journal = {Journal of the American Medical Informatics Association},
  volume  = {32},
  number  = {2},
  pages   = {375--380},
  year    = {2025},
  doi     = {10.1093/jamia/ocae295},
  url     = {https://doi.org/10.1093/jamia/ocae295}
}

@article{rotenstein2026changes,
  title   = {Changes in Clinician Time Expenditure and Visit Quantity With Adoption of Artificial Intelligence--Powered Scribes: A Multisite Study},
  author  = {Rotenstein, Lisa and Holmgren, A. Jay and Thombley, Robert and Sriram, Aditi and Dbouk, Reema H. and Jost, Melissa and Aizenberg, Debbie and MacDonald, Scott and Kanaparthy, Naga and Williams, Brian and Hsiao, Allen and Schwamm, Lee and Murray, Sara and Byron, Maria and Soleimani, Hossein and You, Jacqueline G. and Centi, Amanda J. and Iannaccone, Christine and Frits, Michelle and Landman, Adam B. and Singh, Karandeep and Tai-Seale, Ming and Cao, Jie and Lawrence, Katharine and Mann, Devin and Holland, Christopher and Blanchette, Bryan and Ehrenfeld, Jesse and Melnick, Edward R. and Bates, David W. and Adler-Milstein, Julia and Mishuris, Rebecca G.},
  journal = {JAMA},
  year    = {2026},
  doi     = {10.1001/jama.2026.2253},
  url     = {https://jamanetwork.com/journals/jama/fullarticle/10.1001/jama.2026.2253}
}

@article{williams2025evaluating,
  title   = {Evaluating large language models for drafting emergency department encounter summaries},
  author  = {Williams, Christopher Y. K. and Bains, Jaskaran and Tang, Tianyu and Patel, Kishan and Lucas, Alexa N. and Chen, Fiona and Miao, Brenda Y. and Butte, Atul J. and Kornblith, Aaron E.},
  journal = {PLOS Digital Health},
  volume  = {4},
  number  = {6},
  pages   = {e0000899},
  year    = {2025},
  doi     = {10.1371/journal.pdig.0000899},
  url     = {https://doi.org/10.1371/journal.pdig.0000899}
}

@article{asgari2025framework,
  title   = {A framework to assess clinical safety and hallucination rates of {LLM}s for medical text summarisation},
  author  = {Asgari, Elham and Monta{\~n}a-Brown, Nina and Dubois, Magda and Khalil, Saleh and Balloch, Jasmine and Au Yeung, Joshua and Pimenta, Dominic},
  journal = {npj Digital Medicine},
  volume  = {8},
  number  = {1},
  pages   = {274},
  year    = {2025},
  doi     = {10.1038/s41746-025-01670-7},
  url     = {https://doi.org/10.1038/s41746-025-01670-7}
}

@inproceedings{moramarco-etal-2022-human,
  title     = {Human Evaluation and Correlation with Automatic Metrics in Consultation Note Generation},
  author    = {Moramarco, Francesco and Papadopoulos Korfiatis, Alex and Perera, Mark and Juric, Damir and Flann, Jack and Reiter, Ehud and Belz, Anya and Savkov, Aleksandar},
  booktitle = {Proceedings of the 60th Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)},
  pages     = {5739--5754},
  year      = {2022},
  address   = {Dublin, Ireland},
  publisher = {Association for Computational Linguistics},
  doi       = {10.18653/v1/2022.acl-long.394},
  url       = {https://aclanthology.org/2022.acl-long.394/}
}

@article{croxford2025pdsqi9,
  title   = {Development and Validation of the Provider Documentation Summarization Quality Instrument for Large Language Models},
  author  = {Croxford, Emma and Gao, Yanjun and Pellegrino, Nicholas and Wong, Karen K. and Wills, Graham and First, Elliot and Schnier, Miranda and Burton, Kyle and Ebby, Cris G. and Gorskic, Jillian and Kalscheur, Matthew and Khalil, Samy and Pisani, Marie and Rubeor, Tyler and Stetson, Peter and Liao, Frank and Goswami, Cherodeep and Patterson, Brian and Afshar, Majid},
  journal = {arXiv preprint arXiv:2501.08977},
  year    = {2025},
  note    = {Also published in JAMIA 2025; PMID 40323321},
  url     = {https://arxiv.org/abs/2501.08977},
  doi     = {10.48550/arXiv.2501.08977}
}

@article{chung2025verifact,
  title   = {VeriFact: Verifying Facts in LLM-Generated Clinical Text with Electronic Health Records},
  author  = {Chung, Philip and Swaminathan, Akshay and Goodell, Alex J. and Kim, Yeasul and Reincke, S. Momsen and Han, Lichy and Deverett, Ben and Sadeghi, Mohammad Amin and Ariss, Abdel-Badih and Ghanem, Marc and Seong, David and Lee, Andrew A. and Coombes, Caitlin E. and Bradshaw, Brad and Sufian, Mahir A. and Hong, Hyo Jung and Nguyen, Teresa P. and Rasouli, Mohammad R. and Kamra, Komal and Burbridge, Mark A. and McAvoy, James C. and Saffary, Roya and Ma, Stephen P. and Dash, Dev and Xie, James and Wang, Ellen Y. and Schmiesing, Clifford A. and Shah, Nigam and Aghaeepour, Nima},
  journal = {arXiv preprint arXiv:2501.16672},
  year    = {2025},
  note    = {Also published in NEJM AI, doi:10.1056/AIdbp2500418},
  url     = {https://arxiv.org/abs/2501.16672},
  doi     = {10.48550/arXiv.2501.16672}
}
```

---

## Appendix: additional candidates flagged but not included (useful if expanding)

- **Tierney et al. 2025** — one-year follow-up (NEJM Catalyst, doi:10.1056/CAT.25.0040) documenting >2.5M ambient scribe uses at TPMG and ~15,700 hours saved; strongest complement to Tierney 2024 if expansion is needed.
- **Cain/Young et al. 2025** (NEJM AI, doi:10.1056/AIcs2400977) — Kaiser's enterprise rollout of Abridge across all 8 regions, 600 offices, 40 hospitals, supporting >4M encounters.
- **Ma et al. 2025** (JAMIA, doi:10.1093/jamia/ocae304) — Stanford DAX utilization companion to Shah 2025 (55% encounter utilization, ~20 min/day EHR savings).
- **Wright et al. 2025** (JAMIA ocaf186) — Vanderbilt enterprise rollout; >2,400 clinicians, 20.1% of visit notes using ambient scribing, 90.9% retention-intent.
- **Haberle et al. 2024** (JAMIA) — Atrium Health DAX cohort study.
- **Van Veen et al. 2024** (Nat Med, doi:10.1038/s41591-024-02855-5) — Stanford physician-reader study across four clinical summarization tasks; favorable to LLMs but methodology critiqued by Keszthelyi et al. (JMIR 2025, e68998).
- **Yim et al. 2023** (ACI-Bench, *Sci Data*, doi:10.1038/s41597-023-02487-3) — benchmark + multi-metric evaluation protocol (ROUGE + BERTScore + UMLS concept F1 + human rating) that became the MEDIQA-Chat de facto standard; strong candidate if the ~8-paper cap is relaxed.
- **Hartman et al. 2023** (JAMIA, doi:10.1093/jamia/ocad089) — BART/LED discharge-summary hospital course; 28% hallucination rate in LED outputs.
- **Anderson et al. 2025** (Mayo Clin Proc Digital Health) — simulated-encounter evaluation of commercial ambient scribe platforms with omission/commission/partial error classification.
- **Bedi et al. 2025** (MedHELM) — LLM-jury protocol with inter-rater statistics useful if defending jury-vs.-single-judge design choices.