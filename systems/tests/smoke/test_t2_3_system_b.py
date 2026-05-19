"""Smoke tests for T2.3 — System B (Structured RAG, naive).

Tests verify the StructuredRAGNaive pipeline end-to-end:
  1. Indexing is idempotent.
  2. Patient isolation (no cross-patient retrieval).
  3. Top-k shape (min(TOP_K, collection_size) chunks in query results).
  4. Chunk count is reasonable (>= 10 chunks for a real FHIR bundle).
  5. resource_type metadata is present on every retrieved chunk.
  6. Determinism (identical answer + ranks across two calls; requires API key).
  7. Live end-to-end smoke test (non-empty, non-N/A answer; requires API key).
  8. BaseSystem protocol compliance.
  9. Harness resolves 'structured_rag_naive' to StructuredRAGNaive.

Tests 1-5, 8-9 do NOT require GROQ_API_KEY (retrieval-layer assertions only).
Tests 6-7 require GROQ_API_KEY and are skipped when it is not set (consistent
with the T2.2 test pattern).

All assertions are mechanical — no LLM-as-judge anywhere.

Run with::

    pytest systems/tests/smoke/test_t2_3_system_b.py -v

Target: full suite completes in <3 minutes on a warm cache (indexing 597
resources per patient is the dominant cost on first run).
"""
from __future__ import annotations

import os
from pathlib import Path

import chromadb
import pytest

from eval.config import EMBEDDING_CACHE_DIR, TOP_K

# Two concrete patient IDs that have FHIR bundles committed in
# data/fhir_bundles/ (frozen at dataset-freeze-v1).
_PID_A = "014abeea-627d-f33c-834c-e2a6605046ee"
_PID_B = "02dc5960-eec7-7c95-977a-fbfef0c7318a"


# ---------------------------------------------------------------------------
# Shared helpers (mirror the System A test helpers exactly)
# ---------------------------------------------------------------------------

def _make_system(chroma_base: Path):
    """Return a StructuredRAGNaive wired to *chroma_base* for test isolation."""
    import systems.structured_rag_naive as mod
    from systems.common.embedder import EmbeddingClient

    embedder = EmbeddingClient(cache_dir=EMBEDDING_CACHE_DIR)
    original_base = mod._CHROMA_BASE
    mod._CHROMA_BASE = chroma_base
    try:
        system = mod.StructuredRAGNaive(embedder=embedder)
    finally:
        mod._CHROMA_BASE = original_base
    return system, chroma_base


def _index(chroma_base: Path, patient_id: str) -> int:
    """Index *patient_id* under *chroma_base*, return chunk count."""
    import systems.structured_rag_naive as mod
    from systems.common.embedder import EmbeddingClient

    embedder = EmbeddingClient(cache_dir=EMBEDDING_CACHE_DIR)
    original_base = mod._CHROMA_BASE
    mod._CHROMA_BASE = chroma_base
    try:
        system = mod.StructuredRAGNaive(embedder=embedder)
        system.index_patient(patient_id)
        col_name = mod._collection_name(patient_id)
    finally:
        mod._CHROMA_BASE = original_base

    client = chromadb.PersistentClient(path=str(chroma_base / patient_id))
    col = client.get_collection(col_name)
    return col.count()


def _query_chroma(chroma_base: Path, patient_id: str, question: str, k: int):
    """Query Chroma directly (bypasses LLM) — returns (docs, metadatas, distances)."""
    import systems.structured_rag_naive as mod
    from systems.common.embedder import EmbeddingClient

    embedder = EmbeddingClient(cache_dir=EMBEDDING_CACHE_DIR)
    q_vec = embedder.embed_one(question)

    original_base = mod._CHROMA_BASE
    mod._CHROMA_BASE = chroma_base
    try:
        col_name = mod._collection_name(patient_id)
    finally:
        mod._CHROMA_BASE = original_base

    client = chromadb.PersistentClient(path=str(chroma_base / patient_id))
    col = client.get_collection(col_name)
    n = min(k, col.count())
    result = col.query(
        query_embeddings=[q_vec.tolist()],
        n_results=n,
        include=["documents", "metadatas", "distances"],
    )
    return result["documents"][0], result["metadatas"][0], result["distances"][0]


# ---------------------------------------------------------------------------
# Test 1 — Idempotent indexing  (no API key needed)
# ---------------------------------------------------------------------------

def test_indexing_is_idempotent(tmp_path: Path) -> None:
    """Calling index_patient twice yields one collection of stable chunk count."""
    chroma_base = tmp_path / "chroma"

    count_first = _index(chroma_base, _PID_A)
    assert count_first > 0, "Collection must be non-empty after first indexing"

    count_second = _index(chroma_base, _PID_A)
    assert count_first == count_second, (
        f"Collection size changed after second index_patient call: "
        f"{count_first} -> {count_second}"
    )


