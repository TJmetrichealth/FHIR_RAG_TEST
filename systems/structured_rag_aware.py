"""System C — Structured RAG (resource-aware).

Scientific role in the paper:
  System C is the "aware structured" intervention. It ingests the same FHIR
  bundles as System B and uses the *same* serialisation (``json.dumps`` with
  ``sort_keys=True, indent=2``), the *same* chunker, and the *same* answer LLM.
  The only differences from B are:

    1. Resource-type-aware retrieval: a deterministic regex router routes each
       question to a prioritised set of resource types; Chroma's ``$in`` filter
       restricts the candidate pool before similarity ranking.

    2. One-hop reference expansion: after top-k retrieval, the reference graph
       (built at index time) is walked one hop to fetch chunks from resources
       referenced by the primary hits.  These expansion chunks are appended to
       the context in a clearly marked section so the answer LLM can see the
       local FHIR subgraph, not just isolated resource snapshots.

  Those two mechanisms — and nothing else — constitute the "awareness" claim.
  Adding BM25, re-ranking, hybrid search, or query decomposition is explicitly
  forbidden: it would contaminate the B-vs-C methodological contrast.

  The A-vs-B-vs-C contrast the paper makes:
    A: LLM narrative → flat chunks → retrieve
    B: FHIR resources → JSON-dump → flat chunks → retrieve
    C: FHIR resources → type-filtered + reference-expanded retrieve  ← this module

Expansion cap:
  Hard-capped at SYSTEM_C_EXPANSION_CAP = 10 expansion chunks total, enforced
  across all referenced resources combined.  When more expansion candidates are
  available, they are selected in reference-graph traversal order (the order we
  encounter resource_ids in the expansion loop), taking the first-ranked chunk
  per resource (chunk_index=0) first, then chunk_index=1, etc.  This is a
  deliberate FIFO-by-resource-then-rank order rather than re-scoring — we do
  not re-rank expansion chunks with the embedder because that would introduce a
  second similarity pass that B lacks, polluting the contrast.

  SYSTEM_C_EXPANSION_CAP is kept as a module-level constant (not in eval.config)
  because it is a C-only implementation detail with no direct equivalent in A
  or B.  If the planner decides to expose it as a sweep variable in the W3
  ablation, it should be moved to eval.config under that decision-log entry.
  FLAG for planner: SYSTEM_C_EXPANSION_CAP = 10 (module constant, not config).

Provenance reporting:
  ``SystemResponse.retrieved`` contains the primary top-k chunks with
  ``role="primary"`` on each dict.
  ``SystemResponse.extras["expansion_chunks"]`` contains the expansion chunks
  with ``role="expansion"`` on each dict.
  The evaluator in W3 can inspect both fields independently.
  This avoids modifying base.py while keeping the W3 evaluator's needs met.

Reference graph:
  Built once at index time; stored as a JSON file at:
    ``systems/structured_aware/chroma/{patient_id}/references.json``
  Schema: ``{"resource_id": ["referenced_id_1", "referenced_id_2", ...], ...}``
  Chroma metadata is scalar-only; the graph is stored out-of-band in this file.

Chunk IDs:
  Same format as System B: ``{resourceType}_{resource_id}::chunk_{i}``
  This guarantees that if System C's embedding text is byte-identical to B's
  for the same resource (invariant: same serialisation), the embedding cache
  from B's indexing run will be hit during C's indexing — avoiding redundant
  GPU compute.

ChromaDB collection:
  Per-patient collection at ``systems/structured_aware/chroma/{patient_id}/``.
  Collection name: ``sva_{patient_id[:8]}``  (prefix "sva" = structured-aware).
  Naming mirrors B's "snv_" convention — distinct prefix so A, B, C collections
  never collide even if pointed at the same Chroma directory.

QUESTION_TYPE_ROUTER (methodology artefact — see module constant below):
  The router is a module-level ordered list of (regex_pattern, resource_type_list)
  pairs.  First-match-wins.  The last entry is the fallback (empty list = no filter).
  The router uses compiled regexes (case-insensitive) for determinism.
  It is NOT an LLM; it is a static lookup table.  This is intentional: the
  scientific claim is that even a crude mechanical schema-aware router measurably
  helps, isolating *schema knowledge* as the causal intervention.

No new tunable hyperparameters beyond SYSTEM_C_EXPANSION_CAP (documented above
and flagged for planner).  All other constants (TOP_K, CHUNK_TOKENS, etc.) come
from eval.config as in A and B.
"""
from __future__ import annotations

