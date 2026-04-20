"""Hash-keyed response cache for LLM calls.

Every LLM request is cached at eval/cache/<model>/<first2>/<hash>.json
with the full request payload, the response text, tokens_in/out, and the
model snapshot. This is the single source of truth for reproducibility —
losing this cache means paying rate-limit wall time again.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


DEFAULT_CACHE_DIR = Path("eval/cache")


@dataclass(frozen=True)
class CachedResponse:
    text: str
    tokens_in: int
    tokens_out: int
    model: str
    prompt_sha256: str
    latency_ms: float
    raw: dict[str, Any]


def request_hash(*, model: str, prompt: str, temperature: float, system: str = "") -> str:
    blob = json.dumps(
        {"model": model, "system": system, "prompt": prompt, "temperature": temperature},
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


class ResponseCache:
    def __init__(self, root: Path = DEFAULT_CACHE_DIR) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path_for(self, model: str, key: str) -> Path:
        safe_model = model.replace("/", "_")
        return self.root / safe_model / key[:2] / f"{key}.json"

    def get(self, model: str, key: str) -> CachedResponse | None:
        path = self._path_for(model, key)
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        return CachedResponse(**data)

    def put(self, model: str, key: str, response: CachedResponse) -> None:
        path = self._path_for(model, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(response), indent=2, sort_keys=True))

    def stats(self, model: str | None = None) -> dict[str, int]:
        if model:
            base = self.root / model.replace("/", "_")
            files = list(base.rglob("*.json")) if base.exists() else []
        else:
            files = list(self.root.rglob("*.json"))
        return {"entries": len(files)}
