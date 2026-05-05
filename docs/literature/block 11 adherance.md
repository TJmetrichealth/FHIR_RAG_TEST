# Block 11 — Feature engineering for adherence ML: literature review

## Upfront findings and flags

**Good news first.** Across the five queries, the two strongest citable anchors for the preprint's O6 feature-extraction arm are already in place: a canonical pharmacy-claims ML-for-adherence paper (Lo-Ciganic 2015), a temporal-EHR neural model with interpretable time-aware features (Choi/RETAIN 2016), and — most importantly — a **2025 JAMIA paper that applies LLM-extracted narrative features to a medication-retention prediction task** (Nateghi Haredasht et al.). That last paper **materially constrains any "first-of-kind" novelty claim** for LLM-narrative features in adherence prediction and must be cited and distinguished, not ignored.

**Two flags that matter for the bibliography.**

1. **"Steiner et al. (2020)" could not be verified as an ML adherence-prediction paper.** Targeted PubMed and Scholar searches over Steiner-authored 2020 work on adherence prediction returned nothing matching that description. John F. Steiner's (Kaiser Permanente Colorado) influential adherence work is earlier — Steiner 2009 on clinical-feature weakness for refill adherence, Steiner 2010 Medical Care commentary, and the Raebel/Steiner 2013 Medical Care terminology paper that standardizes PDC, MPR, implementation, and persistence. **The preprint likely intended Steiner 2009 or Raebel/Steiner 2013, or a different author.** For a verifiable AUC benchmark citation in the same register, Zullig et al. 2019 (*Health Services Research*) is a cleaner substitute — it reports C-indices of 0.664–0.677 across logistic regression, LASSO, and random forest on Medicare statin initiators, which is the kind of benchmark the planning document is trying to anchor to. **Recommend TJ verify the original Steiner citation in the metricHEALTH proposal and either correct it or add Zullig 2019 alongside.**

2. **Choi et al. 2016 resolves cleanly to RETAIN (NeurIPS 2016, arXiv:1608.05745)**, not Doctor AI. RETAIN's reverse-time attention is the closer methodological analogue to temporal feature engineering for adherence (visit-level sequences, weighted recency), and it is open access on arXiv.

The eight recommended citations follow.

---

## 1. RETAIN — Choi et al. 2016 (temporal-pattern EHR ML)

**Citation.** Choi E, Bahadori MT, Kulas JA, Schuetz A, Stewart WF, Sun J. RETAIN: An Interpretable Predictive Model for Healthcare using Reverse Time Attention Mechanism. *Advances in Neural Information Processing Systems* 29 (NeurIPS 2016), pp. 3504–3512. arXiv:1608.05745.

**Open access.** Yes (arXiv + NeurIPS proceedings PDF).

**Summary.** RETAIN is a two-level neural attention model over longitudinal EHR visit sequences. Attention is applied in **reverse time order**, mimicking how clinicians weight recent visits more heavily, and yields per-visit and per-variable importance scores alongside a diagnosis- or event-prediction head. Trained on a Sutter Health cohort of ~14 million visits from 263,000 patients over 8 years; a heart-failure prediction task was used as the main evaluation. RETAIN matched GRU/LSTM accuracy while giving logistic-regression-level interpretability. For Block 11 it is the canonical citation for **visit-level temporal feature representation on EHRs**, directly parallel to the temporal aggregation pipeline the preprint uses over MedicationDispense and Encounter sequences.

**BibTeX.**
```bibtex
@inproceedings{choi2016retain,
  author    = {Choi, Edward and Bahadori, Mohammad Taha and Kulas, Jimeng A. and Schuetz, Andy and Stewart, Walter F. and Sun, Jimeng},
  title     = {{RETAIN}: An Interpretable Predictive Model for Healthcare Using Reverse Time Attention Mechanism},
  booktitle = {Advances in Neural Information Processing Systems 29 (NeurIPS 2016)},
  pages     = {3504--3512},
  year      = {2016},
  eprint    = {1608.05745},
  archivePrefix = {arXiv}
}
```

---

## 2. Lo-Ciganic et al. 2015 — Foundational ML-on-claims for adherence and canonical feature set

**Citation.** Lo-Ciganic W-H, Donohue JM, Thorpe JM, Perera S, Thorpe CT, Marcum ZA, Gellad WF. Using machine learning to examine medication adherence thresholds and risk of hospitalization. *Medical Care* 2015;53(8):720–728. DOI: 10.1097/MLR.0000000000000394. PMID: 26147866.

