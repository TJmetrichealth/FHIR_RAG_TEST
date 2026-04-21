"""System B — Structured RAG (naive).

Scientific role in the paper:
  System B is the "naive structured" baseline. It ingests the same FHIR bundles
  as System C but applies zero schema awareness — every resource is serialised to
  text by a dumb JSON dump and indexed flat, identically to how System A indexes
  narrative text.  The A-vs-B-vs-C contrast is:

    A: LLM narrative → flat chunks → retrieve
    B: FHIR resources → JSON-dump → flat chunks → retrieve     ← this module
    C: FHIR resources → resource-type-aware retrieval (next task)

  System B answers the question: "Does knowing the data is FHIR, but treating it
  as plain text, beat the narrative?" Schema awareness must NOT be introduced here
  — that would contaminate the B-vs-C contrast.

Serialisation choice (documented here per the task spec):
  Default: ``json.dumps(resource, indent=2, sort_keys=True)``.
  Rationale:
    1. JSON is the canonical FHIR wire format — the embedding model (BGE-large)
       has seen JSON-shaped text in training; key names such as ``resourceType``,
       ``code``, ``display``, ``status`` carry semantic signal even as plain text.
    2. ``sort_keys=True`` gives deterministic output regardless of insertion order,
       which is required for cache stability (same resource → same chunk text →
       same embedding cache key on every run).
    3. ``indent=2`` produces one-key-per-line formatting that the sentence-level
       chunker can split naturally at ``\\n`` boundaries between JSON values.
    4. Alternative considered: flat ``key: value`` lines.  Rejected because it
       requires a custom serialiser that would need to handle nested FHIR
       extensions, coding arrays, and reference objects — adding non-trivial
       complexity without a principled accuracy advantage.  "Naive" means minimal.

Chunk IDs:
  Format: ``{resourceType}_{resource_id}::chunk_{i}``
  The double-colon mirrors System A's ``{patient_id}::chunk_{i}`` convention.
  The resource identity prefix lets post-hoc analysis (W3 error taxonomy) trace
  retrieved chunks back to their source resource without parsing the chunk text.

ChromaDB collection:
  Per-patient collection at ``systems/structured_naive/chroma/{patient_id}/``.
  Collection name: ``snv_{patient_id[:8]}``  (prefix "snv" = structured-naive).
  Naming convention mirrors System A's ``narrative_<first8>`` — 8 hex chars from
  the UUID guarantee Chroma's 3-63 char + [a-zA-Z0-9_-] constraint is met.

Metadata stored per chunk (for W3 error taxonomy; NOT used at retrieval time):
  ``resource_type``  — FHIR resourceType string (e.g. "MedicationRequest")
  ``resource_id``    — FHIR resource.id string
  ``chunk_index``    — index of this chunk within the resource's serialisation
  ``patient_id``     — patient UUID (mirrors System A convention)
  ``source_id``      — same value as patient_id (mirrors System A convention)

No new hyperparameters. All constants come from eval.config.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import chromadb
import numpy as np

from eval.config import FHIR_BUNDLES_DIR, PROJECT_ROOT, TOP_K
from systems.base import SystemResponse
from systems.common.answer_llm import ask as answer_llm_ask
from systems.common.chunker import chunk_text
from systems.common.embedder import EmbeddingClient

# ---------------------------------------------------------------------------
# Constants (naming / layout choices — not tunable hyperparameters)
# ---------------------------------------------------------------------------

# Base directory for all System B ChromaDB collections.
_CHROMA_BASE: Path = PROJECT_ROOT / "systems" / "structured_naive" / "chroma"

# Collection name prefix. "snv" = structured-naive.
# 3 chars + 8 hex chars = 11 chars — well within Chroma's 3-63 limit.
_COLLECTION_PREFIX: str = "snv_"

# Chunk separator used when concatenating top-k chunks for the LLM context.
# Identical to System A — controlled variable.
_CHUNK_SEPARATOR: str = "\n\n---\n\n"


def _collection_name(patient_id: str) -> str:
    """Return the Chroma collection name for *patient_id*."""
    return f"{_COLLECTION_PREFIX}{patient_id[:8]}"


def _chroma_dir(patient_id: str) -> Path:
    """Return the on-disk path for this patient's Chroma collection."""
    return _CHROMA_BASE / patient_id


def _open_client(patient_id: str) -> chromadb.PersistentClient:
    """Open (or create) the PersistentClient for *patient_id*."""
    chroma_path = _chroma_dir(patient_id)
    chroma_path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(chroma_path))


def _resource_text(resource: dict[str, Any]) -> str:
    """Serialise a FHIR resource dict to the canonical text form for embedding.

    Uses pretty-printed JSON with sorted keys for determinism.
    No transformation, no field filtering — the whole resource verbatim.
    This is the "naive" invariant: no schema knowledge applied here.
    """
    return json.dumps(resource, indent=2, sort_keys=True, ensure_ascii=False)


