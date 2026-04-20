"""Deterministic templated-narrative generator.

Renders the regimen metadata for each patient into prose via Jinja2 — no LLM.
This is the ablation ceiling (maximum fidelity by construction) and the
fallback if the LLM narratives fail the 90% gate (Risk R1).

Usage:
  python -m narratives.gen_templated_narrative \
      --bundles data/fhir_bundles \
      --output narratives/templated_narratives [--sample N]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from jinja2 import Environment


TEMPLATE = """\
The patient follows a {{ tier_description }}  This regimen (tier {{ tier }}) is
labelled {{ tier_label }} and runs from {{ regimen_start }} to {{ regimen_end }}
({{ horizon_days }} days).

{% for c in components -%}
Component {{ c.component_id }} is {{ c.descriptor }}.
{%- if c.schedule_kind == "fixed_interval" %}
 It is administered on a fixed interval of every {{ c.interval_days }} day{{ "s" if c.interval_days != 1 else "" }}.
{%- elif c.schedule_kind == "cyclic" %}
 It follows a cyclic schedule of {{ c.cycle_on_weeks }} weeks on and {{ c.cycle_off_weeks }} weeks off.
{%- elif c.schedule_kind == "prn" %}
 It is taken as needed (PRN){% if c.prn_indication %} for {{ c.prn_indication }}{% endif %}.
{%- endif %}

{% if c.dose_event_dates %}\
A total of {{ c.dose_event_dates|length }} administration{{ "s" if c.dose_event_dates|length != 1 else "" }} are recorded, starting on {{ c.dose_event_dates[0] }} and ending on {{ c.dose_event_dates[-1] }}.
{%- if c.dose_event_dates|length > 6 %} The first three dates are {{ c.dose_event_dates[:3]|join(", ") }}; the last three are {{ c.dose_event_dates[-3:]|join(", ") }}.
{%- endif %}
{% else %}
No administrations are recorded for this component in the observation window.
{% endif %}

{% endfor %}
"""


def render(meta: dict[str, Any]) -> str:
    env = Environment(autoescape=False, trim_blocks=False, lstrip_blocks=False)
    template = env.from_string(TEMPLATE)
    return template.render(**meta)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundles", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--sample", type=int, default=0)
    args = parser.parse_args(argv)

    args.output.mkdir(parents=True, exist_ok=True)
    index = json.loads((args.bundles / "_regimen_index.json").read_text())
    patients = list(index["patients"].values())
    if args.sample > 0:
        patients = patients[: args.sample]

    produced = 0
    for meta in patients:
        text = render(meta)
        (args.output / f"{meta['patient_id']}.txt").write_text(text.strip() + "\n")
        produced += 1

    print(f"templated: produced={produced} output_dir={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