# ---------------------------------------------------------------------------
# Test 2 — Patient isolation  (no API key needed — Chroma-level check)
# ---------------------------------------------------------------------------

def test_patient_isolation(tmp_path: Path) -> None:
    """Indexing patients A and B then querying A returns only A's chunks."""
    chroma_base = tmp_path / "chroma"

    _index(chroma_base, _PID_A)
    _index(chroma_base, _PID_B)

    question = "What medication is the patient on?"
    docs_a, metas_a, _ = _query_chroma(chroma_base, _PID_A, question, TOP_K)
    docs_b, metas_b, _ = _query_chroma(chroma_base, _PID_B, question, TOP_K)

    # All chunks from patient A's collection must belong to A
    for meta in metas_a:
        assert meta["patient_id"] == _PID_A, (
            f"Retrieved chunk from patient A's collection belongs to "
            f"{meta['patient_id']!r}, expected {_PID_A!r}"
        )

    # All chunks from patient B's collection must belong to B
    for meta in metas_b:
        assert meta["patient_id"] == _PID_B, (
            f"Retrieved chunk from patient B's collection belongs to "
            f"{meta['patient_id']!r}, expected {_PID_B!r}"
        )

    # FHIR resources are patient-specific — verify no text overlap
    # (catches shared-collection bugs)
    set_a = set(docs_a)
    set_b = set(docs_b)
    overlap = set_a & set_b
    assert len(overlap) == 0, (
        f"Cross-patient text overlap detected ({len(overlap)} shared chunks). "
        "Patient isolation is violated."
    )


# ---------------------------------------------------------------------------
# Test 3 — Top-k shape  (no API key needed — Chroma-level check)
# ---------------------------------------------------------------------------

def test_top_k_shape(tmp_path: Path) -> None:
    """Querying Chroma returns min(TOP_K, collection_size) chunks — never more.

    FHIR bundles have hundreds of resources (and thus hundreds of chunks), so
    for System B we assert exactly TOP_K (unlike System A where short narratives
    may yield fewer chunks than TOP_K).
    """
    chroma_base = tmp_path / "chroma"
    count = _index(chroma_base, _PID_A)
    assert count > 0, "Collection must be non-empty after indexing"

    expected_k = min(TOP_K, count)

    question = "What medication is the patient on?"
    docs, _, _ = _query_chroma(chroma_base, _PID_A, question, TOP_K)

    assert len(docs) == expected_k, (
        f"Expected {expected_k} chunks (min(TOP_K={TOP_K}, count={count})), "
        f"got {len(docs)}"
    )
    assert len(docs) <= TOP_K, (
        f"Retrieved {len(docs)} chunks — exceeds TOP_K={TOP_K}"
    )


# ---------------------------------------------------------------------------
# Test 4 — Chunk count reasonable  (NEW, specific to System B)
# ---------------------------------------------------------------------------

def test_chunk_count_reasonable(tmp_path: Path) -> None:
    """A real FHIR bundle produces at least 10 chunks.

    Catches the silent-drop bug where the serialiser skips resources and
    indexes nothing.  Patient 014abeea has 597 entries (verified empirically
    during development); the threshold is deliberately conservative (10) to
    remain valid across all patients in the frozen dataset.
    """
    chroma_base = tmp_path / "chroma"
    count = _index(chroma_base, _PID_A)
    assert count >= 10, (
        f"Expected at least 10 chunks for patient {_PID_A!r} but got {count}. "
        "This likely means the FHIR resource serialiser is silently dropping resources."
    )


# ---------------------------------------------------------------------------
# Test 5 — resource_type metadata present  (NEW, specific to System B)
# ---------------------------------------------------------------------------

def test_resource_type_metadata_present(tmp_path: Path) -> None:
    """Every retrieved chunk must have a non-empty resource_type in its metadata.

    This metadata is the hook for error-taxonomy analysis: which resource
    types were retrieved for which question categories.  If resource_type is
    missing, that analysis breaks silently.
    """
    chroma_base = tmp_path / "chroma"
    _index(chroma_base, _PID_A)

    question = "What medication is the patient on?"
    _, metas, _ = _query_chroma(chroma_base, _PID_A, question, TOP_K)

    assert len(metas) > 0, "Query must return at least one chunk for this test to be meaningful"
    for i, meta in enumerate(metas):
        rt = meta.get("resource_type", "")
        assert isinstance(rt, str) and rt.strip() != "", (
            f"Chunk at rank {i + 1} has empty or missing resource_type in metadata: {meta!r}"
        )


