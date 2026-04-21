"""Smoke tests for T2.4 — System C (Structured RAG, resource-aware).

Tests verify the StructuredRAGAware pipeline:

  1. test_indexing_is_idempotent        — twice-indexing yields one collection +
                                         one references.json; stable chunk count.
  2. test_patient_isolation             — retrieves zero chunks from another
                                         patient's collection.
  3. test_references_json_exists        — references.json is written at the
                                         expected path and is non-empty.
  4. test_router_deterministic          — same question returns the same type list
                                         on two calls.
  5. test_router_fallback_on_unmatched  — unmatched question returns [] fallback;
                                         retrieval proceeds unfiltered.
  6. test_expansion_cap_enforced        — expansion_chunks never exceed
                                         SYSTEM_C_EXPANSION_CAP=10.
  7. test_top_k_shape                   — primary chunks ≤ TOP_K=5; expansion ≤ 10.
  8. test_determinism                   — skip-on-no-GROQ; identical answer + ranks
                                         across two calls.
  9. test_live_end_to_end               — skip-on-no-GROQ; non-empty non-N/A answer.
 10. test_base_system_protocol_compliance — StructuredRAGAware satisfies BaseSystem.
 11. test_harness_recognises_structured_rag_aware — harness resolves all C aliases.

Tests 1-7, 10-11 do NOT require GROQ_API_KEY.
Tests 8-9 skip when GROQ_API_KEY is absent.

No test asserts a specific answer string. No LLM-as-judge anywhere.

Run with::

    pytest systems/tests/smoke/test_t2_4_system_c.py -v

The full smoke suite (24 pre-existing + 11 new = 35) can be verified with::

    pytest systems/tests/smoke/ -v
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import chromadb
import pytest

from eval.config import EMBEDDING_CACHE_DIR, TOP_K
from systems.structured_rag_aware import SYSTEM_C_EXPANSION_CAP

# Two patient IDs matching those used by System B's smoke tests.
# They are the first two in data/fhir_bundles/ sorted lexicographically and
# both have committed FHIR bundles (frozen at dataset-freeze-v1).
_PID_A = "014abeea-627d-f33c-834c-e2a6605046ee"
_PID_B = "02dc5960-eec7-7c95-977a-fbfef0c7318a"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_system(chroma_base: Path):
    """Return a StructuredRAGAware instance wired to *chroma_base*."""
    import systems.structured_rag_aware as mod
    from systems.common.embedder import EmbeddingClient

    embedder = EmbeddingClient(cache_dir=EMBEDDING_CACHE_DIR)
    original_base = mod._CHROMA_BASE
    mod._CHROMA_BASE = chroma_base
    try:
        system = mod.StructuredRAGAware(embedder=embedder)
    finally:
        mod._CHROMA_BASE = original_base
    return system, chroma_base


def _index(chroma_base: Path, patient_id: str) -> int:
    """Index *patient_id* under *chroma_base*; return chunk count."""
    import systems.structured_rag_aware as mod
    from systems.common.embedder import EmbeddingClient

    embedder = EmbeddingClient(cache_dir=EMBEDDING_CACHE_DIR)
    original_base = mod._CHROMA_BASE
    mod._CHROMA_BASE = chroma_base
    try:
        system = mod.StructuredRAGAware(embedder=embedder)
        system.index_patient(patient_id)
        col_name = mod._collection_name(patient_id)
    finally:
        mod._CHROMA_BASE = original_base

    client = chromadb.PersistentClient(path=str(chroma_base / patient_id))
    col = client.get_collection(col_name)
    return col.count()


def _query_chroma(
    chroma_base: Path,
    patient_id: str,
    question: str,
    k: int,
) -> tuple[list[str], list[dict], list[float]]:
    """Query Chroma directly (bypasses LLM) — returns (docs, metadatas, distances)."""
    import systems.structured_rag_aware as mod
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


def _answer_via_system(
    chroma_base: Path,
    patient_id: str,
    question: str,
):
    """Call system.answer() with chroma_base overridden to *chroma_base*."""
    import systems.structured_rag_aware as mod
    from systems.common.embedder import EmbeddingClient

    embedder = EmbeddingClient(cache_dir=EMBEDDING_CACHE_DIR)
    original_base = mod._CHROMA_BASE
    mod._CHROMA_BASE = chroma_base
    try:
        system = mod.StructuredRAGAware(embedder=embedder)
        return system.answer(question=question, patient_id=patient_id)
    finally:
        mod._CHROMA_BASE = original_base


# ---------------------------------------------------------------------------
# Test 1 — Idempotent indexing  (no API key needed)
# ---------------------------------------------------------------------------

def test_indexing_is_idempotent(tmp_path: Path) -> None:
    """Calling index_patient twice yields one collection + one references.json."""
    import systems.structured_rag_aware as mod

    chroma_base = tmp_path / "chroma"

    count_first = _index(chroma_base, _PID_A)
    assert count_first > 0, "Collection must be non-empty after first indexing"

    # references.json must exist after first call
    ref_path = chroma_base / _PID_A / "references.json"
    assert ref_path.exists(), "references.json must be written after first indexing"

    count_second = _index(chroma_base, _PID_A)
    assert count_first == count_second, (
        f"Collection size changed after second index_patient call: "
        f"{count_first} -> {count_second}"
    )

    # references.json must still exist and not have been corrupted
    assert ref_path.exists(), "references.json must persist after second index call"
    graph = json.loads(ref_path.read_text(encoding="utf-8"))
    assert isinstance(graph, dict), "references.json must contain a JSON object"


# ---------------------------------------------------------------------------
# Test 2 — Patient isolation  (no API key needed)
# ---------------------------------------------------------------------------

def test_patient_isolation(tmp_path: Path) -> None:
    """Indexing patients A and B then querying A returns only A's chunks."""
    chroma_base = tmp_path / "chroma"

    _index(chroma_base, _PID_A)
    _index(chroma_base, _PID_B)

    question = "What medication is the patient on?"
    docs_a, metas_a, _ = _query_chroma(chroma_base, _PID_A, question, TOP_K)
    docs_b, metas_b, _ = _query_chroma(chroma_base, _PID_B, question, TOP_K)

    for meta in metas_a:
        assert meta["patient_id"] == _PID_A, (
            f"Chunk from A's collection belongs to {meta['patient_id']!r}, "
            f"expected {_PID_A!r}"
        )

    for meta in metas_b:
        assert meta["patient_id"] == _PID_B, (
            f"Chunk from B's collection belongs to {meta['patient_id']!r}, "
            f"expected {_PID_B!r}"
        )

    # FHIR resources are patient-specific — no text overlap expected
    set_a = set(docs_a)
    set_b = set(docs_b)
    overlap = set_a & set_b
    assert len(overlap) == 0, (
        f"Cross-patient text overlap detected ({len(overlap)} shared chunks). "
        "Patient isolation is violated."
    )