**Open access.** Author manuscript freely available at PMC4503478; final published version paywalled at Wolters Kluwer.

**Summary.** Pennsylvania Medicaid cohort of 33,130 non-dual-eligible adults initiating oral hypoglycemics. A random survival forest with survival-tree thresholding is fit over 19 candidate features: demographics, Elixhauser comorbidity index, diabetes complication severity index, prior ED visits and hospitalizations, number of prescriptions, number of prescribers, insulin use, Medicaid eligibility category, and **PDC for oral hypoglycemics** (strictly distinct from MPR). The key methodological finding is that the conventional 80% PDC threshold is **not universally optimal**: empirically optimal thresholds ranged from 46% to 94% depending on patient complexity. Top predictors in descending importance: prior hospitalization/ED, prescription count, diabetes complications, insulin use, PDC, prescriber count, Elixhauser, eligibility category. For Block 11 this is the **canonical enumeration of the claims-based adherence feature family** — utilization + comorbidity + prescriber + prior-adherence — that the preprint's structured-FHIR arm must replicate.

**BibTeX.**
```bibtex
@article{lociganic2015using,
  author  = {Lo-Ciganic, Wei-Hsuan and Donohue, Julie M. and Thorpe, Joshua M. and Perera, Subashan and Thorpe, Carolyn T. and Marcum, Zachary A. and Gellad, Walid F.},
  title   = {Using Machine Learning to Examine Medication Adherence Thresholds and Risk of Hospitalization},
  journal = {Medical Care},
  volume  = {53},
  number  = {8},
  pages   = {720--728},
  year    = {2015},
  doi     = {10.1097/MLR.0000000000000394}
}
```

---

## 3. Franklin et al. 2018 — Claims vs EHR feature head-to-head for adherence trajectory

**Citation.** Franklin JM, Gopalakrishnan C, Krumme AA, Singh K, Rogers JR, Kimura J, McKay C, McElwee NE, Choudhry NK. The relative benefits of claims and electronic health record data for predicting medication adherence trajectory. *American Heart Journal* 2018;197:153–162. DOI: 10.1016/j.ahj.2017.10.012. PMID: 29447776.

**Open access.** **No — paywalled at Elsevier.** No public preprint located. Flag for verification; consider requesting via institutional access or contacting authors.

**Summary.** Linked Medicare Advantage claims plus a comprehensive multi-specialty EHR for patients filling a statin, antihypertensive, or oral antidiabetic in 2011–2012. Outcome is membership in the worst-adherence group from a group-based trajectory model fit to 12-month PDC patterns (not dichotomized PDC≥0.8). The paper is an **explicit feature-engineering ablation**: penalized-regression models built on (a) claims-only features (prior adherence, fill-gap statistics, utilization), (b) EHR-only features (labs, vitals, diagnoses, orders, demographics), and (c) combined. Claims features alone reached C = 0.78; EHR features alone C = 0.72; a single claims variable — prior fill gap ≥ 6 days — dominated. This is the **strongest direct precedent for the preprint's data-source-comparison design** and justifies treating prior-gap and prior-PDC features as baseline in both the structured and narrative arms.

**BibTeX.**
```bibtex
@article{franklin2018relative,
  author  = {Franklin, Jessica M. and Gopalakrishnan, Chandrasekar and Krumme, Alexis A. and Singh, Karandeep and Rogers, James R. and Kimura, Joe and McKay, Caroline and McElwee, Newell E. and Choudhry, Niteesh K.},
  title   = {The Relative Benefits of Claims and Electronic Health Record Data for Predicting Medication Adherence Trajectory},
  journal = {American Heart Journal},
  volume  = {197},
  pages   = {153--162},
  year    = {2018},
  doi     = {10.1016/j.ahj.2017.10.012}
}
```

---

## 4. Zullig et al. 2019 — Reference AUC benchmark (substitute for unverified Steiner 2020)

**Citation.** Zullig LL, Jazowski SA, Wang TY, Hellkamp A, Wojdyla D, Thomas L, Egbuonu-Davis L, Beal A, Bosworth HB. Novel application of approaches to predicting medication adherence using medical claims data. *Health Services Research* 2019;54(6):1255–1262. DOI: 10.1111/1475-6773.13200. PMC6863234.

**Open access.** Yes via PMC.

