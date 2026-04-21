"""System A — Narrative RAG.

Pipeline (per patient):
  1. Load LLM narrative from narratives/llm_narratives/{patient_id}.txt.
  2. Chunk via systems.common.chunker (CHUNK_TOKENS=500, overlap=50).
  3. Embed each chunk via systems.common.embedder (BGE-large-en-v1.5, cached).
  4. Index into a per-patient ChromaDB collection persisted at
     systems/system_a/chroma/{patient_id}/.
     Collection name: ``narrative_<first8>`` (first 8 chars of the UUID).
     Patient isolation is a hard methodological invariant — no cross-patient
     retrieval is possible because each collection contains only that patient's
     chunks.
  5. On query: embed question → top-k cosine-nearest chunks → concatenate →
     pass to answer_llm.ask() → return SystemResponse.

ChromaDB config note (judgment call):
  - Distance metric: cosine similarity (``hnsw:space = 'cosine'``).
    This is the natural choice for normalised BGE embeddings (the embedder
    already normalises to unit sphere).  A decision-log entry is not strictly
    required because the metric is implied by the embedding normalisation
    choice (decision A3), but it is documented here for auditability.
  - Chroma collection naming: ``narrative_<first8>`` — Chroma requires names
    3-63 chars, matching [a-zA-Z0-9_-]+.  First 8 chars of a UUID are always
    hex so this is safe.
  - PersistentClient per collection query: we open a fresh PersistentClient
    for each method call to avoid holding a long-lived file lock across calls.
    This is safe because Chroma's HNSW index is thread-safe for reads, and we
    index only once (idempotent guard on collection count > 0).

No new hyperparameters are introduced.  All constants (TOP_K, CHUNK_TOKENS,
CHUNK_OVERLAP_TOKENS, EMBEDDING_MODEL, ANSWER_*) come from eval.config.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import chromadb
import numpy as np

from eval.config import (
    LLM_NARRATIVES_DIR,
    PROJECT_ROOT,
    TOP_K,
)
from systems.base import SystemResponse
from systems.common.answer_llm import ask as answer_llm_ask
from systems.common.chunker import chunk_text
from systems.common.embedder import EmbeddingClient

# ---------------------------------------------------------------------------
# Constants (not hyperparameters — these are naming/layout choices)
# ---------------------------------------------------------------------------

# Base directory for all System A ChromaDB collections.
# Persisted so re-indexing is skipped on subsequent runs.
_CHROMA_BASE: Path = PROJECT_ROOT / "systems" / "system_a" / "chroma"

# Collection name prefix.  Combined with first 8 chars of patient UUID.
# Documented in module docstring — not in eval.config because it is an
# internal naming convention, not a tunable hyperparameter.
_COLLECTION_PREFIX: str = "narrative_"

# Chunk separator used when concatenating top-k chunks for the LLM context.
_CHUNK_SEPARATOR: str = "\n\n---\n\n"


def _collection_name(patient_id: str) -> str:
    """Return the Chroma collection name for *patient_id*.

    Uses first 8 chars of the UUID (always hex, safe for Chroma's regex).
    """
    return f"{_COLLECTION_PREFIX}{patient_id[:8]}"


def _chroma_dir(patient_id: str) -> Path:
    """Return the on-disk path for this patient's Chroma collection."""
    return _CHROMA_BASE / patient_id


def _open_client(patient_id: str) -> chromadb.PersistentClient:
    """Open (or create) the PersistentClient for *patient_id*."""
    chroma_path = _chroma_dir(patient_id)
    chroma_path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(chroma_path))