# ---------------------------------------------------------------------------
# Test 3 — references.json exists and is non-empty  (no API key needed)
# ---------------------------------------------------------------------------

def test_references_json_exists(tmp_path: Path) -> None:
    """After indexing, references.json is at the expected path and non-empty."""
    chroma_base = tmp_path / "chroma"
    _index(chroma_base, _PID_A)

    ref_path = chroma_base / _PID_A / "references.json"
    assert ref_path.exists(), (
        f"references.json expected at {ref_path} but does not exist"
    )

    graph = json.loads(ref_path.read_text(encoding="utf-8"))
    assert isinstance(graph, dict), "references.json must be a JSON object"
    assert len(graph) > 0, (
        "references.json must be non-empty — the FHIR bundle has many resources "
        "and at least some will have outbound references"
    )

    # Every value must be a list (possibly empty) of strings
    for rid, refs in graph.items():
        assert isinstance(rid, str), f"Key {rid!r} must be a string"
        assert isinstance(refs, list), (
            f"Value for {rid!r} must be a list, got {type(refs)}"
        )
        for ref in refs:
            assert isinstance(ref, str), (
                f"Reference {ref!r} in {rid!r}'s list must be a string"
            )


# ---------------------------------------------------------------------------
# Test 4 — Router determinism  (no API key needed)
# ---------------------------------------------------------------------------