import json
import re
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
# Module-level constants
# ---------------------------------------------------------------------------

# Base directory for all System C ChromaDB collections.
_CHROMA_BASE: Path = PROJECT_ROOT / "systems" / "structured_aware" / "chroma"

# Collection name prefix.  "sva" = structured-aware.
# 3 chars + 8 hex chars = 11 chars — within Chroma's 3-63 limit.
_COLLECTION_PREFIX: str = "sva_"

# Chunk separator used when concatenating top-k chunks for the LLM context.
# Identical to Systems A and B — controlled variable.
_CHUNK_SEPARATOR: str = "\n\n---\n\n"

# Separator between primary context block and reference-expansion block.
_EXPANSION_SEPARATOR: str = "\n\n=== Referenced resources ===\n\n"

# Hard cap on expansion chunks (C-only implementation detail).
# FLAG for planner: this is NOT in eval.config; decision-log entry required if
# it becomes a W3 ablation sweep variable.
SYSTEM_C_EXPANSION_CAP: int = 10

# ---------------------------------------------------------------------------
# QUESTION_TYPE_ROUTER
#
# Methodology-critical artefact — described verbatim in the paper methods.
# Order: first-match-wins (most specific patterns first).
# Fallback: empty list (no type filter — degrades to B-like flat retrieval).
#
# Rules for this table:
#   - Each pattern is a compiled case-insensitive regex.
#   - The resource-type list is the prioritised candidate set for Chroma's $in
#     filter; ordering within the list does not affect Chroma (it's an OR filter).
#   - Do NOT add patterns that require LLM interpretation. Text-matching only.
#   - Do NOT sort results by type within the list — Chroma's ANN handles ranking.
# ---------------------------------------------------------------------------

QUESTION_TYPE_ROUTER: list[tuple[re.Pattern[str], list[str]]] = [
    # Administration / dose / adherence — narrow to administration events first
    (
        re.compile(
            r"\b(dose|administration|administered|missed|last dose|next dose"
            r"|inject|injection|infusion|taken|dispens)\b",
            re.IGNORECASE,
        ),
        ["MedicationAdministration", "MedicationRequest"],
    ),
    # Prescription / regimen / plan — still medication-centric but higher-level
    (
        re.compile(
            r"\b(prescription|prescrib|regimen|schedule|cycle|tier"
            r"|specialty medication|care plan|careplan)\b",
            re.IGNORECASE,
        ),
        ["MedicationRequest", "CarePlan", "Medication"],
    ),
    # Encounter / visit
    (
        re.compile(
            r"\b(encounter|visit|appointment|hospitali|inpatient|outpatient)\b",
            re.IGNORECASE,
        ),
        ["Encounter"],
    ),
    # Condition / diagnosis
    (
        re.compile(
            r"\b(condition|diagnosis|diagnos|disease|disorder|problem|complaint)\b",
            re.IGNORECASE,
        ),
        ["Condition"],
    ),
    # Observations / lab / vitals
    (
        re.compile(
            r"\b(observation|lab|laboratory|test|result|value|vital|weight"
            r"|height|bmi|blood pressure|glucose)\b",
            re.IGNORECASE,
        ),
        ["Observation", "DiagnosticReport"],
    ),
    # Immunisation
    (
        re.compile(
            r"\b(immunization|immunisation|vaccine|vaccination)\b",
            re.IGNORECASE,
        ),
        ["Immunization"],
    ),
    # Procedure
    (
        re.compile(
            r"\b(procedure|surgery|operation|intervention)\b",
            re.IGNORECASE,
        ),
        ["Procedure"],
    ),
    # Patient demographics — gender / age / DOB etc.
    (
        re.compile(
            r"\b(gender|sex|birthdate|date.of.birth|dob|age|born|name"
            r"|address|patient)\b",
            re.IGNORECASE,
        ),
        ["Patient"],
    ),
    # Generic medication keyword (catch-all for drug-related questions that
    # didn't match the more specific administration/prescription patterns above)
    (
        re.compile(
            r"\b(medication|drug|medicine|pharmaceutical|biologic|therapy)\b",
            re.IGNORECASE,
        ),
        ["Medication", "MedicationRequest"],
    ),
    # Fallback — no filter; retrieval proceeds across all resource types (B-like)
    (
        re.compile(r".*", re.DOTALL),
        [],  # empty list signals "no type filter"
    ),
]