**Summary.** Post-myocardial-infarction statin adherence in a Medicare 5% sample (N ≈ 11,969), with PDC-based adherence at one year as the outcome. The authors benchmark three methods — backward-selection logistic regression, LASSO, and random forest — on a claims feature set including demographics, prior statin use, cardiovascular comorbidities, dual-eligibility, discharge medication count, and prior utilization. All three models achieved **moderate, essentially indistinguishable C-indices of 0.664–0.677**. Prior statin use was by far the strongest predictor (OR ≈ 3.55–3.65), consistent with Franklin 2018 and Koesmahargyo 2020. For Block 11 this is the **cleanest single benchmark AUC/C-index reference** for claims-based adherence prediction on a chronic cardiovascular cohort and a defensible substitute for the unverified Steiner 2020 citation.

**BibTeX.**
```bibtex
@article{zullig2019novel,
  author  = {Zullig, Leah L. and Jazowski, Shelley A. and Wang, Tracy Y. and Hellkamp, Anne and Wojdyla, Daniel and Thomas, Laine and Egbuonu-Davis, Lisa and Beal, Anne and Bosworth, Hayden B.},
  title   = {Novel Application of Approaches to Predicting Medication Adherence Using Medical Claims Data},
  journal = {Health Services Research},
  volume  = {54},
  number  = {6},
  pages   = {1255--1262},
  year    = {2019},
  doi     = {10.1111/1475-6773.13200}
}
```

---

## 5. Gu et al. 2021 — Gradient-boosted trees and deep learning on adherence event data

**Citation.** Gu Y, Zalkikar A, Liu M, Kelly L, Hall A, Daly K, Ward T. Predicting medication adherence using ensemble learning and deep learning models with large scale healthcare data. *Scientific Reports* 2021;11:18961. DOI: 10.1038/s41598-021-98387-w.

**Open access.** Yes (Springer Nature, CC-BY).