# ---------------------------------------------------------------------------
# Test 6 — Determinism  (requires GROQ_API_KEY)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not os.environ.get("GROQ_API_KEY"),
    reason="GROQ_API_KEY not set — skipping LLM determinism test",
)
def test_determinism(tmp_path: Path) -> None:
    """Two identical (patient, question) calls return identical answers and ranks."""
    import systems.structured_rag_naive as mod
    from systems.common.embedder import EmbeddingClient

    chroma_base = tmp_path / "chroma"
    embedder = EmbeddingClient(cache_dir=EMBEDDING_CACHE_DIR)

    original_base = mod._CHROMA_BASE
    mod._CHROMA_BASE = chroma_base
    try:
        system = mod.StructuredRAGNaive(embedder=embedder)
        question = "What medication is the patient on?"

        resp1 = system.answer(question=question, patient_id=_PID_A)
        resp2 = system.answer(question=question, patient_id=_PID_A)
    finally:
        mod._CHROMA_BASE = original_base

    assert resp1.answer == resp2.answer, (
        "Two identical calls produced different answers (non-determinism)"
    )

    ranks1 = [(r["chunk_index"], r["score"]) for r in resp1.retrieved]
    ranks2 = [(r["chunk_index"], r["score"]) for r in resp2.retrieved]
    assert ranks1 == ranks2, (
        f"Chunk ranks/scores differ across calls:\n{ranks1}\nvs\n{ranks2}"
    )

    # Second call must be an answer-cache hit
    assert resp2.extras.get("cache_hit") is True, (
        "Second identical call must hit the answer LLM cache"
    )


# ---------------------------------------------------------------------------
# Test 7 — Live end-to-end smoke test  (requires GROQ_API_KEY)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not os.environ.get("GROQ_API_KEY"),
    reason="GROQ_API_KEY not set — skipping live LLM test",
)
def test_live_end_to_end(tmp_path: Path) -> None:
    """Full pipeline smoke: non-empty, non-N/A answer for a real FHIR bundle.

    Uses "What is the patient's gender?" because Patient.gender is always
    populated in Synthea-generated FHIR bundles and is in the first resource —
    it will always be present in the indexed chunks.

    Assertion is purely mechanical — length > 0 and not the literal 'N/A'
    fallback.  No LLM-as-judge.
    """
    import systems.structured_rag_naive as mod
    from systems.common.embedder import EmbeddingClient
    from systems.base import BaseSystem

    chroma_base = tmp_path / "chroma"
    embedder = EmbeddingClient(cache_dir=EMBEDDING_CACHE_DIR)

    original_base = mod._CHROMA_BASE
    mod._CHROMA_BASE = chroma_base
    try:
        system = mod.StructuredRAGNaive(embedder=embedder)

        assert isinstance(system, BaseSystem), (
            "StructuredRAGNaive must satisfy the BaseSystem protocol"
        )

        resp = system.answer(
            question="What is the patient's gender?",
            patient_id=_PID_A,
        )
    finally:
        mod._CHROMA_BASE = original_base

    assert isinstance(resp.answer, str), "Answer must be a string"
    assert len(resp.answer.strip()) > 0, "Answer must not be empty"
    assert resp.answer.strip() != "N/A", (
        "Answer is the fallback 'N/A' — Patient.gender should always be in the "
        "FHIR bundle and thus the indexed chunks."
    )
    assert resp.tokens_in > 0, "tokens_in must be > 0 for a real LLM call"
    assert resp.latency_ms >= 0, "latency_ms must be non-negative"
    assert len(resp.retrieved) > 0, "At least one chunk must be retrieved"
    assert len(resp.retrieved) <= TOP_K, (
        f"Live answer must not exceed TOP_K={TOP_K} chunks, got {len(resp.retrieved)}"
    )


# ---------------------------------------------------------------------------
# Test 8 — BaseSystem protocol compliance  (no API key needed)
# ---------------------------------------------------------------------------

def test_base_system_protocol_compliance() -> None:
    """StructuredRAGNaive satisfies the BaseSystem protocol (duck-typed runtime check)."""
    from systems.structured_rag_naive import StructuredRAGNaive
    from systems.base import BaseSystem

    system = StructuredRAGNaive()
    assert isinstance(system, BaseSystem), (
        "StructuredRAGNaive must satisfy the BaseSystem protocol. "
        "Check that answer(question: str, patient_id: str) -> SystemResponse is implemented."
    )


# ---------------------------------------------------------------------------
# Test 9 — Harness resolves 'structured_rag_naive'  (no API key needed)
# ---------------------------------------------------------------------------

def test_harness_recognises_structured_rag_naive(tmp_path: Path) -> None:
    """The eval harness resolves 'structured_rag_naive' to a StructuredRAGNaive instance."""
    import systems.structured_rag_naive as mod
    from systems.structured_rag_naive import StructuredRAGNaive

    original_base = mod._CHROMA_BASE
    mod._CHROMA_BASE = tmp_path / "chroma"
    try:
        from eval.harness import _load_system
        system = _load_system("structured_rag_naive")
        assert isinstance(system, StructuredRAGNaive), (
            f"Expected StructuredRAGNaive from harness, got {type(system)}"
        )
    finally:
        mod._CHROMA_BASE = original_base