def test_router_deterministic() -> None:
    """Same question returns the same resource-type list across two calls."""
    from systems.structured_rag_aware import route_question

    questions = [
        "What is the patient's gender?",
        "What is the last dose of the medication?",
        "What conditions has the patient been diagnosed with?",
        "What is the patient's current prescription regimen?",
        "xyzzy randomstring that matches nothing specific",
    ]

    for q in questions:
        result1 = route_question(q)
        result2 = route_question(q)
        assert result1 == result2, (
            f"Router returned different results for {q!r}: {result1} vs {result2}"
        )
        # Both calls must return a list
        assert isinstance(result1, list), (
            f"Router must return a list, got {type(result1)} for {q!r}"
        )


# ---------------------------------------------------------------------------
# Test 5 — Router fallback on unmatched question  (no API key needed)
# ---------------------------------------------------------------------------

def test_router_fallback_on_unmatched_question(tmp_path: Path) -> None:
    """An unrecognised question returns [] (empty fallback) and retrieval is unfiltered."""
    from systems.structured_rag_aware import route_question

    # A completely artificial string that matches none of the specific patterns
    # but is guaranteed to match the catch-all fallback.
    unmatched = "xyzzy frobnicator quux 12345"
    types = route_question(unmatched)

    # The fallback must return an empty list
    assert types == [], (
        f"Fallback pattern must return [], got {types!r} for {unmatched!r}"
    )

    # Verify that retrieval works with an empty type filter (no crash)
    chroma_base = tmp_path / "chroma"
    _index(chroma_base, _PID_A)
    docs, metas, distances = _query_chroma(chroma_base, _PID_A, unmatched, TOP_K)

    # Retrieval must return some chunks (the collection has hundreds)
    assert len(docs) > 0, (
        "Fallback (unfiltered) retrieval must return at least one chunk"
    )
    assert len(docs) <= TOP_K, (
        f"Fallback retrieval must not exceed TOP_K={TOP_K} chunks"
    )


# ---------------------------------------------------------------------------
# Retrieval-layer helpers (no LLM; call internal methods directly)
# ---------------------------------------------------------------------------

def _retrieve_and_expand(
    chroma_base: Path,
    patient_id: str,
    question: str,
) -> tuple[list[dict], list[dict]]:
    """Run the retrieval + expansion phase without calling the answer LLM.

    Returns (primary_chunks, expansion_chunks).
    Bypasses answer_llm_ask entirely — safe to call without GROQ_API_KEY.
    """
    import systems.structured_rag_aware as mod
    from systems.common.embedder import EmbeddingClient

    embedder = EmbeddingClient(cache_dir=EMBEDDING_CACHE_DIR)
    original_base = mod._CHROMA_BASE
    mod._CHROMA_BASE = chroma_base
    try:
        system = mod.StructuredRAGAware(embedder=embedder)
        system.index_patient(patient_id)

        q_vec = embedder.embed_one(question)
        q_vec_list = q_vec.tolist()

        client = mod._open_client(patient_id)
        col_name = mod._collection_name(patient_id)
        collection = client.get_or_create_collection(
            name=col_name,
            metadata={"hnsw:space": "cosine"},
        )
        total_count = collection.count()

        type_filter = mod.route_question(question)
        primary = system._retrieve_primary(
            collection=collection,
            q_vec_list=q_vec_list,
            type_filter=type_filter,
            total_count=total_count,
            patient_id=patient_id,
        )
        ref_graph = mod._load_reference_graph(patient_id)
        expansion = system._expand_references(
            collection=collection,
            primary_chunks=primary,
            ref_graph=ref_graph,
        )
        return primary, expansion
    finally:
        mod._CHROMA_BASE = original_base


