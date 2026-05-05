# Literature review — Synthea and synthetic EHR generation (Block 5)

*Scope: justify the choice of Synthea as the synthetic-EHR substrate for this preprint, honestly document its limitations (especially for medications), situate it against learned alternatives, and acknowledge the general fidelity/utility caveats for synthetic-EHR ML benchmarking. Eight papers retained. Each was verified against the publisher page or PubMed/arXiv — not Google Scholar snippets.*

---

## Motivation and scope

Our preprint uses Synthea-generated FHIR bundles with a small **custom specialty-medication overlay** (long-acting injectables, cyclic regimens, described generically without drug names, PSP-relevant) to compare structured-FHIR RAG against narrative RAG on specialty-medication question answering. The future upgrade path is MIMIC-IV via PhysioNet for a journal submission. Synthea is an appropriate substrate for a **methodological comparison** — both retrievers see the same synthetic ground truth — but the preprint must acknowledge (i) that Synthea's medication realism is known to be weak, (ii) that learned alternatives exist, and (iii) that synthetic EHR benchmarks do not transfer one-to-one to real cohorts. The eight papers below supply each of those defensive claims.

## Canonical Synthea citation

**Walonoski et al. (2018)** remains the single required citation for introducing Synthea. It describes the **Generic Module Framework (GMF)** — clinician-curated state-transition machines that drive a synthetic patient from birth to death — and documents the modules covering the top-ten primary-care encounter reasons and the top-ten chronic morbidities, with output to FHIR, C-CDA, and CSV. Medications are emitted as discrete `MedicationOrder`/`MedicationEnd` events inside these state machines rather than as draws from real prescribing distributions, which foreshadows the realism gap subsequent work identifies. The paper has a 2018 erratum (doi:10.1093/jamia/ocx147) correcting author metadata; both entries are cross-indexed in the bibliography below.

## The medication-module gap, with receipts

The most direct published critique of Synthea's medication output is **Hodges, Tokunaga & LeGrand (2023, *JAMIA Open*)**. Writing as the ONC Synthetic Health Data Challenge winners, they state plainly that "**Synthea's synthetically created medication profiles did not mimic the real world**" and demonstrate this on a pediatric asthma cohort where vanilla Synthea's medication distribution deviates from MEPS national data with χ² = 7168.52 (df = 5, N = 14 410, p < .01) — including the striking result that 100% of simulated pediatric asthma patients received the same inhaler regardless of age. Their Medication Diversification Tool (MDT) overlays MEPS + RxNorm + RxClass distributions on Synthea output and restores realism to χ² = 2.73 (p = .84 vs. MEPS). **This is the single strongest citation for our specialty-medication overlay**: a prior peer-reviewed paper has established both the need for, and the pattern of, layering a medication module on top of Synthea.

**Chen et al. (2019, *BMC MIDM*)** is the canonical independent validity study. Using the 1.2M-patient Massachusetts Synthea cohort, the authors compute four CMS clinical quality measures and find that Synthea models **demographics and service-offering probabilities** reasonably (63% colorectal-screening compliance vs. 69.8–77.3% real) but **underrepresents post-service heterogeneous outcomes**: 0.7% COPD 30-day mortality vs. 7–8% real, 0% hip/knee-replacement complications vs. ~2.8% real, and 0% controlled hypertension vs. ~70–75% real. Their explicit conclusion — that Synthea and similar generators "**do not currently model for deviations in care and the potential outcomes that may result from care deviations**" — lets us honestly bound our claims: Synthea captures encounter/service structure (which is what FHIR vs. narrative RAG actually exercises) well, but not heterogeneous outcomes.

**Meeker et al. (2022, *JAMIA Open*)** is the supporting case report. The authors attempt to reproduce a pediatric-AML levofloxacin-prophylaxis cost-effectiveness study in Synthea and document concrete module-level gaps directly relevant to specialty oncology: Synthea modules "**use models derived from guideline pathways, rather than models that also include alternative or hypothetical pathways, including guideline-discordant pathways**"; transitions at the time supported only uniform distributions; chemotherapy cost and medication data required extensive custom lookup-table editing; and matching a real AML cohort required six module iterations and 22 additional states. This is the strongest published evidence that Synthea's native GMF cannot represent **cyclic chemotherapy, biologic regimens, or non-guideline-concordant specialty prescribing** without custom extension — which is exactly what our overlay does.

