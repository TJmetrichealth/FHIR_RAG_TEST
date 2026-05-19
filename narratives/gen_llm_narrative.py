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
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()  # must happen before GroqClient reads GROQ_API_KEY from env

from systems.common.groq_client import GroqClient

from .prompts import (
    LLM_NARRATIVE_SYSTEM_PROMPT_V1,
    LLM_NARRATIVE_USER_PROMPT_V1,
    prompt_version_hash,
)


DEFAULT_MODEL = "llama-3.3-70b-versatile"

# Pinned prompt hash for the v1 LLM-narrative prompt.
# If you edit either prompt string in prompts.py you MUST also update this
# constant — or the generator will fail fast before any API calls are made.
# To regenerate: python -c "from narratives.prompts import prompt_version_hash; print(prompt_version_hash())"
PINNED_PROMPT_HASH = "518bc71d87b7"

_actual_hash = prompt_version_hash()
if _actual_hash != PINNED_PROMPT_HASH:
    raise RuntimeError(
        f"Prompt hash mismatch: pinned={PINNED_PROMPT_HASH!r}, actual={_actual_hash!r}. "
        "The LLM-narrative prompt has been edited without updating PINNED_PROMPT_HASH. "
        "Either revert your prompt changes, or deliberately bump PINNED_PROMPT_HASH "
        "and tag a new release documenting the new prompt version."
    )


def _mid_administration(events: list[str]) -> str | None:
    """Return the median-indexed administration date for mid-window coverage.

    The audit checks admin_dates[len(admin_dates)//2].  We surface that exact
    date so the LLM can include it verbatim.  Returns None when the list is
    short enough that first-three / last-three already cover every date
    (i.e., fewer than 7 events).
    """
    if len(events) < 7:
        return None
    return events[len(events) // 2]


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
            "mid_administration": _mid_administration(events),
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
    skipped = 0
    cache_hits = 0
    errors: list[str] = []
    total = len(patients)
    run_start = time.monotonic()

    print(
        f"[{datetime.utcnow().isoformat(timespec='seconds')}Z] "
        f"Starting narrative generation: {total} patients, "
        f"model={args.model}, temperature={args.temperature}, "
        f"prompt_version={prompt_hash}"
    )

    for idx, meta in enumerate(patients, 1):
        pid = meta["patient_id"]
        narrative_path = args.output / f"{pid}.txt"

        # Resumability: skip if narrative already written to disk
        if narrative_path.exists():
            skipped += 1
            if idx % 20 == 0 or idx == total:
                print(
                    f"[{datetime.utcnow().isoformat(timespec='seconds')}Z] "
                    f"  {idx}/{total} skipped={skipped} produced={produced} errors={len(errors)}"
                )
            continue

        user_prompt = LLM_NARRATIVE_USER_PROMPT_V1.format(
            regimen_json=json.dumps(_regimen_payload(meta), indent=2, sort_keys=True)
        )
        t0 = time.monotonic()
        try:
            result = client.complete(
                prompt=user_prompt,
                system=LLM_NARRATIVE_SYSTEM_PROMPT_V1,
                temperature=args.temperature,
                max_tokens=args.max_tokens,
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{pid}: {exc}")
            print(
                f"[{datetime.utcnow().isoformat(timespec='seconds')}Z] "
                f"  ERROR {idx}/{total} pid={pid}: {exc}",
                file=sys.stderr,
            )
            continue

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

        elapsed = time.monotonic() - run_start
        rate = produced / elapsed if elapsed > 0 else 0
        eta_s = (total - idx) / rate if rate > 0 else 0
        print(
            f"[{datetime.utcnow().isoformat(timespec='seconds')}Z] "
            f"  {idx}/{total} pid={pid} "
            f"tok_in={result.tokens_in} tok_out={result.tokens_out} "
            f"latency={result.latency_ms:.0f}ms cache={result.cache_hit} "
            f"rate={rate:.2f}/s eta={eta_s/60:.1f}min"
        )

    elapsed_total = time.monotonic() - run_start
    print(
        f"[{datetime.utcnow().isoformat(timespec='seconds')}Z] "
        f"DONE: produced={produced} skipped={skipped} cache_hits={cache_hits} "
        f"errors={len(errors)} elapsed={elapsed_total:.1f}s "
        f"model={args.model} prompt_version={prompt_hash}"
    )
    if errors:
        print("Errors encountered:", file=sys.stderr)
        for e in errors[:10]:
            print(f"  {e}", file=sys.stderr)
    return 0 if not errors or produced > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
