# Literature wiki — log

Append-only chronological record. One entry per ingest, query-with-synthesis, or lint pass. Entry prefix: `## [YYYY-MM-DD] <kind> | <short title>`. Kinds: `ingest`, `query`, `lint`, `bootstrap`.

To grep recent entries: `grep "^## \[" docs/literature/log.md | tail -20`.

---

## [2026-04-21] bootstrap | wiki scaffolding initialized

Converted the `docs/literature/` directory into a maintained wiki.

- Added [`_WIKI_SCHEMA.md`](_WIKI_SCHEMA.md) (conventions, ingest/query/lint protocols).
- Added [`index.md`](index.md) cataloguing the 11 existing topic pages plus the cross-cutting `clinical_temporal.md`.
- Added this file.
- Existing topic pages were catalogued but not rewritten. They do not yet conform fully to the topic-page shape (most have the bottom-line and papers sections; some are missing an explicit gap-analysis heading). Conformance will accrue lazily — next time a page is touched for ingest, bring it into shape.
- Block 4 has no dedicated topic page; noted in `index.md`.
- Updated `.claude/agents/researcher.md` to point at the ingest/query/lint protocols so future researcher invocations follow them without being re-prompted.

Not changed: existing topic pages, `bibliography.bib`, `docs/02_LITERATURE_REVIEW_QUERIES.md`, any project code.

## [2026-05-08] ingest | BibTeX stub verification — walonoski2018synthea, hodges2023medication, meeker2022synthea

Verified and completed three stub BibTeX entries in `paper/refs.bib` flagged by the Phase 9 reviewer. No new topic-page entries required; these papers are already summarised in `synthea.md`.

- **walonoski2018synthea** (DOI 10.1093/jamia/ocx079): Corrected author list from a partially-reconstructed stub (Twyman, Bouley et al.) to the verified 10-author list (Walonoski, Kramer, Nichols, Quina, Moesel, Hall, Duffett, Dube, Gallagher, McLachlan). Verified against OUP publisher page and PubMed PMID 29025144.
- **hodges2023medication** (DOI 10.1093/jamiaopen/ooad052): Title corrected from "Diversifying Synthea's Medication Module..." to "A novel method to create realistic synthetic medication data"; author first names corrected (Robert Hodges, Kristen Tokunaga, Joseph LeGrand); volume/issue/pages/DOI added (JAMIA Open 6(3):ooad052). Verified via OUP and PubMed PMID 37457749.
- **meeker2022synthea** (DOI 10.1093/jamiaopen/ooac067): Author replaced from placeholder "Meeker, Cathy and others" to full 5-author list (Meeker, Daniella; Kallem, Crystal; Heras, Yan; Garcia, Stephanie; Thompson, Casey); title corrected from AML/Synthea fabrication to actual title "Case report: evaluation of an open-source synthetic data platform for simulation studies"; volume/issue/pages/DOI added (JAMIA Open 5(3):ooac067). Verified via OUP and PubMed PMID 35958672.

`paper/TODO.md` items 1, 5, 6, 15, 16, 17 marked DONE. Checklist rows updated.

## [pre-2026-04-21] ingest | Blocks 1–11 (historical, retroactively logged)

The 11 topic pages under `docs/literature/` were produced during Week 1 by the `researcher` agent against [`../02_LITERATURE_REVIEW_QUERIES.md`](../02_LITERATURE_REVIEW_QUERIES.md). Individual ingest entries were not logged at the time; this composite entry stands in for that history. Going forward every ingest gets its own entry.
