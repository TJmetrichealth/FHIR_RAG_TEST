# paper/TODO.md
# Append-only list of uncertainties, citation gaps, stub sections,
# and anything requiring researcher or reviewer follow-up before arXiv submission.
#
# REVISION PASS 2026-05-08: items 2, 3, 4, 8 CLEARED.
# Items 1, 5, 6, 7, 9-15 remain open. See notes below.

---

## 1. Citation Gaps — Partially Resolved

### CLEARED
2. **Fleming et al. 2024 (MedAlign)** — BibTeX entry `fleming2024medalign` added to
   refs.bib and `\citep{fleming2024medalign}` inserted in `02_related_work.tex`.

3. **Yuan et al. 2023 (BioNLP temporal)** — BibTeX entry `yuan2023zeroshot` added to
   refs.bib and `\citep{yuan2023zeroshot}` inserted in `02_related_work.tex`.

4. **Cui et al. 2025 (TIMER)** — BibTeX entry `cui2025timer` added to refs.bib and
   `\citep{cui2025timer}` inserted in `02_related_work.tex`.

### STILL OPEN

1. **Walonoski et al. 2018 (Synthea)** — DONE (2026-05-08). Full author list verified
   against OUP publisher page https://academic.oup.com/jamia/article/25/3/230/4098271
   and PubMed PMID 29025144. Updated in refs.bib: Walonoski, Kramer, Nichols, Quina,
   Moesel, Hall, Duffett, Dube, Gallagher, McLachlan. DOI 10.1093/jamia/ocx079
   confirmed resolving.

---

## 2. Stub BibTeX Entries Requiring Completion

5. **hodges2023medication** — DONE (2026-05-08). Title corrected to "A novel method
   to create realistic synthetic medication data". Authors: Hodges, Robert; Tokunaga,
   Kristen; LeGrand, Joseph. JAMIA Open 6(3):ooad052, 2023.
   DOI 10.1093/jamiaopen/ooad052 verified at OUP and PubMed PMID 37457749.

6. **meeker2022synthea** — DONE (2026-05-08). Title corrected to "Case report:
   evaluation of an open-source synthetic data platform for simulation studies".
   Authors: Meeker, Daniella; Kallem, Crystal; Heras, Yan; Garcia, Stephanie;
   Thompson, Casey. JAMIA Open 5(3):ooac067, 2022.
   DOI 10.1093/jamiaopen/ooac067 verified at OUP and PubMed PMID 35958672.

---

## 3. Numbers Asserted Without Explicit Source File Citation

7. **"approximately 250 to 350" per-cell question count** (Limitations section) —
   derived by the writer from 200 patients × 5 families × 3 tiers / (number of templates
   per cell). Verify against `results/recall_at_k_w2_smoke.csv` or recompute from
   `questions/questions.jsonl` cell counts.

8. CLEARED — **"templated-narrative ablation also showed A > B > C"** overclaim
   was REMOVED in this revision pass. The Limitations section now honestly states:
   "A downstream QA evaluation against the templated narratives was planned ... but
   that evaluation was not completed within the results-freeze timeline."

9. **"Tier distribution 63 / 63 / 74"** (Methods section) — sourced from
   `reports/fidelity_audit_llm.md` per-tier breakdown. Cross-check against patient
   manifest in `data/fhir_bundles/`.

---

## 4. Stub or Under-developed Sections

10. **Figures in Section 4** — the accuracy heatmap (`accuracy_heatmap.png`) and
    partial_vs_exact scatter (`partial_vs_exact.png`) and recall_at_k curve
    (`recall_at_k_curve.png`) are confirmed to exist in `figures/` but are not included
    in the paper body. Consider adding at least the heatmap as a supplementary figure
    before full-venue submission.

11. **Appendix sections** — the methods section references `Appendix A.6` (sensitivity
    sweep) which was not completed within Week 3. Either remove this reference or add
    an appendix placeholder noting the sweep is deferred to the full venue version.
    Appendices A.1–A.5 and A.7–A.8 are mentioned in the draft structure but not written.
    These should be added before arXiv submission.

