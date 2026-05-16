"""No-retrieval baseline arm (reviewer revision #3, System N).

Goal: decompose absolute QA accuracy into a "question-text-attributable"
floor (this system, no patient context) and a "retrieval-attributable"
remainder (Systems A/B/C minus this). The reviewer correctly notes that
without this baseline, we cannot say how much of System A's 40.6%
accuracy comes from qwen3-32b's priors on question text alone.

Sample: all 13,800 questions.

Cache isolation: routes through ``eval/cache_noretrieval/answers/``. The
existing cache key includes the user prompt (which here has an empty
context block), so it does not collide with A/B/C cache entries, but the
directory split makes cost accounting explicit.

Output: ``results/raw_noretrieval/n.jsonl`` (same schema as
``results/raw_large/a.jsonl``).

Usage::

    python scripts/run_no_retrieval_arm.py [--concurrency 4]

Expected cost: ~$0.30-0.50 USD (no retrieved context to embed in the
prompt, so the input-token payload is minimal: just the system prompt and
the question text). Wall time: ~5-15 minutes.
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
OUTPUT_DIR = ROOT / "results" / "raw_noretrieval"
CACHE_DIR_NORETRIEVAL = ROOT / "eval" / "cache_noretrieval" / "answers"


def patch_cache_dir() -> None:
    import systems.common.answer_llm as al

    al.ANSWER_CACHE_DIR = CACHE_DIR_NORETRIEVAL
    al._clients.clear()
    print(f"[noretrieval] patched ANSWER_CACHE_DIR={al.ANSWER_CACHE_DIR}", flush=True)


def load_questions() -> list[dict[str, Any]]:
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

    from systems.no_retrieval import NoRetrieval  # noqa: E402

    system = NoRetrieval()
    sample = load_questions()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "n.jsonl"

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
            f"[noretrieval] resuming: {len(done_ids)} already done, "
            f"{len(remaining)} remaining",
            flush=True,
        )
    print(
        f"[noretrieval] sample={len(sample)}, remaining={len(remaining)}, "
        f"concurrency={concurrency}",
        flush=True,
    )
    if not remaining:
        print("[noretrieval] nothing to do.", flush=True)
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
                    f"[noretrieval] {n}/{n_total} done "
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
                max_workers=concurrency, thread_name_prefix="noretrieval"
            ) as ex:
                futures = [ex.submit(answer_one, q) for q in remaining]
                for fut in as_completed(futures):
                    rec = fut.result()
                    write_record(rec, fh)

    elapsed = time.perf_counter() - t_start
    print(
        f"[noretrieval] done in {elapsed:.0f}s; wrote {counter['n']} records to {out_path}",
        flush=True,
    )


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--concurrency", type=int, default=4)
    args = p.parse_args()
    if args.concurrency < 1:
        print("concurrency must be >= 1", file=sys.stderr)
        sys.exit(2)
    run(args.concurrency)


if __name__ == "__main__":
    main()
