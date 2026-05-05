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

## [pre-2026-04-21] ingest | Blocks 1–11 (historical, retroactively logged)

The 11 topic pages under `docs/literature/` were produced during Week 1 by the `researcher` agent against [`../02_LITERATURE_REVIEW_QUERIES.md`](../02_LITERATURE_REVIEW_QUERIES.md). Individual ingest entries were not logged at the time; this composite entry stands in for that history. Going forward every ingest gets its own entry.
