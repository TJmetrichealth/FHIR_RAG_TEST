"""1024-token sweep on a stratified 500-question sample.

Goal: test the §5 hypothesis that the A > B > C ordering is conditional on the
512-token output budget by re-running all three systems on a stratified sample
at max_tokens=1024.

Sample: 33 question_ids per (tier x type) cell = 5 families x 3 tiers x 33 = 495
questions. Seed 42. Each system answers exactly the same 495 question_ids.

Cache isolation: routes through eval/cache_1024/answers so the production
eval/cache/ remains byte-reproducible. The existing cache key does not include
max_tokens, which is why a separate cache directory is required.

Output: results/raw_1024/{a,b,c}.jsonl (same schema as results/raw_large/).

Usage::

    python scripts/token_sweep_1024.py --system a [--concurrency 4]

Environment: requires GROQ_API_KEY with Developer-plan access. Estimated cost
~$3 USD total across all three systems; ~15-30 min wall time.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS_PATH = ROOT / "questions" / "questions.jsonl"
OUTPUT_DIR = ROOT / "results" / "raw_1024"
CACHE_DIR_1024 = ROOT / "eval" / "cache_1024" / "answers"

SAMPLE_PER_CELL = 33
SEED = 42
MAX_TOKENS = 1024


def load_sample() -> list[dict[str, Any]]:
    """Load 33 questions per (tier, type) cell, seed 42, deterministic."""
    by_cell: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    with open(QUESTIONS_PATH, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            q = json.loads(line)
            tier = q.get("tier")
            fam = q.get("type")
            by_cell[(tier, fam)].append(q)

    sampled: list[dict[str, Any]] = []
    rng = random.Random(SEED)
    for cell in sorted(by_cell.keys()):
        qs = list(by_cell[cell])
        qs.sort(key=lambda q: q["id"])  # deterministic pre-shuffle order
        rng.shuffle(qs)
        take = qs[:SAMPLE_PER_CELL]
        sampled.extend(take)

    sampled.sort(key=lambda q: q["id"])
    return sampled


def patch_for_1024() -> None:
    """Monkey-patch answer_llm to use max_tokens=1024 + a fresh cache dir.

    Must be called BEFORE any system module is imported, because answer_llm
    reads these names at call time from its own namespace and the systems
    bind to answer_llm.ask via 'from ... import ask'.
    """
    import systems.common.answer_llm as al

    al.ANSWER_MAX_TOKENS = MAX_TOKENS
    al.ANSWER_CACHE_DIR = CACHE_DIR_1024
    al._clients.clear()
    print(
        f"[sweep] patched ANSWER_MAX_TOKENS={al.ANSWER_MAX_TOKENS}, "
        f"ANSWER_CACHE_DIR={al.ANSWER_CACHE_DIR}",
        flush=True,
    )


def run_for_system(system_name: str, concurrency: int) -> None:
    patch_for_1024()

    from eval.harness import _load_system  # noqa: E402

    sys_obj = _load_system(system_name)
    sample = load_sample()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{system_name}.jsonl"

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
            f"[sweep] resuming: {len(done_ids)} already done, {len(remaining)} remaining",
            flush=True,
        )
    print(
        f"[sweep] system={system_name}, sample={len(sample)}, remaining={len(remaining)}, "
        f"concurrency={concurrency}",
        flush=True,
    )

    if not remaining:
        print("[sweep] nothing to do.")
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
            resp = sys_obj.answer(q["question"], q["patient_id"])
            record = {
                "question_id": q["id"],
                "patient_id": q["patient_id"],
                "question": q["question"],
                "question_type": q["type"],
                "tier": q.get("tier"),
                "reference_date": q.get("reference_date"),
                "ground_truth": q.get("ground_truth"),
                "system": system_name,
                "answer": resp.answer,
                "retrieved": resp.retrieved,
                "tokens_in": resp.tokens_in,
                "tokens_out": resp.tokens_out,
                "latency_ms": resp.latency_ms,
                "extras": resp.extras,
                "max_tokens": MAX_TOKENS,
            }
        except Exception as exc:  # noqa: BLE001
            record = {
                "question_id": q["id"],
                "patient_id": q["patient_id"],
                "system": system_name,
                "max_tokens": MAX_TOKENS,
                "error": str(exc),
                "latency_ms": (time.perf_counter() - t0) * 1000.0,
            }
        return record

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
                    f"[sweep] {n}/{n_total} done "
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
                max_workers=concurrency, thread_name_prefix="sweep"
            ) as ex:
                futures = [ex.submit(answer_one, q) for q in remaining]
                for fut in as_completed(futures):
                    rec = fut.result()
                    write_record(rec, fh)

    elapsed = time.perf_counter() - t_start
    print(
        f"[sweep] system={system_name} done in {elapsed:.0f}s; "
        f"wrote {counter['n']} records to {out_path}",
        flush=True,
    )


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--system",
        required=True,
        choices=["a", "b", "c"],
        help="which system to run",
    )
    p.add_argument(
        "--concurrency",
        type=int,
        default=4,
        help="in-flight system.answer calls (default 4)",
    )
    args = p.parse_args()

    if args.concurrency < 1:
        print("concurrency must be >= 1", file=sys.stderr)
        sys.exit(2)

    run_for_system(args.system, args.concurrency)


if __name__ == "__main__":
    main()
