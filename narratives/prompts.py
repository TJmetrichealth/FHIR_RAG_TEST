"""Fixed prompt templates for narrative generation.

All prompts are pinned and hashed. Any change requires a new entry in
docs/decisions.md and a new prompt version number — the fidelity audit
records which prompt version generated each narrative.
"""
from __future__ import annotations

import hashlib


LLM_NARRATIVE_SYSTEM_PROMPT_V1 = (
    "You are a clinical documentation assistant. You convert structured FHIR "
    "medication and care-plan data into a concise, factually faithful clinical "
    "narrative. Output only the narrative prose — no lists, no markdown, no "
    "preamble. Preserve every medication descriptor, every dose event date, "
    "every cycle/interval, and every PRN indication verbatim where they appear "
    "in the source data. Do not introduce clinical details that are not "
    "supported by the source."
)


LLM_NARRATIVE_USER_PROMPT_V1 = """\
Convert the following FHIR regimen data for one patient into a clinical narrative
of 3–6 short paragraphs. The narrative must:

1. State the patient's specialty-regimen tier and its overall description.
2. List each medication component with its route and schedule (fixed interval,
   cyclic, or PRN), including the exact interval in days where applicable.
3. Give the regimen start date and the end of the projected horizon.
4. Mention each dose administration date in ISO format (YYYY-MM-DD), grouped
   by component. For each component include the first three administration dates,
   the last three administration dates, the total count, and — if the component
   has seven or more administrations — at least one date from the middle of the
   regimen window (i.e., from the middle third of the administration timeline,
   between the earliest and latest recorded dates). The field "mid_administration"
   in the JSON supplies a representative mid-window date; use it verbatim when
   present. For components with fewer than seven administrations the first-three
   and last-three already cover the full timeline, so no additional mid-window
   date is required.
5. If any component is PRN, state the indication ("as needed for ...") and
   whether any PRN administrations were recorded.

Do not mention anything outside the structured data below.

----- STRUCTURED REGIMEN DATA (JSON) -----
{regimen_json}
------------------------------------------

Write the narrative now.
"""


def prompt_version_hash() -> str:
    blob = (LLM_NARRATIVE_SYSTEM_PROMPT_V1 + "\n\n" + LLM_NARRATIVE_USER_PROMPT_V1).encode(
        "utf-8"
    )
    return hashlib.sha256(blob).hexdigest()[:12]