---

## 5. Guesses / Assumptions Made by the Writer

12. **Tier-2 positive-label interpretation** (Results §7.6): the writer inferred from
    `analysis/feature_extraction.md` that "all 29 positives are Tier-2" — this is
    stated explicitly in that file and should be correct. Verify programmatically.

13. **"Cost modestly exceeded the \$20 ceiling for B alone"** (Methods §API disclosure)
    — the total \$32.68 is sourced from `analysis/latency_tokens.md`. The single-system
    ceiling was \$20; B alone was \$21.07, which exceeds the ceiling. Decision log entry
    2026-05-06 should be verified for exact wording.

14. **"A templated narrative ablation was run"** — FIXED in this revision. The sentence
    now qualifies that only the fidelity audit (100% entity recall) is verified; the
    downstream QA eval is deferred.

---

## 6. Pre-submission Citation Verification (added 2026-05-08)

15. **hodges2023medication** — DONE (2026-05-08). See item 5 above. DOI 10.1093/jamiaopen/ooad052.

16. **meeker2022synthea** — DONE (2026-05-08). See item 6 above. DOI 10.1093/jamiaopen/ooac067.

17. **walonoski2018synthea** — DONE (2026-05-08). See item 1 above. DOI 10.1093/jamia/ocx079.

---

## 7. Pre-submission Checklist Items

- [x] Replace [CITATION NEEDED] in 02_related_work.tex (DONE — 2026-05-08 revision pass)
- [x] Fix templated-ablation overclaim in 06_limitations.tex (DONE — 2026-05-08)
- [x] Strip em dashes and bullet-to-prose conversions (DONE — 2026-05-08)
- [x] Fix "500-character" → "512-token" throughout (DONE — 2026-05-08 S1.1)
- [x] Fix "Four-category" → "Five-category" taxonomy claim (DONE — 2026-05-08 S1.2)
- [x] Remove dangling Appendix~A.6 and sec:appendix:repro references (DONE — 2026-05-08 S2.1)
- [x] Hedge abstract FS-Structured AUC claim (DONE — 2026-05-08 S2.2)
- [x] Fix context-reduction percentage 54% → 51% (DONE — 2026-05-08 S2.3)
- [x] Remove fabricated "MEME" acronym (DONE — 2026-05-08 S2.4)
- [x] Fix model ID qwen-3-32b → qwen/qwen3-32b (DONE — 2026-05-08 S2.5)
- [x] Clean stub BibTeX NOTE/Stub comments (DONE — 2026-05-08 S2.6/S2.7)
- [x] Fix LLM triangulation claim in limitations (DONE — 2026-05-08 S3.1)
- [x] Append ANSWER_MAX_TOKENS=512 decision log entry (DONE — 2026-05-08 S3.2)
- [x] Append duplicate O6 note to decision log (DONE — 2026-05-08 S3.3)
- [x] Add results-freeze-v1 commit SHA to reproducibility (DONE — 2026-05-08 S3.4)
- [x] Resolve citation gap 1 (Walonoski author list — item 1, TODO §6 item 17) (DONE 2026-05-08)
- [x] Complete stub BibTeX entries hodges2023medication and meeker2022synthea with DOIs (TODO §6 items 15--16) (DONE 2026-05-08)
- [ ] Verify per-cell N count (item 7)
- [ ] Add appendix sections or placeholder notes
- [ ] Run LaTeX (pdflatex + bibtex) to confirm no undefined references or overfull hboxes
- [ ] Confirm all figures in `paper/sections/*.tex` resolve to existing PNGs in `figures/`
- [ ] Verify abstract word count (~200 words target)
- [ ] Confirm abstract does NOT mention metricHEALTH (R16 mitigation — currently clean)
- [ ] Reviewer pass (read-only) before arXiv submission per governance §11
- [ ] Employer IP clearance for CC-BY-4.0 dataset licence (decision B4 pending)
- [ ] Thesis-chapter scaffold `thesis_chapter/phase_0.md` consistent with paper numbers