# ---------------------------------------------------------------------------
# Test 6 — Expansion cap enforced  (no API key needed)
# ---------------------------------------------------------------------------

def test_expansion_cap_enforced(tmp_path: Path) -> None:
    """Expansion chunks are always <= SYSTEM_C_EXPANSION_CAP regardless of fan-out.

    MedicationAdministration resources each reference ~4 resources
    (Patient, Encounter, Medication, MedicationRequest), and the bundle has
    252 such resources.  If expansion were uncapped the context would explode.
    This test verifies the cap holds.  The LLM is not called — retrieval only.
    """
    chroma_base = tmp_path / "chroma"
    _index(chroma_base, _PID_A)

    # Use a question that routes to MedicationAdministration (high fan-out)
    primary, expansion = _retrieve_and_expand(
        chroma_base,
        _PID_A,
        "What was the last dose administered?",
    )

    assert len(expansion) <= SYSTEM_C_EXPANSION_CAP, (
        f"Expansion chunks ({len(expansion)}) exceed cap ({SYSTEM_C_EXPANSION_CAP}). "
        "The cap guard in _expand_references is broken."
    )
    # All expansion chunks must have role="expansion"
    for chunk in expansion:
        assert chunk.get("role") == "expansion", (
            f"Expansion chunk missing role='expansion': {chunk!r}"
        )


# ---------------------------------------------------------------------------
# Test 7 — Top-k shape  (no API key needed)
# ---------------------------------------------------------------------------

def test_top_k_shape(tmp_path: Path) -> None:
    """Primary chunks <= TOP_K; expansion chunks <= SYSTEM_C_EXPANSION_CAP.

    The LLM is not called — retrieval layer only.
    """
    chroma_base = tmp_path / "chroma"
    count = _index(chroma_base, _PID_A)
    assert count > 0, "Collection must be non-empty after indexing"

    question = "What medication is the patient on?"
    primary, expansion = _retrieve_and_expand(chroma_base, _PID_A, question)

    assert len(primary) <= TOP_K, (
        f"Primary chunks ({len(primary)}) exceed TOP_K={TOP_K}"
    )
    assert len(primary) > 0, "Must retrieve at least one primary chunk"

    assert len(expansion) <= SYSTEM_C_EXPANSION_CAP, (
        f"Expansion chunks ({len(expansion)}) exceed cap={SYSTEM_C_EXPANSION_CAP}"
    )

    # Verify role tagging
    for chunk in primary:
        assert chunk.get("role") == "primary", (
            f"Primary chunk missing role='primary': {chunk!r}"
        )
    for chunk in expansion:
        assert chunk.get("role") == "expansion", (
            f"Expansion chunk missing role='expansion': {chunk!r}"
        )


# ---------------------------------------------------------------------------
# Test 8 — Determinism  (requires GROQ_API_KEY)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not os.environ.get("GROQ_API_KEY"),
    reason="GROQ_API_KEY not set — skipping LLM determinism test",
)
def test_determinism(tmp_path: Path) -> None:
    """Two identical (patient, question) calls return identical answers and chunk ranks."""
    chroma_base = tmp_path / "chroma"

    question = "What medication is the patient on?"
    resp1 = _answer_via_system(chroma_base, _PID_A, question)
    resp2 = _answer_via_system(chroma_base, _PID_A, question)

    assert resp1.answer == resp2.answer, (
        "Two identical calls produced different answers (non-determinism)"
    )

    # Primary chunk ranks must be stable
    ranks1 = [(r["chunk_index"], r["score"]) for r in resp1.retrieved]
    ranks2 = [(r["chunk_index"], r["score"]) for r in resp2.retrieved]
    assert ranks1 == ranks2, (
        f"Primary chunk ranks/scores differ across calls:\n{ranks1}\nvs\n{ranks2}"
    )

    # Expansion chunk sets must be stable (same resource_ids in same order)
    exp_rids1 = [c.get("resource_id") for c in resp1.extras.get("expansion_chunks", [])]
    exp_rids2 = [c.get("resource_id") for c in resp2.extras.get("expansion_chunks", [])]
    assert exp_rids1 == exp_rids2, (
        f"Expansion resource_ids differ across calls:\n{exp_rids1}\nvs\n{exp_rids2}"
    )

    # Second call must be an answer-cache hit
    assert resp2.extras.get("cache_hit") is True, (
        "Second identical call must hit the answer LLM cache"
    )


