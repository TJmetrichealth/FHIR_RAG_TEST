"""Embedding client wrapping BAAI/bge-large-en-v1.5 via sentence-transformers.

Design:
- Single model instance loaded lazily (first call).
- Disk cache keyed by SHA-256(text + model_id) at eval/cache/embeddings/.
  Cache is gitignored but must be preserved locally.
- Deterministic: same text always returns the same vector (fp32 numpy array).
- Single-text and batch APIs; batch is always preferred for throughput.

All retrieval systems (A, B, C) import from this module.
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from eval.config import EMBEDDING_CACHE_DIR, EMBEDDING_MODEL

if TYPE_CHECKING:
    pass

# Module-level lock serialising .encode() on the shared SentenceTransformer.
# Required because the eval harness may dispatch many .answer() calls
# concurrently (decisions log: 2026-05-06). encode() on a single model
# instance is not thread-safe; serialising it is fine because each encode
# is ~10ms vs the ~1.5s Groq call that follows.
_ENCODE_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# Disk cache helpers
# ---------------------------------------------------------------------------

def _embed_cache_key(text: str, model_id: str) -> str:
    blob = json.dumps({"model": model_id, "text": text}, sort_keys=True, ensure_ascii=False).encode()
    return hashlib.sha256(blob).hexdigest()


def _cache_path(key: str, cache_dir: Path) -> Path:
    return cache_dir / key[:2] / f"{key}.npy"


def _load_from_cache(key: str, cache_dir: Path) -> np.ndarray | None:
    p = _cache_path(key, cache_dir)
    if not p.exists():
        return None
    # Treat a zero-byte file as a cache miss (left over from crashed np.save
    # under concurrency). The caller will re-embed and overwrite cleanly.
    try:
        if p.stat().st_size == 0:
            try:
                p.unlink()
            except OSError:
                pass
            return None
    except OSError:
        return None
    # Read bytes ourselves (Python file IO is GIL-protected and FD-leak-free
    # under threading) and feed numpy a BytesIO. Avoids the
    # "Getting a FILE* from a Python file object via _fdopen failed" race
    # that np.load(path) hits under concurrent ThreadPoolExecutor on Windows.
    import io
    last_exc: Exception | None = None
    for _ in range(3):
        try:
            with open(p, "rb") as fh:
                data = fh.read()
            if not data:
                # File got truncated between stat() and read() — treat as miss.
                return None
            return np.load(io.BytesIO(data))
        except (EOFError, ValueError) as exc:
            # Truncated / corrupt cache file — wipe and report miss.
            try:
                p.unlink()
            except OSError:
                pass
            last_exc = exc
            return None
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            time.sleep(0.05)
    raise last_exc  # pragma: no cover


def _save_to_cache(key: str, vec: np.ndarray, cache_dir: Path) -> None:
    p = _cache_path(key, cache_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    # Atomic write: serialise into bytes, write to a temp file in the same
    # directory, then rename onto the target. On Windows os.replace is atomic
    # for files on the same volume. This prevents readers from seeing a
    # partially-written file when many threads are computing identical
    # embeddings concurrently (same question across patients => same cache key).
    import io
    import os
    import uuid
    buf = io.BytesIO()
    np.save(buf, vec)
    payload = buf.getvalue()
    tmp = p.with_suffix(f".npy.tmp-{uuid.uuid4().hex[:8]}")
    try:
        tmp.write_bytes(payload)
        os.replace(tmp, p)
    except Exception:
        # Best-effort cleanup of orphaned tmp; safe to ignore on failure.
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Model singleton
# ---------------------------------------------------------------------------

_MODEL_INSTANCE: object | None = None
_LOADED_MODEL_ID: str | None = None


def _get_model(model_id: str) -> object:
    global _MODEL_INSTANCE, _LOADED_MODEL_ID
    if _MODEL_INSTANCE is None or _LOADED_MODEL_ID != model_id:
        from sentence_transformers import SentenceTransformer  # type: ignore

        _MODEL_INSTANCE = SentenceTransformer(model_id)
        _LOADED_MODEL_ID = model_id
    return _MODEL_INSTANCE


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class EmbeddingClient:
    """Cached, deterministic embedding client.

    Parameters
    ----------
    model_id:
        HuggingFace model name. Defaults to EMBEDDING_MODEL from config.
    cache_dir:
        Directory for on-disk embedding cache. Defaults to config value.
    """

    def __init__(
        self,
        model_id: str = EMBEDDING_MODEL,
        cache_dir: Path | None = None,
    ) -> None:
        self.model_id = model_id
        self.cache_dir = cache_dir or EMBEDDING_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def embed_one(self, text: str) -> np.ndarray:
        """Embed a single string. Returns a 1-D float32 numpy array."""
        key = _embed_cache_key(text, self.model_id)
        cached = _load_from_cache(key, self.cache_dir)
        if cached is not None:
            return cached
        model = _get_model(self.model_id)
        with _ENCODE_LOCK:
            vec: np.ndarray = model.encode(text, normalize_embeddings=True)  # type: ignore[union-attr]
        _save_to_cache(key, vec.astype(np.float32), self.cache_dir)
        return vec.astype(np.float32)

    def embed_batch(self, texts: list[str]) -> list[np.ndarray]:
        """Embed a list of strings.

        Returns cache hits immediately; only uncached texts are sent to the
        model in a single batch call (efficient for large lists).
        """
        keys = [_embed_cache_key(t, self.model_id) for t in texts]
        results: list[np.ndarray | None] = [_load_from_cache(k, self.cache_dir) for k in keys]

        # Collect indices that need to be computed
        missing_idx = [i for i, r in enumerate(results) if r is None]
        if missing_idx:
            missing_texts = [texts[i] for i in missing_idx]
            model = _get_model(self.model_id)
            with _ENCODE_LOCK:
                vecs: np.ndarray = model.encode(  # type: ignore[union-attr]
                    missing_texts, normalize_embeddings=True, show_progress_bar=False
                )
            for local_i, global_i in enumerate(missing_idx):
                vec = vecs[local_i].astype(np.float32)
                _save_to_cache(keys[global_i], vec, self.cache_dir)
                results[global_i] = vec

        return results  # type: ignore[return-value]

    def cache_stats(self) -> dict[str, int]:
        files = list(self.cache_dir.rglob("*.npy"))
        return {"entries": len(files)}
