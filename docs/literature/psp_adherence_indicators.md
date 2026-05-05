# Specialty pharmacy and long-acting injectables: clinical context

This block establishes that **specialty medications — biologics, long-acting injectables (LAIs), and cyclic chemotherapy regimens — are an economically dominant, clinically complex, and NLP-under-studied drug class**, making them a well-motivated domain for a FHIR-structured vs. narrative-RAG comparison. The evidence gathered converges on three points: specialty drugs now account for roughly half of US prescription spend and nearly a third of Canadian public-plan drug spend despite very low prescription volume; adherence and regimen-state tracking for these drugs is genuinely hard (missed-dose semantics for LAIs, real-world persistence gaps for biologics, cycle-delay effects on chemotherapy dose intensity); and prior NLP/ML work targeting specialty pharmacy specifically is effectively absent, confirming a real gap.

## 1. Prevalence and cost: specialty medications dominate drug spend

Specialty drugs are the most economically consequential segment of modern pharmacotherapy, and the gap between prescription volume and spend share has widened sharply since 2012.

**Niu S, Happe LE, Abuloha S, Svensson M. (2024).** *Concentration of spending and share of specialty drug spending in Medicare Part D over a 10-year period.* Journal of Managed Care & Specialty Pharmacy, 30(12), 1355–1363. DOI: 10.18553/jmcp.2024.30.12.1355. PMID: 39612254 (open access via PMC11607209).

Repeated cross-sectional analysis of the CMS Part D Drug Spending Dashboard (2012–2021) quantifying concentration and the specialty/non-specialty split, using the CMS monthly cost-tier definition ($670/month from 2017 onward). Specialty drug spending grew at a **23.5% compound annual rate** over the decade, and by 2021 specialty drugs were **6.2% of Part D prescription claims but 71.1% of gross spending** — up from 21.7% in 2012. The authors also situate Part D within the all-payer picture, noting that specialty drugs rose from 32% of US drug spend in 2012 to **~51% in 2022**. *Why cited:* canonical peer-reviewed figure for the US specialty-spend share and growth trajectory used in the framing paragraph of the introduction.

**Canadian Institute for Health Information (CIHI). (2023).** *Prescribed Drug Spending in Canada, 2023: A focus on public drug programs.* Ottawa: CIHI. https://www.cihi.ca/en/prescribed-drug-spending-in-canada-2023

CIHI's annual National Prescription Drug Utilization Information System (NPDUIS) report is the authoritative Canadian source for public drug-plan spending. It shows Canada does not use the US "specialty" label operationally and instead tracks **biologics** and **high-cost drugs** (≥ CA$10,000/beneficiary/year) as proxies. In 2022, **biologics accounted for 29.6% of public drug program spending (≈CA$4.7B) from only 2.4% of claims**, and the **2.2% of beneficiaries whose plan paid ≥ CA$10,000 accounted for 43.3% of total spending**. *Why cited:* only authoritative Canadian figure for specialty-class spend concentration; anchors the Canadian-relevance framing for the metricHEALTH PSP context. Flagged as a government report because no Canadian peer-reviewed equivalent of Niu et al. exists.

## 2. Regimen-adherence tracking is clinically hard for LAIs, biologics, and cyclic chemo

The second argument is that the temporal structure of specialty regimens — long and variable inter-dose intervals, real-world discontinuations, and dose delays in cyclic protocols — makes adherence measurement and regimen-state tracking non-trivial, and that this difficulty has direct clinical consequences.

**Correll CU, Litman RE, Filts Y, et al. (2024).** *Three-year outcomes of 6-month paliperidone palmitate in adults with schizophrenia: an open-label extension study of a randomized clinical trial.* JAMA Psychiatry, 81(11), 1099–1108. DOI: 10.1001/jamapsychiatry.2024.1994.