def _safe_resource_id(resource: dict[str, Any]) -> str:
    """Return a filesystem/Chroma-safe resource id string.

    Falls back to the resourceType when the resource has no ``id`` field
    (rare but valid for inline resources in Synthea bundles).
    """
    rid = resource.get("id", "")
    if rid:
        return rid
    # No id — use resourceType as fallback; still unique enough within one
    # resource serialisation (we never need global uniqueness here).
    return resource.get("resourceType", "unknown")


class StructuredRAGNaive:
    """System B: FHIR resources → JSON text → chunks → BGE embeddings → ChromaDB → answer LLM.

    Satisfies the ``BaseSystem`` protocol from ``systems.base`` via structural
    subtyping (duck typing).  No inheritance needed.

    Controlled variables (identical to System A):
    - Embedding model: BAAI/bge-large-en-v1.5 (via shared EmbeddingClient)
    - Chunk size / overlap: CHUNK_TOKENS=500, CHUNK_OVERLAP_TOKENS=50
    - TOP_K: 5
    - Answer LLM: qwen/qwen3-32b at temperature 0.0
    - Chunk separator: "\\n\\n---\\n\\n"
    - ChromaDB metric: cosine (hnsw:space=cosine)

    The ONLY difference from System A is the source text: JSON-serialised FHIR
    resources instead of LLM-generated narrative.

    Parameters
    ----------
    embedder:
        Optional pre-constructed EmbeddingClient.  Defaults to a fresh client
        using the config defaults.  Inject in tests to control the cache dir.
    """

    #: Identifier used by the harness for result records.
    name: str = "system_b_structured_naive"

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
            If the FHIR bundle for *patient_id* does not exist.
        """
        bundle_path = FHIR_BUNDLES_DIR / f"{patient_id}.json"
        if not bundle_path.exists():
            raise FileNotFoundError(
                f"FHIR bundle not found for patient {patient_id!r}: {bundle_path}"
            )

        client = _open_client(patient_id)
        col_name = _collection_name(patient_id)

        collection = client.get_or_create_collection(
            name=col_name,
            metadata={"hnsw:space": "cosine"},
        )

        # Idempotency guard: skip if already indexed
        if collection.count() > 0:
            return

        # Load bundle
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        entries: list[dict[str, Any]] = bundle.get("entry", [])

        # Accumulate all (chunk_text, chunk_id, chunk_metadata) triples
        all_texts: list[str] = []
        all_ids: list[str] = []
        all_metas: list[dict[str, Any]] = []

        for entry in entries:
            resource: dict[str, Any] = entry.get("resource", {})
            if not resource:
                continue

            resource_type: str = resource.get("resourceType", "Unknown")
            resource_id: str = _safe_resource_id(resource)

            # Serialise to text — no schema awareness, just JSON dump
            text = _resource_text(resource)

            # Chunk via the shared chunker (same parameters as System A)
            chunks = chunk_text(text, source_id=resource_id)
            if not chunks:
                continue

            for chunk in chunks:
                # Chunk ID encodes resource identity + chunk index so duplicates
                # can be detected and provenance can be traced in W3 analysis.
                chunk_id = f"{resource_type}_{resource_id}::chunk_{chunk.chunk_index}"
                all_ids.append(chunk_id)
                all_texts.append(chunk.text)
                all_metas.append(
                    {
                        "resource_type": resource_type,
                        "resource_id": resource_id,
                        "chunk_index": str(chunk.chunk_index),
                        "patient_id": patient_id,
                        "source_id": patient_id,
                    }
                )

        if not all_texts:
            # Bundle has no serialisable resources — collection stays empty.
            return

        # Embed all chunks in one batch (cache on disk)
        embeddings: list[np.ndarray] = self._embedder.embed_batch(all_texts)
        embedding_lists: list[list[float]] = [e.tolist() for e in embeddings]

        collection.add(
            ids=all_ids,
            embeddings=embedding_lists,
            documents=all_texts,
            metadatas=all_metas,
        )

    def answer(self, question: str, patient_id: str) -> SystemResponse:
        """Answer *question* for *patient_id* using the structured-naive RAG pipeline.

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
                    "resource_type": meta.get("resource_type", ""),
                    "resource_id": meta.get("resource_id", ""),
                    "chunk_index": meta.get("chunk_index", ""),
                    "score": round(similarity, 6),
                    "rank": rank,
                    "patient_id": meta.get("patient_id", patient_id),
                }
            )

        # Concatenate context in rank order (rank 1 first)
        context = _CHUNK_SEPARATOR.join(r["text"] for r in retrieved)

        # Call answer LLM (cached) — identical call to System A
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
