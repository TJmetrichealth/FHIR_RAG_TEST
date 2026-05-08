"""One-off Groq cost projection for the W3 eval matrix."""
from __future__ import annotations

import json
from pathlib import Path

# Groq qwen-3-32b pricing (USD per 1M tokens). User should verify against the
# Groq dashboard; pricing rarely changes but this is a snapshot.
PRICE_IN_PER_M = 0.29
PRICE_OUT_PER_M = 0.59


def main() -> None:
    total_rows = 0
    cache_hits = 0
    live_calls = 0
    error_rows = 0
    live_in_tokens = 0
    live_out_tokens = 0
    cached_in_tokens = 0
    cached_out_tokens = 0

    for sys_name in ["a", "b", "c"]:
        p = Path(f"results/raw/{sys_name}.jsonl")
        if not p.exists():
            continue
        s_rows = s_hits = s_live = s_err = 0
        s_in_live = s_out_live = 0
        s_in_cached = s_out_cached = 0
        with open(p, encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                ex = r.get("extras") or {}
                if ex.get("error"):
                    s_err += 1
                    continue
                s_rows += 1
                tok_in = r.get("tokens_in", 0) or 0
                tok_out = r.get("tokens_out", 0) or 0
                if ex.get("cache_hit"):
                    s_hits += 1
                    s_in_cached += tok_in
                    s_out_cached += tok_out
                else:
                    s_live += 1
                    s_in_live += tok_in
                    s_out_live += tok_out
        total_rows += s_rows
        cache_hits += s_hits
        live_calls += s_live
        error_rows += s_err
        live_in_tokens += s_in_live
        live_out_tokens += s_out_live
        cached_in_tokens += s_in_cached
        cached_out_tokens += s_out_cached
        avg_in = s_in_live / max(1, s_live) if s_live else 0
        avg_out = s_out_live / max(1, s_live) if s_live else 0
        print(
            f"{sys_name}: rows={s_rows:>5}  err={s_err:>4}  cache_hits={s_hits:>5}  live={s_live:>5}  "
            f"live_avg_in={avg_in:.0f}  live_avg_out={avg_out:.0f}"
        )

    print()
    print(f"TOTAL: rows={total_rows}  cache_hits={cache_hits}  live={live_calls}  err={error_rows}")
    print(f"  Live tokens: in={live_in_tokens:,}  out={live_out_tokens:,}  total={live_in_tokens+live_out_tokens:,}")

    cost_in = live_in_tokens * PRICE_IN_PER_M / 1_000_000
    cost_out = live_out_tokens * PRICE_OUT_PER_M / 1_000_000
    cost_so_far = cost_in + cost_out
    pin = "$"
    print(f"  Estimated cost so far (in @ {pin}{PRICE_IN_PER_M}/M, out @ {pin}{PRICE_OUT_PER_M}/M):")
    print(f"    input:  {pin}{cost_in:.2f}")
    print(f"    output: {pin}{cost_out:.2f}")
    print(f"    TOTAL:  {pin}{cost_so_far:.2f}")

    remaining = 0
    for sys_name in ["a", "b", "c"]:
        p = Path(f"results/raw/{sys_name}.jsonl")
        if p.exists():
            n = sum(1 for _ in open(p, encoding="utf-8"))
            remaining += 13800 - n
    print()
    print(f"Calls remaining (across all systems): {remaining:,}")

    if live_calls > 0:
        avg_in_live = live_in_tokens / live_calls
        avg_out_live = live_out_tokens / live_calls
        # Most remaining will be NEW (live). Project with current live averages.
        proj_in = remaining * avg_in_live
        proj_out = remaining * avg_out_live
        proj_cost = proj_in * PRICE_IN_PER_M / 1_000_000 + proj_out * PRICE_OUT_PER_M / 1_000_000
        print(f"  Projected remaining tokens: in={proj_in:,.0f}  out={proj_out:,.0f}")
        print(f"  Projected remaining cost: {pin}{proj_cost:.2f}")
        print(f"  Projected TOTAL eval cost (already-billed + remaining): {pin}{cost_so_far+proj_cost:.2f}")


if __name__ == "__main__":
    main()