# ---------------------------------------------------------------------------
# Reference-graph helpers
# ---------------------------------------------------------------------------

def _find_references_in_obj(obj: Any, refs: set[str]) -> None:
    """Recursively walk *obj* and collect every ``reference`` string value."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "reference" and isinstance(v, str):
                refs.add(v)
            else:
                _find_references_in_obj(v, refs)
    elif isinstance(obj, list):
        for item in obj:
            _find_references_in_obj(item, refs)


def _normalize_reference(ref_str: str, fullurl_to_id: dict[str, str]) -> str | None:
    """Normalise a FHIR reference string to a bare resource id.

    Handles three formats:
      1. ``"ResourceType/id"``      → returns ``id``
      2. ``"urn:uuid:xxx"``         → resolves via *fullurl_to_id*
      3. Conditional / search refs  → returns None (not resolvable)

    Returns None for unresolvable references so callers can skip them cleanly.
    """
    if ref_str.startswith("urn:uuid:"):
        return fullurl_to_id.get(ref_str)

    if "?" in ref_str:
        # Conditional reference — not resolvable without a server
        return None

    if "/" in ref_str:
        parts = ref_str.split("/", 1)
        if len(parts) == 2 and parts[1]:
            return parts[1]  # bare resource id

    return None


def _build_reference_graph(
    entries: list[dict[str, Any]],
) -> dict[str, list[str]]:
    """Build the outbound reference graph for a FHIR bundle.

    Parameters
    ----------
    entries:
        The ``bundle["entry"]`` list from a FHIR bundle.

    Returns
    -------
    dict[str, list[str]]
        Maps each resource's bare id to a sorted list of bare ids it references.
        Resources with no resolvable outbound references map to ``[]``.
    """
    # Build fullUrl → bare-id index for urn:uuid resolution
    fullurl_to_id: dict[str, str] = {}
    for entry in entries:
        full_url = entry.get("fullUrl", "")
        resource = entry.get("resource", {})
        rid = resource.get("id", "")
        if full_url and rid:
            fullurl_to_id[full_url] = rid

    references: dict[str, list[str]] = {}
    for entry in entries:
        resource = entry.get("resource", {})
        rid = resource.get("id", "")
        if not rid:
            continue

        raw_refs: set[str] = set()
        _find_references_in_obj(resource, raw_refs)

        resolved: set[str] = set()
        for raw in raw_refs:
            norm = _normalize_reference(raw, fullurl_to_id)
            if norm and norm != rid:  # skip self-references
                resolved.add(norm)

        references[rid] = sorted(resolved)

    return references


def _references_path(patient_id: str) -> Path:
    """Return the path to the references.json side-table for *patient_id*."""
    return _CHROMA_BASE / patient_id / "references.json"


def _load_reference_graph(patient_id: str) -> dict[str, list[str]]:
    """Load the reference graph from disk.  Returns {} if file missing."""
    p = _references_path(patient_id)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# ChromaDB helpers (same pattern as System B)
# ---------------------------------------------------------------------------

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

    INVARIANT: byte-identical to System B's _resource_text().
    Uses ``json.dumps(resource, indent=2, sort_keys=True, ensure_ascii=False)``.
    Same serialisation ensures the embedding cache from a prior B indexing run
    is hit during C's indexing — no redundant GPU compute.
    """
    return json.dumps(resource, indent=2, sort_keys=True, ensure_ascii=False)


def _safe_resource_id(resource: dict[str, Any]) -> str:
    """Return a filesystem/Chroma-safe resource id string.

    Falls back to the resourceType when the resource has no ``id`` field.
    Same logic as System B.
    """
    rid = resource.get("id", "")
    if rid:
        return rid
    return resource.get("resourceType", "unknown")


# ---------------------------------------------------------------------------
# Router helpers
# ---------------------------------------------------------------------------

