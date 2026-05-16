"""Templated-narrative QA arm (reviewer revision #1, System A-T).

Goal: disambiguate "narrative format wins" from "LLM-generated narratives
win." Runs the same System A pipeline against deterministic templated
narratives (200 .txt files under narratives/templated_narratives/) instead
of LLM-generated narratives, scores the result against the same 13,800
questions, and produces a paired delta against the canonical System A.

Sample: all 13,800 questions (matches the canonical evaluation).

Cache isolation: routes through ``eval/cache_templated/answers/`` so the
canonical answer cache stays untouched and the live-call cost is
computable from this directory alone. The existing cache key already
includes the user prompt (which contains the retrieved context), so
different narrative text would produce different cache keys anyway, but
the directory split makes accounting explicit.

Chroma isolation: a fresh per-patient Chroma collection tree under
``systems/system_a_templated/chroma/`` so the canonical
``systems/system_a/chroma/`` is untouched.

Output: ``results/raw_templated/a_templated.jsonl`` (same schema as
``results/raw_large/a.jsonl``).

Usage::

    python scripts/run_templated_arm.py [--concurrency 4]

Environment: requires GROQ_API_KEY with Developer-plan access.
Expected cost: ~$4-5 USD given System A's mean of 490 tokens-in (parallels
canonical System A live-call cost of $4.74). Wall time: ~17-30 minutes at
800 RPM throttle, plus 5-10 minutes for one-time BGE re-embedding of all
200 templated narratives.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

QUESTIONS_PATH = ROOT / "questions" / "questions.jsonl"
OUTPUT_DIR = ROOT / "results" / "raw_templated"
CACHE_DIR_TEMPLATED = ROOT / "eval" / "cache_templated" / "answers"
CHROMA_BASE_TEMPLATED = ROOT / "systems" / "system_a_templated" / "chroma"
TEMPLATED_NARRATIVES_DIR = ROOT / "narratives" / "templated_narratives"


def patch_cache_dir() -> None:
    """Monkey-patch the answer-LLM cache dir to the templated-arm bucket.

    Must run BEFORE the systems package is imported so the GroqClient's
    cache uses the new dir. Mirrors ``scripts.token_sweep_1024.patch_for_1024``.
    """
    import systems.common.answer_llm as al

    al.ANSWER_CACHE_DIR = CACHE_DIR_TEMPLATED
    al._clients.clear()
    print(f"[templated] patched ANSWER_CACHE_DIR={al.ANSWER_CACHE_DIR}", flush=True)


def load_questions() -> list[dict[str, Any]]:
    """Load all 13,800 questions, sorted deterministically by id."""
    out: list[dict[str, Any]] = []
    with open(QUESTIONS_PATH, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    out.sort(key=lambda q: q["id"])
    return out


def run(concurrency: int) -> None:
    patch_cache_dir()

    from systems.narrative_rag import NarrativeRAG  # noqa: E402

    system = NarrativeRAG(
        narratives_dir=TEMPLATED_NARRATIVES_DIR,
        chroma_base=CHROMA_BASE_TEMPLATED,
        name="system_a_templated",
    )
    sample = load_questions()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "a_templated.jsonl"

    # Resume support: skip question_ids already written.
    done_ids: set[str] = set()
    if out_path.exists():
        with open(out_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    done_ids.add(json.loads(line)["question_id"])
                except (KeyError, json.JSONDecodeError):
                    pass

    remaining = [q for q in sample if q["id"] not in done_ids]
    if done_ids:
        print(
            f"[templated] resuming: {len(done_ids)} already done, "
            f"{len(remaining)} remaining",
            flush=True,
        )
    print(
        f"[templated] sample={len(sample)}, remaining={len(remaining)}, "
        f"concurrency={concurrency}",
        flush=True,
    )
    if not remaining:
        print("[templated] nothing to do.", flush=True)
        return

    import threading
    from concurrent.futures import ThreadPoolExecutor, as_completed

    write_lock = threading.Lock()
    counter = {"n": 0}
    n_total = len(remaining)
    t_start = time.perf_counter()

    def answer_one(q: dict[str, Any]) -> dict[str, Any]:
        t0 = time.perf_counter()
        try:
            resp = system.answer(q["question"], q["patient_id"])
            return {
                "question_id": q["id"],
                "patient_id": q["patient_id"],
                "question": q["question"],
                "question_type": q["type"],
                "tier": q.get("tier"),
                "reference_date": q.get("reference_date"),
                "ground_truth": q.get("ground_truth"),
                "system": system.name,
                "answer": resp.answer,
                "retrieved": resp.retrieved,
                "tokens_in": resp.tokens_in,
                "tokens_out": resp.tokens_out,
                "latency_ms": resp.latency_ms,
                "extras": resp.extras,
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "question_id": q["id"],
                "patient_id": q["patient_id"],
                "system": system.name,
                "error": str(exc),
                "latency_ms": (time.perf_counter() - t0) * 1000.0,
            }

    def write_record(record: dict[str, Any], fh: Any) -> None:
        with write_lock:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            fh.flush()
            counter["n"] += 1
            n = counter["n"]
            if n == 1 or n % 25 == 0 or n == n_total:
                elapsed = time.perf_counter() - t_start
                rate = n / max(elapsed, 1e-6)
                eta = (n_total - n) / max(rate, 1e-6)
                print(
                    f"[templated] {n}/{n_total} done "
                    f"({elapsed:.0f}s elapsed, ~{eta:.0f}s remaining)",
                    flush=True,
                )

    with open(out_path, "a", encoding="utf-8") as fh:
        if concurrency == 1:
            for q in remaining:
                rec = answer_one(q)
                write_record(rec, fh)
        else:
            with ThreadPoolExecutor(
                max_workers=concurrency, thread_name_prefix="templated"
            ) as ex:
                futures = [ex.submit(answer_one, q) for q in remaining]
                for fut in as_completed(futures):
                    rec = fut.result()
                    write_record(rec, fh)

    elapsed = time.perf_counter() - t_start
    print(
        f"[templated] done in {elapsed:.0f}s; wrote {counter['n']} records to {out_path}",
        flush=True,
    )


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--concurrency",
        type=int,
        default=4,
        help="in-flight system.answer calls (default 4, matches token_sweep_1024)",
    )
    args = p.parse_args()
    if args.concurrency < 1:
        print("concurrency must be >= 1", file=sys.stderr)
        sys.exit(2)
    run(args.concurrency)


if __name__ == "__main__":
    main()
