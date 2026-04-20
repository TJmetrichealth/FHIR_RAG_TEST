"""Generate one LLM narrative per enhanced FHIR bundle via Groq (Llama 3.3 70B).

Reads data/fhir_bundles/_regimen_index.json to get tier + dose events +
reference pointers. Sends a fixed prompt at temperature 0. Writes:
  narratives/llm_narratives/<patient_id>.txt
  narratives/llm_narratives/<patient_id>.meta.json  (model, prompt hash, tokens, latency, cache_hit)

Usage:
  GROQ_API_KEY=... python -m narratives.gen_llm_narrative \
      --bundles data/fhir_bundles \
      --output narratives/llm_narratives [--sample N] [--model llama-3.3-70b-versatile]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from systems.common.groq_client import GroqClient

from .prompts import (
    LLM_NARRATIVE_SYSTEM_PROMPT_V1,
    LLM_NARRATIVE_USER_PROMPT_V1,
    prompt_version_hash,
)


DEFAULT_MODEL = "llama-3.3-70b-versatile"


def _regimen_payload(meta: dict[str, Any]) -> dict[str, Any]:
    # Build a compact payload that the LLM can render into prose.
    components = []
    for comp in meta["components"]:
        events = comp.get("dose_event_dates") or []
        summary = {
            "component_id": comp["component_id"],
            "descriptor": comp["descriptor"],
            "schedule_kind": comp["schedule_kind"],
            "interval_days": comp.get("interval_days"),
            "cycle_on_weeks": comp.get("cycle_on_weeks"),
            "cycle_off_weeks": comp.get("cycle_off_weeks"),
            "prn_indication": comp.get("prn_indication"),
            "n_administrations": len(events),
            "first_administrations": events[:3],
            "last_administrations": events[-3:] if len(events) > 3 else [],
        }
        components.append(summary)
    return {
        "patient_id": meta["patient_id"],
        "tier": meta["tier"],
        "tier_label": meta["tier_label"],
        "tier_description": meta["tier_description"],
        "regimen_start": meta["regimen_start"],
        "regimen_end": meta["regimen_end"],
        "horizon_days": meta["horizon_days"],
        "components": components,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundles", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=1200)
    parser.add_argument("--sample", type=int, default=0)
    args = parser.parse_args(argv)

    args.output.mkdir(parents=True, exist_ok=True)
    index_path = args.bundles / "_regimen_index.json"
    if not index_path.exists():
        print(f"Missing regimen index: {index_path}", file=sys.stderr)
        return 2

    index = json.loads(index_path.read_text())
    patients = list(index["patients"].values())
    if args.sample > 0:
        patients = patients[: args.sample]

    client = GroqClient(model=args.model)
    prompt_hash = prompt_version_hash()
    produced = 0
    cache_hits = 0
    errors: list[str] = []

    for meta in patients:
        pid = meta["patient_id"]
        user_prompt = LLM_NARRATIVE_USER_PROMPT_V1.format(
            regimen_json=json.dumps(_regimen_payload(meta), indent=2, sort_keys=True)
        )
        try:
            result = client.complete(
                prompt=user_prompt,
                system=LLM_NARRATIVE_SYSTEM_PROMPT_V1,
                temperature=args.temperature,
                max_tokens=args.max_tokens,
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{pid}: {exc}")
            continue

        narrative_path = args.output / f"{pid}.txt"
        narrative_path.write_text(result.text + "\n")

        meta_out = {
            "patient_id": pid,
            "model": args.model,
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
            "prompt_version": prompt_hash,
            "tokens_in": result.tokens_in,
            "tokens_out": result.tokens_out,
            "latency_ms": round(result.latency_ms, 2),
            "cache_hit": result.cache_hit,
            "prompt_sha256": result.prompt_sha256,
        }
        (args.output / f"{pid}.meta.json").write_text(
            json.dumps(meta_out, indent=2, sort_keys=True)
        )
        produced += 1
        cache_hits += int(result.cache_hit)

    print(
        f"narratives: produced={produced}/{len(patients)} cache_hits={cache_hits} "
        f"errors={len(errors)} model={args.model} prompt_version={prompt_hash}"
    )
    if errors:
        print("first errors:", file=sys.stderr)
        for e in errors[:5]:
            print(f"  {e}", file=sys.stderr)
    return 0 if not errors or produced > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