def route_question(question: str) -> list[str]:
    """Apply QUESTION_TYPE_ROUTER to *question*; return the resource type list.

    Returns the type list of the first matching pattern.  Returns ``[]`` for
    the fallback pattern (no filter — all resource types allowed).

    This function is deterministic: same question → same list, always.
    It is called at query time, not at index time.
    """
    for pattern, types in QUESTION_TYPE_ROUTER:
        if pattern.search(question):
            return types
    # Should never reach here because the catch-all pattern matches everything,
    # but be safe:
    return []


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class StructuredRAGAware:
    """System C: resource-type-filtered + reference-expanded FHIR RAG.

    Satisfies the ``BaseSystem`` protocol from ``systems.base`` via structural
    subtyping (duck typing).  No inheritance needed.

    Controlled variables (identical to Systems A and B):
    - Embedding model: BAAI/bge-large-en-v1.5 (via shared EmbeddingClient)
    - Chunk size / overlap: CHUNK_TOKENS=500, CHUNK_OVERLAP_TOKENS=50
    - TOP_K: 5
    - Answer LLM: qwen/qwen3-32b at temperature 0.0
    - Chunk separator: "\\n\\n---\\n\\n"
    - ChromaDB metric: cosine (hnsw:space=cosine)
    - Serialisation: json.dumps(indent=2, sort_keys=True, ensure_ascii=False)

    Differences from System B:
    1. Resource-type filter at retrieval time (QUESTION_TYPE_ROUTER).
    2. One-hop reference expansion after top-k retrieval.
    3. expansion_chunks in extras (provenance for W3 evaluator).

    Parameters
    ----------
    embedder:
        Optional pre-constructed EmbeddingClient.  Defaults to a fresh client
        using the config defaults.  Inject in tests to control the cache dir.
    """

    #: Identifier used by the harness for result records.
    name: str = "system_c_structured_aware"

    def __init__(self, embedder: EmbeddingClient | None = None) -> None:
        self._embedder = embedder or EmbeddingClient()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def index_patient(self, patient_id: str) -> None:
        """Build (or verify) the ChromaDB collection for *patient_id*.

        Also writes (or verifies) the ``references.json`` side-table.

        Idempotent: if the collection already contains at least one document
        *and* references.json already exists, returns immediately.

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

        ref_path = _references_path(patient_id)

        # Idempotency guard: skip if already indexed and references exist
        if collection.count() > 0 and ref_path.exists():
            return

        # Load bundle
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        entries: list[dict[str, Any]] = bundle.get("entry", [])

        # Build and write the reference graph (idempotent if already written)
        if not ref_path.exists():
            ref_graph = _build_reference_graph(entries)
            ref_path.parent.mkdir(parents=True, exist_ok=True)
            ref_path.write_text(
                json.dumps(ref_graph, indent=2, sort_keys=True, ensure_ascii=False),
                encoding="utf-8",
            )

        # Skip collection build if already indexed
        if collection.count() > 0:
            return

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

            # Serialise — byte-identical to System B (embedding cache invariant)
            text = _resource_text(resource)

            # Chunk via the shared chunker (same parameters as B)
            chunks = chunk_text(text, source_id=resource_id)
            if not chunks:
                continue

            for chunk in chunks:
                # Chunk ID format identical to System B
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
            return

        # Embed all chunks (batch; cache on disk — hits B's cache if B ran first)
        embeddings: list[np.ndarray] = self._embedder.embed_batch(all_texts)
        embedding_lists: list[list[float]] = [e.tolist() for e in embeddings]

        collection.add(
            ids=all_ids,
            embeddings=embedding_lists,
            documents=all_texts,
            metadatas=all_metas,
        )

    def answer(self, question: str, patient_id: str) -> SystemResponse:
        """Answer *question* for *patient_id* using resource-aware RAG.

        Pipeline:
          1. Ensure indexed (idempotent).
          2. Embed the question.
          3. Route the question to a resource-type set via QUESTION_TYPE_ROUTER.
          4. Query Chroma with a type filter (if non-empty); back off to
             unfiltered if fewer than TOP_K hits from the filtered pool.
          5. One-hop reference expansion (capped at SYSTEM_C_EXPANSION_CAP).
          6. Build context: primary block + expansion block.
          7. Call answer LLM (cached).
          8. Return SystemResponse with expansion_chunks in extras.

        Parameters
        ----------
        question:
            Natural-language question string.
        patient_id:
            UUID string identifying the patient.

        Returns
        -------
        SystemResponse
            answer, retrieved chunks (primary hits, role="primary"),
            tokens_in, tokens_out, latency_ms.
            extras["expansion_chunks"]: expansion chunks (role="expansion").
        """
        t0 = time.perf_counter()

        # Ensure indexed (idempotent)
        self.index_patient(patient_id)

        # Embed the question
        q_vec: np.ndarray = self._embedder.embed_one(question)
        q_vec_list: list[float] = q_vec.tolist()

        # Open Chroma collection
        client = _open_client(patient_id)
        col_name = _collection_name(patient_id)
        collection = client.get_or_create_collection(
            name=col_name,
            metadata={"hnsw:space": "cosine"},
        )

        total_count = collection.count()

        # --- Step 3: route question to resource types ---
        type_filter: list[str] = route_question(question)

        # --- Step 4: filtered retrieval with backoff ---
        primary_chunks = self._retrieve_primary(
            collection=collection,
            q_vec_list=q_vec_list,
            type_filter=type_filter,
            total_count=total_count,
            patient_id=patient_id,
        )

        # --- Step 5: one-hop reference expansion ---
        ref_graph = _load_reference_graph(patient_id)
        expansion_chunks = self._expand_references(
            collection=collection,
            primary_chunks=primary_chunks,
            ref_graph=ref_graph,
        )

        # --- Step 6: build context string ---
        primary_texts = [c["text"] for c in primary_chunks]
        expansion_texts = [c["text"] for c in expansion_chunks]

        context_parts = [_CHUNK_SEPARATOR.join(primary_texts)]
        if expansion_texts:
            context_parts.append(_EXPANSION_SEPARATOR)
            context_parts.append(_CHUNK_SEPARATOR.join(expansion_texts))

        context = "".join(context_parts)

        # --- Step 7: answer LLM (cached) ---
        llm_result = answer_llm_ask(question=question, context=context)

        latency_ms = (time.perf_counter() - t0) * 1000.0

        return SystemResponse(
            answer=llm_result.answer,
            retrieved=primary_chunks,
            tokens_in=llm_result.tokens_in,
            tokens_out=llm_result.tokens_out,
            latency_ms=latency_ms,
            extras={
                "system": self.name,
                "cache_hit": llm_result.cache_hit,
                "prompt_sha256": llm_result.prompt_sha256,
                "n_chunks_indexed": total_count,
                "n_chunks_retrieved": len(primary_chunks),
                "n_expansion_chunks": len(expansion_chunks),
                "type_filter": type_filter,
                "expansion_chunks": expansion_chunks,
            },
        )

    # ------------------------------------------------------------------
    # Internal retrieval helpers
    # ------------------------------------------------------------------

    def _retrieve_primary(
        self,
        *,
        collection: chromadb.Collection,
        q_vec_list: list[float],
        type_filter: list[str],
        total_count: int,
        patient_id: str,
    ) -> list[dict[str, Any]]:
        """Retrieve top-k primary chunks with optional type filter + backoff.

        If *type_filter* is non-empty, queries Chroma with a ``$in`` filter.
        If the filtered pool yields fewer than TOP_K chunks, issues a second
        unfiltered query and unions the results (dedup by chunk id).

        Returns a list of at most TOP_K dicts (rank-annotated, role="primary").
        """
        if total_count == 0:
            return []

        seen_ids: set[str] = set()
        results: list[dict[str, Any]] = []

        # --- Filtered pass ---
        if type_filter:
            where_filter: dict[str, Any] = {"resource_type": {"$in": type_filter}}
            n_filtered = min(TOP_K, total_count)
            try:
                qr = collection.query(
                    query_embeddings=[q_vec_list],
                    n_results=n_filtered,
                    where=where_filter,
                    include=["documents", "metadatas", "distances"],
                )
                results = self._unpack_query_result(qr, seen_ids, patient_id)
            except Exception:
                # If filtered query fails (e.g. type not present in collection),
                # fall through to unfiltered pass below.
                pass

        # --- Backoff / unfiltered pass (always runs if results < TOP_K) ---
        if len(results) < TOP_K and total_count > len(results):
            n_unfiltered = min(TOP_K, total_count)
            qr2 = collection.query(
                query_embeddings=[q_vec_list],
                n_results=n_unfiltered,
                include=["documents", "metadatas", "distances"],
            )
            fallback = self._unpack_query_result(qr2, seen_ids, patient_id)
            results.extend(fallback)
            results = results[:TOP_K]  # trim to TOP_K after union

        # Annotate with rank and role
        for rank, chunk in enumerate(results, start=1):
            chunk["rank"] = rank
            chunk["role"] = "primary"

        return results

    def _expand_references(
        self,
        *,
        collection: chromadb.Collection,
        primary_chunks: list[dict[str, Any]],
        ref_graph: dict[str, list[str]],
    ) -> list[dict[str, Any]]:
        """One-hop reference expansion.

        For each primary chunk, looks up its ``resource_id`` in *ref_graph* and
        fetches all chunks belonging to referenced resources from *collection*.

        Expansion order: we iterate primary chunks in rank order (rank 1 first),
        then for each referenced resource_id, we fetch chunks sorted by
        chunk_index.  We add chunks in this order until SYSTEM_C_EXPANSION_CAP
        is reached.  This is FIFO-by-rank-then-resource-then-chunk; no
        re-embedding or re-ranking occurs.

        Returns a list of at most SYSTEM_C_EXPANSION_CAP dicts (role="expansion").
        Chunks already in *primary_chunks* are excluded (dedup by chunk id).
        """
        if not ref_graph:
            return []

        # Collect all resource_ids from primary hits
        primary_resource_ids: set[str] = {
            c.get("resource_id", "") for c in primary_chunks
        }
        # Collect chunk ids already in primary to avoid duplication
        primary_chunk_ids: set[str] = {
            f"{c.get('resource_type', '')}_{c.get('resource_id', '')}::chunk_{c.get('chunk_index', '')}"
            for c in primary_chunks
        }

        # Build ordered list of referenced resource_ids to fetch
        # (deduplicated, ordered by first encounter)
        seen_resource_ids: set[str] = set(primary_resource_ids)
        expansion_resource_ids: list[str] = []
        for chunk in primary_chunks:
            rid = chunk.get("resource_id", "")
            for ref_rid in ref_graph.get(rid, []):
                if ref_rid not in seen_resource_ids:
                    expansion_resource_ids.append(ref_rid)
                    seen_resource_ids.add(ref_rid)

        if not expansion_resource_ids:
            return []

        expansion_chunks: list[dict[str, Any]] = []

        for ref_rid in expansion_resource_ids:
            if len(expansion_chunks) >= SYSTEM_C_EXPANSION_CAP:
                break

            # Fetch all chunks for this resource_id from the collection
            try:
                get_result = collection.get(
                    where={"resource_id": {"$eq": ref_rid}},
                    include=["documents", "metadatas", "ids"],
                )
            except Exception:
                continue

            fetched_ids: list[str] = get_result.get("ids", [])
            fetched_docs: list[str] = get_result.get("documents", [])
            fetched_metas: list[dict[str, Any]] = get_result.get("metadatas", [])

            if not fetched_ids:
                continue

            # Sort fetched chunks by chunk_index (ascending) for determinism
            triplets = sorted(
                zip(fetched_ids, fetched_docs, fetched_metas),
                key=lambda t: int(t[2].get("chunk_index", 0)),
            )

            for cid, doc, meta in triplets:
                if len(expansion_chunks) >= SYSTEM_C_EXPANSION_CAP:
                    break
                if cid in primary_chunk_ids:
                    continue
                expansion_chunks.append(
                    {
                        "text": doc,
                        "source_id": meta.get("source_id", ""),
                        "resource_type": meta.get("resource_type", ""),
                        "resource_id": meta.get("resource_id", ref_rid),
                        "chunk_index": meta.get("chunk_index", ""),
                        "score": None,  # expansion chunks are not similarity-ranked
                        "rank": None,   # no rank — expansion is not ordered by score
                        "patient_id": meta.get("patient_id", ""),
                        "role": "expansion",
                    }
                )

        return expansion_chunks

    @staticmethod
    def _unpack_query_result(
        qr: dict[str, Any],
        seen_ids: set[str],
        patient_id: str,
    ) -> list[dict[str, Any]]:
        """Convert a Chroma query result into chunk dicts, deduplicating by id.

        Updates *seen_ids* in place (so callers can union multiple query passes).
        Does NOT set rank or role — caller assigns those after unioning.
        """
        docs: list[str] = qr.get("documents", [[]])[0]
        distances: list[float] = qr.get("distances", [[]])[0]
        metas: list[dict[str, Any]] = qr.get("metadatas", [[]])[0]
        ids: list[str] = qr.get("ids", [[]])[0]

        chunks: list[dict[str, Any]] = []
        for cid, doc, dist, meta in zip(ids, docs, distances, metas):
            if cid in seen_ids:
                continue
            seen_ids.add(cid)
            similarity = 1.0 - dist
            chunks.append(
                {
                    "text": doc,
                    "source_id": meta.get("source_id", patient_id),
                    "resource_type": meta.get("resource_type", ""),
                    "resource_id": meta.get("resource_id", ""),
                    "chunk_index": meta.get("chunk_index", ""),
                    "score": round(similarity, 6),
                    "patient_id": meta.get("patient_id", patient_id),
                    # rank and role set by caller
                }
            )
        return chunks