class NarrativeRAG:
    """System A: LLM narrative → chunks → BGE embeddings → ChromaDB → answer LLM.

    Satisfies the ``BaseSystem`` protocol from ``systems.base`` via structural
    subtyping (duck typing).  No inheritance is needed because ``BaseSystem``
    is a ``runtime_checkable`` Protocol.

    Parameters
    ----------
    embedder:
        Optional pre-constructed EmbeddingClient.  Defaults to a fresh client
        using the config defaults.  Inject in tests to control the cache dir.
    """

    #: Identifier used by the harness for result records.
    name: str = "system_a_narrative"

    def __init__(self, embedder: EmbeddingClient | None = None) -> None:
        self._embedder = embedder or EmbeddingClient()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def index_patient(self, patient_id: str) -> None:
        """Build (or verify) the ChromaDB collection for *patient_id*.

        Idempotent: if the collection already contains at least one document
        the method returns immediately without re-embedding or re-inserting.

        Parameters
        ----------
        patient_id:
            Full UUID string (e.g. ``"014abeea-627d-f33c-834c-e2a6605046ee"``).

        Raises
        ------
        FileNotFoundError
            If the narrative file for *patient_id* does not exist.
        """
        narrative_path = LLM_NARRATIVES_DIR / f"{patient_id}.txt"
        if not narrative_path.exists():
            raise FileNotFoundError(
                f"Narrative not found for patient {patient_id!r}: {narrative_path}"
            )

        client = _open_client(patient_id)
        col_name = _collection_name(patient_id)

        # get_or_create with cosine distance (matching normalised BGE vectors)
        collection = client.get_or_create_collection(
            name=col_name,
            metadata={"hnsw:space": "cosine"},
        )

        # Idempotency guard: skip if already indexed
        if collection.count() > 0:
            return

        # Load narrative text
        text = narrative_path.read_text(encoding="utf-8")

        # Chunk
        chunks = chunk_text(text, source_id=patient_id)
        if not chunks:
            # Empty narrative — nothing to index.  Collection stays empty.
            return

        # Embed all chunks (batch for efficiency; cache on disk)
        chunk_texts = [c.text for c in chunks]
        embeddings: list[np.ndarray] = self._embedder.embed_batch(chunk_texts)

        # Build Chroma documents
        ids: list[str] = [f"{patient_id}::chunk_{c.chunk_index}" for c in chunks]
        metadatas: list[dict[str, Any]] = [
            {
                "patient_id": patient_id,
                "chunk_index": str(c.chunk_index),
                "source_id": c.source_id,
            }
            for c in chunks
        ]
        embedding_lists: list[list[float]] = [e.tolist() for e in embeddings]

        collection.add(
            ids=ids,
            embeddings=embedding_lists,
            documents=chunk_texts,
            metadatas=metadatas,
        )

    def answer(self, question: str, patient_id: str) -> SystemResponse:
        """Answer *question* for *patient_id* using the narrative RAG pipeline.

        Calls ``index_patient`` first (idempotent — cheap if already indexed).

        Parameters
        ----------
        question:
            Natural-language question string.
        patient_id:
            UUID string identifying the patient.

        Returns
        -------
        SystemResponse
            answer, retrieved chunks (with text/source_id/score/rank),
            tokens_in, tokens_out, latency_ms.
        """
        t0 = time.perf_counter()

        # Ensure indexed (idempotent)
        self.index_patient(patient_id)

        # Embed the question
        q_vec: np.ndarray = self._embedder.embed_one(question)

        # Query ChromaDB
        client = _open_client(patient_id)
        col_name = _collection_name(patient_id)
        collection = client.get_or_create_collection(
            name=col_name,
            metadata={"hnsw:space": "cosine"},
        )

        n_results = min(TOP_K, collection.count())
        query_result = collection.query(
            query_embeddings=[q_vec.tolist()],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

        # Unpack results (Chroma returns lists-of-lists for batch queries)
        docs: list[str] = query_result["documents"][0]
        distances: list[float] = query_result["distances"][0]
        metadatas_list: list[dict[str, Any]] = query_result["metadatas"][0]

        # Build retrieved provenance list (rank-ordered, rank 1 = closest)
        retrieved: list[dict[str, Any]] = []
        for rank, (doc, dist, meta) in enumerate(
            zip(docs, distances, metadatas_list), start=1
        ):
            # Chroma cosine distance ∈ [0, 2]; convert to similarity ∈ [-1, 1]
            similarity = 1.0 - dist
            retrieved.append(
                {
                    "text": doc,
                    "source_id": meta.get("source_id", patient_id),
                    "chunk_index": meta.get("chunk_index", ""),
                    "score": round(similarity, 6),
                    "rank": rank,
                    "patient_id": meta.get("patient_id", patient_id),
                }
            )

        # Concatenate context in rank order (rank 1 first)
        context = _CHUNK_SEPARATOR.join(r["text"] for r in retrieved)

        # Call answer LLM (cached)
        llm_result = answer_llm_ask(question=question, context=context)

        latency_ms = (time.perf_counter() - t0) * 1000.0

        return SystemResponse(
            answer=llm_result.answer,
            retrieved=retrieved,
            tokens_in=llm_result.tokens_in,
            tokens_out=llm_result.tokens_out,
            latency_ms=latency_ms,
            extras={
                "system": self.name,
                "cache_hit": llm_result.cache_hit,
                "prompt_sha256": llm_result.prompt_sha256,
                "n_chunks_indexed": collection.count(),
                "n_chunks_retrieved": len(retrieved),
            },
        )