**Note on evidence limits (important for honest framing):** no peer-reviewed paper we located specifically critiques Synthea on missing long-acting injectables, missing biologics as a class, or missing prior-authorization patterns. Those claims in the preprint should be framed as "**Synthea's GMF does not natively model X**," citing Hodges 2023 for narrow medication selection and Meeker 2022 for guideline-only pathways, not as "prior work has shown Synthea fails at X." The ONC/HealthIT 2022 final report ("Synthetic Health Data Generation to Accelerate PCOR") and the GitHub issue history (e.g., `synthetichealth/synthea` #236 on pre-FDA-approval prescribing) provide corroborating grey-literature signals but should not be cited in place of peer-reviewed work.

## Learned alternatives a 2026 reader expects to see

Three papers suffice to bracket the learned-generator design space. **Choi et al. (2017, MLHC)** introduced **medGAN** — the foundational GAN-plus-autoencoder architecture for generating high-dimensional discrete patient records with minibatch averaging to avoid mode collapse. Virtually every subsequent learned-EHR-synthesis paper (medBGAN, medWGAN, EMR-WGAN, CorGAN, EHR-Safe, HALO, EHRDiff) benchmarks against or extends medGAN, so it is the natural counterpoint to rule-based Synthea. **Yoon et al. (2023, *npj Digital Medicine*)** introduced **EHR-Safe**, a Google-Cloud sequential encoder–decoder + GAN trained on MIMIC-III and eICU that explicitly handles the real-world messiness Synthea cannot — mixed numerical/categorical features, high sparsity, variable-length time series, and realistic missingness — while passing membership-inference and re-identification attacks. It is the best modern citation for "learned, high-fidelity, privacy-preserving generator" and directly relevant to anyone considering a learned replacement for Synthea in a structured-RAG pipeline.

Two other works are candidates but were not retained to stay within an 8-paper budget: Theodorou, Xiao & Sun's **HALO** (autoregressive LLM-style synthesis, *Nature Communications* 2023) and Baowaly et al.'s **medBGAN/medWGAN** (JAMIA 2019). Cite HALO if a reviewer specifically asks about LLM-based synthesis; cite medBGAN if a reviewer wants a JAMIA alternative. Our scoping citation (Chen et al. 2025, below) already covers both method families.

## Fidelity and transportability caveats for synthetic-EHR ML benchmarking

**Yan et al. (2022, *Nature Communications*)** is the strongest multi-generator benchmark paper. The Vanderbilt–Sage–UW team evaluates five GAN-based generators (medGAN, medBGAN, EMR-WGAN, WGAN, DPGAN) plus a baseline on two large AMC datasets across complementary utility metrics (feature-level similarity, outcome prediction, dimension-wise probability) and privacy metrics (membership inference, attribute inference, meaningful identity disclosure, nearest-neighbor adversarial accuracy). Their headline result — a persistent **utility–privacy Pareto tradeoff** with **no method dominating across all use cases** — is the core caveat any ML-on-synthetic-EHR paper must cite: benchmark rankings are context-dependent and do not transfer across tasks or operating points.

**Chen et al. (2025, *JAMIA*)** is the most recent comprehensive treatment and the paper we need for the distribution-shift caveat. The Michigan–Yale team combines a 48-study scoping review across five method families (rule-based, GAN, VAE, diffusion, LLM-based) with an empirical benchmark of seven open-source generators trained on MIMIC-III and evaluated on **both MIMIC-III and MIMIC-IV** to probe transportability under real distribution shift. They measure fidelity (MMD, RMSPE, discriminative AUC), utility via explicit **TSTR / TRTR / TSRTR gaps**, privacy (membership and attribute inference), and compute cost, and release the `SynthEHRella` toolkit. Two findings matter for our preprint: **rule-based generators (Synthea-style) are strongest on privacy but weaker on fidelity**, and **method rankings shift across evaluation axes and across the MIMIC-III → MIMIC-IV transport**, with a persistent TSTR–TRTR gap. This grounds our narrow claim that synthetic EHR supports **methodological comparison under a matched evaluation** (both RAG variants on the same substrate) but that absolute benchmark numbers are not transportable to real cohorts without caveat — and it motivates the MIMIC-IV upgrade path we flag for the journal submission.

## Conclusion — how these eight papers support the preprint's framing

The bibliography lets the preprint make three narrow, defensible claims. *First*, Synthea is an appropriate, widely cited synthetic-EHR substrate for methodological work (Walonoski 2018), but its medication module is known to deviate from real prescribing distributions (Hodges 2023), relies on guideline-based pathways without deviation modeling (Chen 2019), and lacks native support for complex specialty regimens such as cyclic chemotherapy (Meeker 2022) — together justifying a custom specialty-medication overlay. *Second*, learned alternatives exist and are improving fast (Choi 2017 for the canonical GAN line; Yoon 2023 for modern high-fidelity + privacy-preserving synthesis), and the preprint should acknowledge these as the rational journal-stage upgrade alongside MIMIC-IV. *Third*, any synthetic-EHR benchmark — including ours — must acknowledge the utility–privacy Pareto (Yan 2022) and the TSTR/transportability gap under distribution shift (Chen 2025); our controlled matched comparison is the right way to extract methodological signal from a synthetic substrate despite those gaps.

---

## Bibliography

```bibtex
@article{walonoski2018synthea,
  author  = {Walonoski, Jason and Kramer, Mark and Nichols, Joseph and Quina, Andre and Moesel, Chris and Hall, Dylan and Duffett, Carlton and Dube, Kudakwashe and Gallagher, Thomas and McLachlan, Scott},
  title   = {Synthea: An approach, method, and software mechanism for generating synthetic patients and the synthetic electronic health care record},
  journal = {Journal of the American Medical Informatics Association},
  volume  = {25},
  number  = {3},
  pages   = {230--238},
  year    = {2018},
  month   = {mar},
  doi     = {10.1093/jamia/ocx079},
  pmid    = {29025144},
  pmcid   = {PMC7651916},
  note    = {Erratum in JAMIA 2018;25(7):921, doi:10.1093/jamia/ocx147}
}

@article{hodges2023mdt,
  author  = {Hodges, Robert and Tokunaga, Kristen and LeGrand, Joseph},
  title   = {A novel method to create realistic synthetic medication data},
  journal = {JAMIA Open},
  volume  = {6},
  number  = {3},
  pages   = {ooad052},
  year    = {2023},
  month   = {oct},
  doi     = {10.1093/jamiaopen/ooad052},
  pmcid   = {PMC10343944}
}

@article{chen2019validity,
  author  = {Chen, Junqiao and Chun, David and Patel, Milesh and Chiang, Epson and James, Jesse},
  title   = {The validity of synthetic clinical data: a validation study of a leading synthetic data generator ({Synthea}) using clinical quality measures},
  journal = {BMC Medical Informatics and Decision Making},
  volume  = {19},
  number  = {1},
  pages   = {44},
  year    = {2019},
  doi     = {10.1186/s12911-019-0793-0},
  pmid    = {30871520},
  pmcid   = {PMC6416981}
}

@article{meeker2022synthea,
  author  = {Meeker, Daniella and Kallem, Crystal and Heras, Yan and Garcia, Stephanie and Thompson, Casey},
  title   = {Case report: evaluation of an open-source synthetic data platform for simulation studies},
  journal = {JAMIA Open},
  volume  = {5},
  number  = {3},
  pages   = {ooac067},
  year    = {2022},
  month   = {aug},
  doi     = {10.1093/jamiaopen/ooac067},
  pmid    = {35958672},
  pmcid   = {PMC9360775}
}

@inproceedings{choi2017medgan,
  author        = {Choi, Edward and Biswal, Siddharth and Malin, Bradley and Duke, Jon and Stewart, Walter F. and Sun, Jimeng},
  title         = {Generating Multi-label Discrete Patient Records using Generative Adversarial Networks},
  booktitle     = {Proceedings of the 2nd Machine Learning for Healthcare Conference (MLHC)},
  series        = {Proceedings of Machine Learning Research},
  volume        = {68},
  pages         = {286--305},
  year          = {2017},
  publisher     = {PMLR},
  eprint        = {1703.06490},
  archivePrefix = {arXiv},
  primaryClass  = {cs.LG},
  url           = {https://proceedings.mlr.press/v68/choi17a.html}
}

@article{yoon2023ehrsafe,
  author  = {Yoon, Jinsung and Mizrahi, Michel and Ghalaty, Nahid Farhady and Jarvinen, Thomas and Ravi, Ashwin S. and Brune, Peter and Kong, Fanyu and Anderson, Dave and Lee, George and Meir, Arie and Bandukwala, Farhana and Kanal, Elli and Ar{\i}k, Sercan {\"O}. and Pfister, Tomas},
  title   = {{EHR-Safe}: generating high-fidelity and privacy-preserving synthetic electronic health records},
  journal = {npj Digital Medicine},
  volume  = {6},
  number  = {1},
  pages   = {141},
  year    = {2023},
  doi     = {10.1038/s41746-023-00888-7},
  pmid    = {37567968},
  pmcid   = {PMC10421926}
}

@article{yan2022multifaceted,
  author  = {Yan, Chao and Yan, Yao and Wan, Zhiyu and Zhang, Ziqi and Omberg, Larsson and Guinney, Justin and Mooney, Sean D. and Malin, Bradley A.},
  title   = {A multifaceted benchmarking of synthetic electronic health record generation models},
  journal = {Nature Communications},
  volume  = {13},
  number  = {1},
  pages   = {7609},
  year    = {2022},
  doi     = {10.1038/s41467-022-35295-1},
  pmid    = {36494374},
  pmcid   = {PMC9734113}
}

@article{chen2025scoping,
  author  = {Chen, Xingran and Wu, Zhenke and Shi, Xu and Cho, Hyunghoon and Mukherjee, Bhramar},
  title   = {Generating synthetic electronic health record data: a methodological scoping review with benchmarking on phenotype data and open-source software},
  journal = {Journal of the American Medical Informatics Association},
  volume  = {32},
  number  = {7},
  pages   = {1227--1240},
  year    = {2025},
  doi     = {10.1093/jamia/ocaf082},
  pmid    = {40460023},
  pmcid   = {PMC12203555},
  eprint  = {2411.04281},
  archivePrefix = {arXiv}
}
```

---

## Appendix — candidates considered but cut for the 8-paper budget

- **Theodorou, Xiao & Sun 2023, "HALO," *Nature Communications* 14:5305** (arXiv:2304.02169) — LLM-style autoregressive EHR synthesis at visit + code hierarchy; reach R² > 0.9 on unigram/co-occurrence/temporal-bigram distributions vs. MIMIC-III. Add if a reviewer asks about LLM-based synthesis.
- **Baowaly et al. 2019, medBGAN/medWGAN, *JAMIA* 26(3):228–241** (doi:10.1093/jamia/ocy142) — Wasserstein/boundary-seeking GAN successors to medGAN; useful JAMIA alternative if a journal reviewer prefers a non-arXiv learned-generator citation.
- **Torfi & Fox 2020, "CorGAN,"** FLAIRS-33 (arXiv:2001.09346) — CNN-based extension of medGAN; incremental.
- **ONC/HealthIT 2022, "Synthetic Health Data Generation to Accelerate PCOR: Final Report"** — grey literature; corroborates Chen 2019 and Meeker 2022 on guideline-only limitations.
- **Synthea GitHub issues #236, #578** — anecdotal physician-reported medication-realism problems (e.g., drug prescribed before FDA approval; missing `Medication.amount` population). Grey literature; useful context only.