**Summary.** Retrospective analysis of 342,174 injection-disposal events from a connected "smart" sharps-bin device used by patients self-administering injectable biologics (multiple chronic conditions including rheumatoid arthritis, multiple sclerosis, Crohn's disease). Outcome is a **binary event-level "on-time" vs "not on-time" next injection** — distinct from PDC or MPR; do not conflate when citing. Features are event-history variables (prior injection timing, inter-injection intervals, counts). Seven models are benchmarked with Bayesian hyperparameter search: **XGBoost, Extra Trees, Random Forest, GBM, MLP, RNN, and LSTM**. Internal-validation AUCs cluster tightly in 0.839–0.843; LSTM was selected for future-window evaluation (AUC 0.839, F1 0.77). For Block 11 this is the strongest citation for the claim that **gradient-boosted trees and sequence models are statistically indistinguishable on dense adherence-event data**, which justifies the preprint's use of XGBoost over an end-to-end temporal network.

**BibTeX.**
```bibtex
@article{gu2021predicting,
  author  = {Gu, Yingqi and Zalkikar, Akshay and Liu, Mingming and Kelly, Lara and Hall, Amy and Daly, Kieran and Ward, Tomas},
  title   = {Predicting Medication Adherence Using Ensemble Learning and Deep Learning Models with Large Scale Healthcare Data},
  journal = {Scientific Reports},
  volume  = {11},
  pages   = {18961},
  year    = {2021},
  doi     = {10.1038/s41598-021-98387-w}
}
```

---

## 6. Nateghi Haredasht et al. 2025 — LLM-extracted features for medication retention (critical)

**Citation.** Nateghi Haredasht F, Lopez I, Tate S, Ashtari P, Chan MM, Kulkarni D, Chen C-YA, Vangala M, Griffith K, Bunning B, Miner AS, Hernandez-Boussard T, Humphreys K, Lembke A, Vance LA, Chen JH. Predicting treatment retention in medication for opioid use disorder: a machine learning approach using NLP and LLM-derived clinical features. *Journal of the American Medical Informatics Association* 2025;32(12):1865–1876. DOI: 10.1093/jamia/ocaf157.

**Open access.** Yes (CC-BY, Oxford open).

**Summary.** Predicts 6-month retention on buprenorphine-naloxone — a **direct medication-adherence/attrition task**. Development set: 1,800 treatment encounters and 13,922 notes from Stanford STARR; external validation: 459 encounters from the NeuroBlu multi-site behavioral health database. The CLEAR pipeline uses Flan-T5-XXL for entity recognition and **GPT-4** for contextual binary classification (F1 = 0.97 across extraction tasks, beating Med42, Llama-3, Flan-UL2) to extract 13 psychosocial/clinical features (homelessness, chronic pain, major depression, liver disease, PTSD, and others) from free-text notes. The 13 LLM features are concatenated with 193 structured OMOP features and fed to **logistic regression, random forest, and XGBoost** classifiers plus survival variants. LLM-augmented models gained statistically significant ROC-AUC improvements (Wilcoxon p<0.05, ~+4 points for LR, XGBoost top ROC-AUC 0.65). **This is a near-exact precedent for the preprint's LLM-narrative feature arm** and must be cited explicitly; it weakens any first-of-kind novelty claim for medication-adherence LLM feature extraction and forces the preprint to position on non-MOUD chronic-disease adherence, FHIR-structured comparison, or Canadian PSP context.

**BibTeX.**
```bibtex
@article{nateghi2025predicting,
  author  = {Nateghi Haredasht, Fateme and Lopez, Ivan and Tate, Steven and Ashtari, Pooya and Chan, Min Min and Kulkarni, Deepali and Chen, Chwen-Yuen Angie and Vangala, Maithri and Griffith, Kira and Bunning, Bryan and Miner, Adam S. and Hernandez-Boussard, Tina and Humphreys, Keith and Lembke, Anna and Vance, L. Alexander and Chen, Jonathan H.},
  title   = {Predicting Treatment Retention in Medication for Opioid Use Disorder: A Machine Learning Approach Using {NLP} and {LLM}-Derived Clinical Features},
  journal = {Journal of the American Medical Informatics Association},
  volume  = {32},
  number  = {12},
  pages   = {1865--1876},
  year    = {2025},
  doi     = {10.1093/jamia/ocaf157}
}
```

---

## 7. Anderson et al. 2025 — Paging Dr. GPT (LLM-extracted features + logistic regression)

**Citation.** Anderson D, Anderson M, Bjarnadottir M, Mahar S, Reyya S. Paging Dr. GPT: Extracting Information from Clinical Notes to Enhance Patient Predictions. arXiv:2504.12338 [cs.CL], 14 April 2025.

**Open access.** Yes (arXiv). Not yet peer-reviewed — flag as preprint.

**Summary.** Patient-level in-hospital mortality prediction for CCU/CVICU admissions on MIMIC-IV-Note, N = 14,011 first-time admissions. **GPT-4o-mini** is prompted with each patient's discharge summary and answers a fixed set of simple clinical questions; the categorical/binary answers are used as input features to a logistic regression model — explicitly not end-to-end LLM prediction and no fine-tuning. The paper compares three arms: structured-tabular-only LR, GPT-feature LR, and combined. GPT-feature LR alone outperforms the standard tabular LR; the combined model gains on average +5.1 AUC points and +29.9% PPV in the top-risk decile. This is the **cleanest template in the literature for the preprint's A-vs-B comparison design** (structured vs LLM-extracted vs combined) on a non-adherence clinical prediction task, and it establishes that the pattern transfers when features are drawn from unstructured narrative rather than structured tables.

**BibTeX.**
```bibtex
@misc{anderson2025paging,
  author        = {Anderson, David and Anderson, Michaela and Bjarnadottir, Margret and Mahar, Stephen and Reyya, Shriyan},
  title         = {Paging {Dr.} {GPT}: Extracting Information from Clinical Notes to Enhance Patient Predictions},
  year          = {2025},
  eprint        = {2504.12338},
  archivePrefix = {arXiv},
  primaryClass  = {cs.CL},
  doi           = {10.48550/arXiv.2504.12338}
}
```

---

## 8. Gao et al. 2024 — Balanced counter-evidence on LLM features

**Citation.** Gao Y, Myers S, Chen S, Dligach D, Miller TA, Bitterman D, Churpek M, Afshar M. When Raw Data Prevails: Are Large Language Model Embeddings Effective in Numerical Data Representation for Medical Machine Learning Applications? *Findings of the Association for Computational Linguistics: EMNLP 2024*, pp. 5414–5428. arXiv:2408.11854.

**Open access.** Yes (ACL Anthology, CC-BY).

**Summary.** Evaluates whether LLM-derived **embeddings** serve as useful input features for tabular ML classifiers on three MIMIC-based tasks: diagnosis prediction, in-hospital mortality, and length of stay. Raw tabular values are templated into natural-language queries, passed through instruction-tuned LLMs (zero-shot), and last-hidden-state embeddings are used as inputs to **XGBoost** and logistic/elastic-net heads. Authors systematically test prompt-engineering and few-shot variants and benchmark against raw-numerical baselines. Headline finding: **raw numerical features plus XGBoost generally win**, but zero-shot LLM embeddings are competitive on several settings and robust across tasks. For Block 11 this is essential **counter-evidence** that LLM-derived features are not universally superior — necessary for honest framing of the preprint's narrative-feature arm and a hedge against overclaiming.

**BibTeX.**
```bibtex
@inproceedings{gao2024raw,
  author    = {Gao, Yanjun and Myers, Skatje and Chen, Shan and Dligach, Dmitriy and Miller, Timothy A. and Bitterman, Danielle and Churpek, Matthew and Afshar, Majid},
  title     = {When Raw Data Prevails: Are Large Language Model Embeddings Effective in Numerical Data Representation for Medical Machine Learning Applications?},
  booktitle = {Findings of the Association for Computational Linguistics: {EMNLP} 2024},
  pages     = {5414--5428},
  year      = {2024},
  publisher = {Association for Computational Linguistics},
  url       = {https://aclanthology.org/2024.findings-emnlp.311}
}
```

---

## Synthesis — state of the field in ~150 words

Adherence-prediction ML on claims and EHR data is a mature but modestly-performing subfield. Claims-based models on chronic cardiovascular and diabetes cohorts typically plateau at **C-index 0.66–0.78** (Zullig 2019, Franklin 2018); denser event-level adherence data pushes AUCs to **~0.84** (Gu 2021). Across settings, **prior-adherence features — especially fill-gap length and prior PDC — dominate all other predictors**, with utilization, comorbidity burden, and prescriber count adding modest lift. PDC and MPR are distinct metrics and the 80% threshold is a convention, not an empirical optimum (Lo-Ciganic 2015). Gradient-boosted trees and recurrent/attention networks are statistically indistinguishable on these tabular feature sets (Gu 2021, RETAIN). The LLM-as-feature-extractor → tabular-classifier pattern is now an **established design family in clinical ML** (Anderson 2025, Gao 2024, Nateghi Haredasht 2025) with mixed evidence — it helps when features come from unstructured narrative, and hurts or ties when features come from already-structured numerical data.

## Gap statement — suitable for the related-work section

Prior work has thoroughly characterized the canonical adherence feature set on claims data (Lo-Ciganic 2015, Franklin 2018), established reference AUC ranges for claims-based adherence prediction (Zullig 2019, Gu 2021), and introduced temporally-aware neural representations for EHR sequences (Choi et al., RETAIN 2016). A recent but growing line of work uses LLMs to extract features from unstructured clinical text for downstream tabular classifiers — demonstrated on in-hospital mortality (Anderson 2025), general MIMIC tasks (Gao 2024), and most directly on MOUD retention (Nateghi Haredasht 2025). However, no prior work has **(i) evaluated LLM-narrative feature extraction against structured-FHIR-derived features head-to-head on a matched cohort for a non-MOUD medication-adherence classification task**, and **(ii) none has done so in the Canadian Patient Support Program setting where structured FHIR R4B MedicationRequest/MedicationDispense data and LLM-generated narratives are both available for the same patients.** The O6 arm of this preprint fills that gap and provides the first direct structured-vs-narrative feature ablation with resource-aware retrieval as a third comparator.

---

## Notes on unmet requests and quality flags

- **Steiner 2020 unverified.** No machine-learning adherence-prediction paper by Steiner published in 2020 could be located after targeted searching. Recommend TJ open the metricHEALTH proposal PDF and verify the exact citation — the intended reference may be Steiner 2009 (*Circ Cardiovasc Qual Outcomes*), Steiner 2010 (*Med Care* commentary), or Raebel/Steiner 2013 (*Med Care*, PDC/MPR terminology standardization). Until then, **cite Zullig et al. 2019 as the claims-based-adherence AUC benchmark**; it is open access, well-scoped, and methodologically transparent.
- **Franklin 2018 is paywalled.** No preprint located. Cite with awareness; consider contacting the Choudhry/Franklin group for an author manuscript.
- **Anderson 2025 is a non-peer-reviewed arXiv preprint**; appropriate as a methodological citation but should be flagged as preprint in the related-work text.
- **PDC vs MPR.** Lo-Ciganic 2015 uses PDC strictly; Gu 2021 uses event-level on-time/late (neither PDC nor MPR); Franklin 2018 uses trajectory-group membership derived from PDC. Never equate these metrics in the preprint text.
- **Novelty hedging.** Given Nateghi Haredasht 2025, the preprint must not claim first-of-kind LLM-narrative features for medication adherence. Safe positioning: first **FHIR-structured-vs-LLM-narrative head-to-head** with resource-aware retrieval as a third arm, in a **Canadian PSP** setting, on a **non-MOUD chronic-disease** adherence task.