Open-label extension of the phase-3 paliperidone palmitate 6-monthly (PP6M) trial following 121 patients for up to three years; **91.7% of relapse-free completers remained relapse-free at 3 years**. PP6M is the only antipsychotic with a 6-month interval, so each patient has ~2 administrations per year. This breaks the implicit daily-dose assumption behind standard adherence metrics: Proportion of Days Covered (PDC), Medication Possession Ratio (MPR), and missed-dose counts all become ill-defined because a single missed injection represents a six-month coverage gap and "late-dose" tolerance windows are protocol-specific rather than continuous. *Why cited:* evidence that temporal reasoning over LAIs cannot rely on daily-dose PDC/MPR arithmetic — motivating structured regimen representations.

**Click B, Barnes EL, Cohen BL, et al. (2024).** *Real-world persistence of successive biologics in patients with inflammatory bowel disease: findings from ROTARY.* Inflammatory Bowel Diseases, 30(10), 1776–1788. DOI: 10.1093/ibd/izad238.

Retrospective US claims cohort (ROTARY) of ~15,000 IBD patients comparing persistence across adalimumab, infliximab, vedolizumab, and ustekinumab as first- and second-line biologics. **Adalimumab — a self-administered subcutaneous biologic dosed every 2 weeks — had significantly higher discontinuation than its peers in both lines**, with substantial switching/discontinuation within 12 months. The study shows that even among FDA-approved, guideline-recommended regimens, real-world persistence is poor and varies by administration route and dosing interval. *Why cited:* primary real-world evidence that biologic injection-interval adherence is both poor and clinically differentiating, justifying longitudinal tracking as a clinical signal.

**Eyre TA, Martinez-Calle N, Hildyard C, et al. (2019).** *Impact of intended and relative dose intensity of R-CHOP in a large, consecutive cohort of elderly diffuse large B-cell lymphoma patients treated with curative intent.* Journal of Internal Medicine, 285(6), 681–692. DOI: 10.1111/joim.12889.

Multicenter UK study of 690 DLBCL patients ≥70 years receiving curative-intent R-CHOP on 21-day cycles across eight centers (2009–2018). Examined intended dose intensity (IDI) and relative dose intensity (RDI) of cyclophosphamide and doxorubicin, where RDI is the ratio of actual cumulative dose per unit time to the planned protocol. **Reduced RDI — driven by cycle delays and dose reductions — was independently associated with worse overall and progression-free survival**, independent of age. *Why cited:* establishes that RDI, an inherently temporal quantity combining scheduled vs. actual cycle timing with dose reductions, is prognostic — so correctly reconstructing the cycle timeline from records has direct clinical consequences.

**Grundy Q, Quanbury A, Chaudhry SA, et al. (2023).** *Prevalence and nature of manufacturer-sponsored patient support programs for prescription drugs in Canada: a cross-sectional study.* CMAJ, 195(46), E1565–E1576. DOI: 10.1503/cmaj.230841.

Cross-sectional study of all manufacturer-sponsored patient support programs (PSPs) across 2,556 prescription drugs marketed in Canada as of August 2022. **256 drugs (10%) had an associated PSP, concentrated among brand-name biologics, orphan, and high-cost specialty drugs**; 90.2% offered reimbursement navigation and 87.1% provided clinical case management including nurse-led injection training, infusion coordination, and adherence support. *Why cited:* frames PSPs as the de facto operational home for specialty-medication adherence tracking in Canada, grounding the applied relevance of the RAG-for-PSP problem and the metricHEALTH context.

## 3. A genuine NLP/ML gap for specialty pharmacy

Systematic search across arXiv, ACL Anthology, PubMed, JAMIA, and JMIR did not surface any work that directly addresses specialty-pharmacy NLP, LLM question answering, or RAG over specialty regimens. The closest prior art clusters into two adjacent silos — cyclic chemotherapy timeline extraction, and general FHIR-grounded LLM QA — neither of which combines both elements at the scale of specialty-medication workflows.

**Yao J, Hochheiser H, Yoon W, Goldner E, Savova G. (2024).** *Overview of the 2024 Shared Task on Chemotherapy Treatment Timeline Extraction.* Proceedings of the 6th Clinical Natural Language Processing Workshop (ClinicalNLP @ NAACL 2024), 557–569. ACL Anthology: 2024.clinicalnlp-1.53. DOI: 10.18653/v1/2024.clinicalnlp-1.53.

