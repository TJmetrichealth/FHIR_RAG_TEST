# Literature wiki — schema and conventions

This directory is a **maintained wiki**, not a dumping ground. The literature review owns these files; the paper draft reads from them.

## Layers

1. **Raw sources** — not stored in this repo. URLs, DOIs, arXiv IDs, and PDFs live in the outside world. This directory only stores our synthesis.
2. **Topic pages** — one markdown file per Block from [`../02_LITERATURE_REVIEW_QUERIES.md`](../02_LITERATURE_REVIEW_QUERIES.md). Annotated bibliography + a short framing argument for the paper.
3. **Index and log** — [`index.md`](index.md) (content-oriented catalog) and [`log.md`](log.md) (append-only chronological record).

## File naming

- Topic pages use lowercase snake_case names keyed to the block's topic, not its number: `clinical_rag.md`, `retrieval_strategies.md`, `synthea.md`. One existing exception with a space (`block 11 adherance.md`) is preserved as-is to avoid breaking links already drafted in the paper.
- The bibliography BibTeX file is [`bibliography.bib`](bibliography.bib). Every paper cited in a topic page must have a BibTeX entry there.

## Topic page shape

A topic page should have, in order:

1. **Title** (`# Block N — <topic>` or `# <topic> (Block N)`).
2. **Scope / bottom line** — one paragraph. What this page defends, and what the headline finding is.
3. **Papers** — 3–8 entries. Each entry has: citation (authors, year, venue, arXiv/DOI), 2–3 sentence summary in our own words, one-line "relevance to us" framing. No bullet dumps of abstracts.
4. **Gap analysis** — one paragraph stating explicitly what is *not* covered by the prior art and why our contribution survives. This is the payload that the Related Work section pulls from.
5. **Cross-links** — wikilink style `[[topic_name]]` or markdown `[topic](topic.md)` to adjacent topic pages when a paper is relevant across blocks.

Do not add YAML frontmatter to topic pages. Keep them plain markdown so spans can be pulled verbatim into the paper without stripping metadata.

## Ingest protocol (when a new source arrives)

When the user hands you a paper, preprint, or article:

1. **Verify it.** Fetch the canonical URL (publisher, arXiv, PMC). Confirm title, authors, year, venue. Never cite a paper you haven't read at least the abstract of.
2. **Place it.** Decide which existing topic page it belongs on. If it belongs on two, place on the primary and cross-link from the secondary.
3. **Write the entry** using the topic-page shape above. If it displaces or contradicts an existing entry, update the affected entries in the same pass — don't leave the contradiction unflagged.
4. **Update the gap-analysis paragraph** if the new source shrinks or shifts the gap. This is the step that is easy to skip; do not skip it.
5. **Update [`index.md`](index.md)** — bump the paper count on the affected topic line if the count is tracked there.
6. **Append to [`log.md`](log.md)** with the prefix `## [YYYY-MM-DD] ingest | <short title>` so `grep "^## \[" log.md` stays parseable.
7. **Add a BibTeX entry** to [`bibliography.bib`](bibliography.bib) if the paper will be cited in the preprint.

## Query protocol (when the user asks a lit-review question)

1. Read [`index.md`](index.md) first. Identify the 1–3 topic pages most likely to hold the answer.
2. Read those pages fully before searching the web.
3. Only after the wiki is exhausted, do new web searches. New findings flow back in via the ingest protocol — do not let query answers disappear into chat history.
4. If a query produces a non-trivial synthesis (comparison table, threat analysis, new gap claim), file it back into the relevant topic page or as a new topic page. Append a `query` entry to the log.

## Lint protocol (run on request, and before paper drafting)

Check for:
- **Stale claims** — a topic page says "no prior work does X" but a newer entry on another page contradicts it.
- **Orphan pages** — topic pages not listed in `index.md`, or pages with no inbound cross-links from any sibling.
- **Missing BibTeX** — papers cited in prose without a matching entry in `bibliography.bib`.
- **Duplicate entries** — the same paper summarized on two pages with divergent framings.
- **Count drift** — a topic page claims "8 papers retained" but actually lists 7 or 9.

Report findings as an `## [YYYY-MM-DD] lint | <scope>` entry in `log.md` with a checklist of fixes. Do not silently apply the fixes — surface them to the user first.

## What this wiki is NOT

- Not a source of evaluation signal. Retrieval-system evaluation is scored against programmatic ground truth, never against claims in this directory.
- Not a place for results. Experimental numbers live in `results/` and `analysis/`.
- Not a general project journal. Project decisions go in [`../decisions.md`](../decisions.md); project status in [`../00_PROJECT_PLAN.md`](../00_PROJECT_PLAN.md).
