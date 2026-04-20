"""Compute a SHA-256 manifest over dataset directories and write data/freeze.json.

Covered directories (recursive):
  * data/fhir_bundles/
  * narratives/llm_narratives/
  * narratives/templated_narratives/
  * narratives/fidelity_reports/
  * questions/questions.jsonl

Every file gets an entry with {path, sha256, bytes}. The overall hash is a
SHA-256 over the sorted list of per-file hashes, giving a single reproducible
"dataset hash" suitable for a git-tag commit message.

Usage:
  python scripts/freeze_dataset.py --output data/freeze.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_TARGETS = [
    "data/fhir_bundles",
    "narratives/llm_narratives",
    "narratives/templated_narratives",
    "narratives/fidelity_reports",
    "questions/questions.jsonl",
]


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _iter_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    if target.is_dir():
        return sorted(p for p in target.rglob("*") if p.is_file() and p.name != ".gitkeep")
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/freeze.json"))
    parser.add_argument(
        "--target",
        action="append",
        default=None,
        help="Override targets (repeat flag for multiple; defaults to DEFAULT_TARGETS).",
    )
    args = parser.parse_args(argv)

    targets = [Path(t) for t in (args.target or DEFAULT_TARGETS)]
    manifest: list[dict[str, object]] = []
    for t in targets:
        for f in _iter_files(t):
            try:
                h = _sha256_file(f)
            except OSError as exc:
                print(f"[warn] could not hash {f}: {exc}", file=sys.stderr)
                continue
            manifest.append(
                {"path": str(f), "sha256": h, "bytes": f.stat().st_size}
            )

    manifest.sort(key=lambda r: r["path"])
    roll = hashlib.sha256()
    for r in manifest:
        roll.update(f"{r['path']}\0{r['sha256']}\n".encode("utf-8"))
    overall = roll.hexdigest()

    out = {
        "frozen_at_utc": datetime.now(tz=timezone.utc).isoformat(),
        "overall_sha256": overall,
        "targets": [str(t) for t in targets],
        "n_files": len(manifest),
        "files": manifest,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=2, sort_keys=True))
    print(f"freeze: {len(manifest)} files → overall_sha256={overall[:16]}… wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