ChemoTimelines is a community shared task using de-identified EHRs from 57,530 breast/ovarian and 15,946 melanoma patients to construct patient-level chemotherapy event timelines. Subtask 1 provides gold events and asks for temporal relations; Subtask 2 is end-to-end extraction from notes. Submissions mixed rule-based pipelines, BERT fine-tuning, zero-shot GPT-4 / Mixtral, and instruction tuning. **Fine-tuned smaller LMs substantially outperformed zero-shot LLM prompting on the temporal component**, suggesting that LLMs alone are insufficient for cyclic-regimen reasoning without explicit structure. *Why cited:* only sustained NLP benchmark on a specialty-medication class (cyclic IV chemo); motivates structured representations over pure-text LLM reasoning.

**Schmiedmayer P, Rao A, Zagar P, Ravi V, Zahedivash A, Fereydooni A, Aalami O. (2024).** *LLM on FHIR — demystifying health records.* arXiv:2402.01711 [cs.CL]. (Subsequently published as Rao et al., *LLMonFHIR: A physician-validated, large language model–based mobile application for querying patient electronic health data*, JACC: Advances, 2025, DOI: 10.1016/j.jacadv.2025.101780.)

Open-source iOS application that lets patients query their own FHIR record via GPT-4, using function-calling as a retrieval abstraction to dynamically pull relevant FHIR resources rather than stuffing a full bundle into context. A physician panel evaluated the system on seven patient questions; accuracy was weakest on lab-value retrieval due to function-calling failures, and medications were not evaluated as a distinct category. *Why cited:* canonical prior art for "LLM + FHIR + retrieval" over a single patient's record — our structural template — and the most direct precedent to which our specialty-pharmacy specialization and structured-vs-narrative comparison extends.

**On the gap:** No published work, as of April 2026, applies NLP, RAG, or LLM question-answering to specialty-pharmacy workflows specifically — including PSPs, biologic and LAI adherence, or chemotherapy cycle reasoning in an interactive QA setting. Adjacent threads include chemo-timeline extraction (Yao et al., 2024), FHIR-grounded general EHR QA (Schmiedmayer et al., 2024; Lee et al., FHIR-AgentBench, arXiv:2509.19319), and pharmacy-facing LLMs for oral-prescription error checking (Bhatt et al., *Nature Medicine*, 2024) — but none evaluate specialty-medication regimens or combine FHIR structure with specialty-pharmacy QA. Confirming this absence is itself a contribution of the present paper.

---

## BibTeX

