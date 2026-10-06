"""Post-think re-scoring (paper v2 sensitivity analysis).

The production scorer searches the entire response, including the Qwen3
``<think>`` block, for the first date or number.  This script re-scores every
arm on the text AFTER the closing ``</think>`` tag only; responses that never
close the block (output budget exhausted mid-reasoning) are scored as an empty
answer.  No API calls are made.

Inputs (read-only): the frozen raw JSONLs under results/raw_large,
results/raw_noretrieval, results/raw_templated.
Outputs:
  results/raw_postthink/{a,b,c,n,at}.jsonl   (stripped copies; regenerable)
  results/scored_postthink/scored.csv         (via eval.score.run_scoring)
  analysis/postthink_rescore.md               (summary tables)

Reproduce: python analysis/run_postthink_rescore.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import functools  # noqa: E402

import eval.score as _score  # noqa: E402
from eval.config import FHIR_BUNDLES_DIR, QUESTIONS_PATH  # noqa: E402
from eval.score import run_scoring  # noqa: E402

# The production scorer re-parses the patient's FHIR bundle on every free-text
# and recall@k call (200 bundles, ~3.6 MB each, 69,000 rows).  Results are
# identical with a per-path cache; this only makes the run finish in minutes.
_score._load_bundle_gt = functools.lru_cache(maxsize=None)(_score._load_bundle_gt)
_score._primary_resource_ids = functools.lru_cache(maxsize=None)(_score._primary_resource_ids)

RAW_OUT = ROOT / "results" / "raw_postthink"
SCORED_OUT = ROOT / "results" / "scored_postthink"
MD_OUT = ROOT / "analysis" / "postthink_rescore.md"

SOURCES = {
    "a": ROOT / "results/raw_large/a.jsonl",
    "b": ROOT / "results/raw_large/b.jsonl",
    "c": ROOT / "results/raw_large/c.jsonl",
    "n": ROOT / "results/raw_noretrieval/n.jsonl",
    "at": ROOT / "results/raw_templated/a_templated.jsonl",
}


def strip_think(answer: str) -> str:
    if "</think>" in answer:
        return answer.rsplit("</think>", 1)[1].strip()
    return ""


def main() -> None:
    RAW_OUT.mkdir(parents=True, exist_ok=True)
    SCORED_OUT.mkdir(parents=True, exist_ok=True)
    closed_stats: dict[str, tuple[int, int]] = {}
    for name, src in SOURCES.items():
        n = closed = 0
        with open(src, encoding="utf-8") as fh, open(RAW_OUT / f"{name}.jsonl", "w", encoding="utf-8") as out:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                n += 1
                ans = r.get("answer", "") or ""
                closed += "</think>" in ans
                r["answer"] = strip_think(ans)
                r["system"] = name
                out.write(json.dumps(r, ensure_ascii=False) + "\n")
        closed_stats[name] = (n, closed)
        print(f"[postthink] {name}: n={n} closed={closed} ({closed / n * 100:.1f}%)", flush=True)

    run_scoring(
        raw_dir=RAW_OUT,
        questions_path=QUESTIONS_PATH,
        output_dir=SCORED_OUT,
        bundles_dir=FHIR_BUNDLES_DIR,
        system_names=list(SOURCES),
    )

    import pandas as pd

    post = pd.read_csv(SCORED_OUT / "scored.csv", low_memory=False)
    post["is_na"] = post.ground_truth.isna()
    orig = pd.concat(
        [
            pd.read_csv(ROOT / "results/scored.csv", low_memory=False),
            pd.read_csv(ROOT / "results/scored_noretrieval/scored.csv", low_memory=False).assign(system="n"),
            pd.read_csv(ROOT / "results/scored_templated/scored.csv", low_memory=False).assign(system="at"),
        ]
    )
    lines = ["# Post-think re-scoring (paper v2)\n",
             "> Reproduce: `python analysis/run_postthink_rescore.py`\n",
             "Scoring applied to the text after `</think>` only; unclosed responses scored as empty.\n",
             "## Closed think blocks\n"]
    for k, (n, c) in closed_stats.items():
        lines.append(f"- {k}: {c}/{n} = {c / n * 100:.1f}%")
    lines.append("\n## Exact-match accuracy, original vs post-think scoring (%)\n")
    rows = []
    for s in SOURCES:
        o = orig[orig.system == s].set_index("question_id").exact_match
        p = post[post.system == s].set_index("question_id").exact_match
        na = post[post.system == s].set_index("question_id").is_na
        j = pd.concat([o.rename("orig"), p.rename("post"), na], axis=1).dropna()
        rows.append({
            "arm": s,
            "orig_all": round(j.orig.mean() * 100, 2),
            "post_all": round(j.post.mean() * 100, 2),
            "orig_subst": round(j[~j.is_na].orig.mean() * 100, 2),
            "post_subst": round(j[~j.is_na].post.mean() * 100, 2),
            "orig_na": round(j[j.is_na].orig.mean() * 100, 2),
            "post_na": round(j[j.is_na].post.mean() * 100, 2),
            "orig_correct_post_wrong": int((j.orig & ~j.post).sum()),
            "orig_wrong_post_correct": int((~j.orig & j.post).sum()),
        })
    lines.append(pd.DataFrame(rows).to_markdown(index=False))
    lines.append("\n## Post-think accuracy by tier (%)\n")
    lines.append((post.pivot_table(index="tier", columns="system", values="exact_match", aggfunc="mean") * 100).round(1).to_markdown())
    lines.append("\n## Post-think accuracy by family x N/A (%)\n")
    lines.append((post.pivot_table(index=["family", "is_na"], columns="system", values="exact_match", aggfunc="mean") * 100).round(1).to_markdown())
    MD_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {MD_OUT}")


if __name__ == "__main__":
    main()