# ---------------------------------------------------------------------------
# Test 9 — Live end-to-end  (requires GROQ_API_KEY)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not os.environ.get("GROQ_API_KEY"),
    reason="GROQ_API_KEY not set — skipping live LLM test",
)
def test_live_end_to_end(tmp_path: Path) -> None:
    """Full pipeline smoke: non-empty, non-N/A answer for a real FHIR bundle.

    Uses "What is the patient's gender?" because Patient.gender is always
    populated in Synthea-generated FHIR bundles.

    Assertion is purely mechanical — no LLM-as-judge.
    """
    from systems.base import BaseSystem

    chroma_base = tmp_path / "chroma"
    resp = _answer_via_system(
        chroma_base, _PID_A, "What is the patient's gender?"
    )

    assert isinstance(resp.answer, str), "Answer must be a string"
    assert len(resp.answer.strip()) > 0, "Answer must not be empty"
    assert resp.answer.strip() != "N/A", (
        "Answer is the fallback 'N/A' — Patient.gender must be in the FHIR bundle"
    )
    assert resp.tokens_in > 0, "tokens_in must be > 0 for a real LLM call"
    assert resp.latency_ms >= 0, "latency_ms must be non-negative"
    assert len(resp.retrieved) > 0, "At least one primary chunk must be retrieved"
    assert len(resp.retrieved) <= TOP_K, (
        f"Primary chunks must not exceed TOP_K={TOP_K}"
    )
    expansion = resp.extras.get("expansion_chunks", [])
    assert len(expansion) <= SYSTEM_C_EXPANSION_CAP, (
        f"Expansion chunks must not exceed cap={SYSTEM_C_EXPANSION_CAP}"
    )


# ---------------------------------------------------------------------------
# Test 10 — BaseSystem protocol compliance  (no API key needed)
# ---------------------------------------------------------------------------

def test_base_system_protocol_compliance() -> None:
    """StructuredRAGAware satisfies the BaseSystem protocol."""
    from systems.structured_rag_aware import StructuredRAGAware
    from systems.base import BaseSystem

    system = StructuredRAGAware()
    assert isinstance(system, BaseSystem), (
        "StructuredRAGAware must satisfy the BaseSystem protocol. "
        "Check that answer(question: str, patient_id: str) -> SystemResponse is implemented."
    )


# ---------------------------------------------------------------------------
# Test 11 — Harness resolves all System C aliases  (no API key needed)
# ---------------------------------------------------------------------------

def test_harness_recognises_structured_rag_aware(tmp_path: Path) -> None:
    """The eval harness resolves all System C aliases to StructuredRAGAware."""
    import systems.structured_rag_aware as mod
    from systems.structured_rag_aware import StructuredRAGAware

    original_base = mod._CHROMA_BASE
    mod._CHROMA_BASE = tmp_path / "chroma"
    try:
        from eval.harness import _load_system

        for alias in ("c", "aware", "structured_rag_aware"):
            system = _load_system(alias)
            assert isinstance(system, StructuredRAGAware), (
                f"Harness alias {alias!r} did not return StructuredRAGAware, "
                f"got {type(system)}"
            )
    finally:
        mod._CHROMA_BASE = original_base