```bibtex
@article{niu2024specialty,
  author  = {Niu, Sheng and Happe, Laura E. and Abuloha, Sumaya and Svensson, Mikael},
  title   = {Concentration of spending and share of specialty drug spending in {Medicare Part D} over a 10-year period},
  journal = {Journal of Managed Care \& Specialty Pharmacy},
  year    = {2024},
  volume  = {30},
  number  = {12},
  pages   = {1355--1363},
  doi     = {10.18553/jmcp.2024.30.12.1355},
  pmid    = {39612254}
}

@techreport{cihi2023prescribed,
  author      = {{Canadian Institute for Health Information}},
  title       = {Prescribed Drug Spending in {Canada}, 2023: A focus on public drug programs},
  institution = {Canadian Institute for Health Information},
  address     = {Ottawa},
  year        = {2023},
  url         = {https://www.cihi.ca/en/prescribed-drug-spending-in-canada-2023},
  note        = {Government report}
}

@article{correll2024pp6m,
  author  = {Correll, Christoph U. and Litman, Robert E. and Filts, Yuriy and Llaud{\'o}, Jordi and Naber, Dieter and Torres, Ferran and Mart{\'i}nez, Javier and Gopal, Srihari and Hough, David and Savitz, Adam and Kern Sliwa, Jennifer},
  title   = {Three-year outcomes of 6-month paliperidone palmitate in adults with schizophrenia: an open-label extension study of a randomized clinical trial},
  journal = {JAMA Psychiatry},
  year    = {2024},
  volume  = {81},
  number  = {11},
  pages   = {1099--1108},
  doi     = {10.1001/jamapsychiatry.2024.1994},
  pmid    = {39018073}
}

@article{click2024rotary,
  author  = {Click, Benjamin and Barnes, Edward L. and Cohen, Benjamin L. and Sands, Bruce E. and Hanson, John S. and Rubin, David T. and Thakkar, Bharati and Bluth, Martin and Candela, Ninfa and Lirio, Richard A. and Long, Millie D.},
  title   = {Real-world persistence of successive biologics in patients with inflammatory bowel disease: findings from {ROTARY}},
  journal = {Inflammatory Bowel Diseases},
  year    = {2024},
  volume  = {30},
  number  = {10},
  pages   = {1776--1788},
  doi     = {10.1093/ibd/izad238},
  pmid    = {37921344}
}

@article{eyre2019rchop,
  author  = {Eyre, Toby A. and Martinez-Calle, Nicolas and Hildyard, Catherine and Eyre, David W. and Plaschkes, Hannah and Griffith, James and Wolf, Jennifer and Fields, Paul and Gunawan, Andrea and Oliver, Rebecca and Booth, Stephen and Jones, Gavin L. and Walter, Harriet S. and McKay, Pamela and Phillips, Elizabeth H. and Shah, Nimish and Bishton, Mark J. and Collins, Graham P. and Linton, Kim M. and Cwynarski, Kate and Hawkes, Eliza A. and Ardeshna, Kirit M.},
  title   = {Impact of intended and relative dose intensity of {R-CHOP} in a large, consecutive cohort of elderly diffuse large {B-cell} lymphoma patients treated with curative intent},
  journal = {Journal of Internal Medicine},
  year    = {2019},
  volume  = {285},
  number  = {6},
  pages   = {681--692},
  doi     = {10.1111/joim.12889},
  pmid    = {30811713}
}

@article{grundy2023psp,
  author  = {Grundy, Quinn and Quanbury, Alexandra and Chaudhry, Sohaib Asif and Hart, Alexander and Tavangar, Farnaz and Lexchin, Joel and Gagnon, Marc-Andr{\'e} and Tadrous, Mina},
  title   = {Prevalence and nature of manufacturer-sponsored patient support programs for prescription drugs in {Canada}: a cross-sectional study},
  journal = {CMAJ},
  year    = {2023},
  volume  = {195},
  number  = {46},
  pages   = {E1565--E1576},
  doi     = {10.1503/cmaj.230841},
  pmid    = {38011930}
}

@inproceedings{yao2024chemotimelines,
  author    = {Yao, Jianfu and Hochheiser, Harry and Yoon, Wonjin and Goldner, Eli and Savova, Guergana},
  title     = {Overview of the 2024 shared task on chemotherapy treatment timeline extraction},
  booktitle = {Proceedings of the 6th Clinical Natural Language Processing Workshop},
  year      = {2024},
  pages     = {557--569},
  publisher = {Association for Computational Linguistics},
  doi       = {10.18653/v1/2024.clinicalnlp-1.53},
  url       = {https://aclanthology.org/2024.clinicalnlp-1.53}
}

@article{schmiedmayer2024llmonfhir,
  author  = {Schmiedmayer, Paul and Rao, Adrit and Zagar, Philipp and Ravi, Vishnu and Zahedivash, Aydin and Fereydooni, Arash and Aalami, Oliver},
  title   = {{LLM} on {FHIR} --- demystifying health records},
  journal = {arXiv preprint arXiv:2402.01711},
  year    = {2024},
  eprint  = {2402.01711},
  archiveprefix = {arXiv},
  primaryclass  = {cs.CL},
  note    = {Published as Rao et al., ``LLMonFHIR: A physician-validated, large language model--based mobile application for querying patient electronic health data,'' JACC: Advances (2025), doi:10.1016/j.jacadv.2025.101780}
}
```