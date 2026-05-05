"""case_manager_qa.py — System C as a FastAPI endpoint for metricCONNECT.

This module wraps ``systems.structured_rag_aware.StructuredRAGAware`` (System C)
behind a FastAPI router so it can be mounted into the metricCONNECT application
without modification to the retrieval logic.

Scientific invariants preserved:
  - The ``StructuredRAGAware.answer()`` call is the *only* retrieval entrypoint.
    No hyperparameters, prompt text, or embedding model are touched here.
  - The answer LLM is reached exclusively through ``systems.common.answer_llm.ask``
    (System C already does this internally).
  - ``retrieved_resources`` in the response maps 1-to-1 to
    ``SystemResponse.retrieved`` (primary chunks, role="primary").
    Expansion chunks from ``SystemResponse.extras["expansion_chunks"]`` are
    surfaced as a separate field so callers can inspect the reference graph
    traversal independently.

Mounting in metricCONNECT (FastAPI app factory pattern)::

    from mh_integration.case_manager_qa import router as qa_router
    app.include_router(qa_router, prefix="/qa", tags=["case-manager-qa"])

Running standalone (smoke test / local dev)::

    python -m mh_integration.case_manager_qa
    # or:
    uvicorn mh_integration.case_manager_qa:app --reload --port 8080
"""
from __future__ import annotations

import time
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.routing import APIRouter
from pydantic import BaseModel, Field

from systems.structured_rag_aware import StructuredRAGAware

# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------


class QARequest(BaseModel):
    """Request body for the case-manager Q&A endpoint.

    Attributes
    ----------
    patient_id:
        Full UUID string identifying the patient
        (e.g. ``"014abeea-627d-f33c-834c-e2a6605046ee"``).
        Must match a FHIR bundle present in ``data/fhir_bundles/``.
    question:
        Natural-language question from the PSP case manager.
        No length limit is enforced here; the answer LLM's token budget
        applies upstream in ``systems.common.answer_llm``.
    """

    patient_id: str = Field(
        ...,
        description="Full UUID of the patient (must match a FHIR bundle on disk).",
        examples=["014abeea-627d-f33c-834c-e2a6605046ee"],
    )
    question: str = Field(
        ...,
        description="Natural-language question for the case manager.",
        examples=["When was the patient's last Aimovig injection?"],
    )


class RetrievedChunk(BaseModel):
    """A single retrieved (or expansion) chunk returned to the caller.

    Maps directly to the dict elements in ``SystemResponse.retrieved`` and
    ``SystemResponse.extras["expansion_chunks"]``.  Unknown keys are forwarded
    as-is via ``model_config = {"extra": "allow"}``.
    """

    model_config = {"extra": "allow"}

    text: str = Field(..., description="Raw chunk text passed to the answer LLM.")
    source_id: str = Field(
        default="",
        description="Patient UUID (source of this chunk).",
    )
    resource_type: str = Field(
        default="",
        description="FHIR resource type (e.g. MedicationAdministration).",
    )
    resource_id: str = Field(
        default="",
        description="Bare FHIR resource id within the bundle.",
    )
    chunk_index: str = Field(
        default="",
        description="Zero-based chunk index within the parent resource.",
    )
    score: float | None = Field(
        default=None,
        description="Cosine similarity score (None for expansion chunks).",
    )
    rank: int | None = Field(
        default=None,
        description="Retrieval rank within the primary pool (None for expansion).",
    )
    role: str = Field(
        default="",
        description='"primary" for top-k hits; "expansion" for reference traversal.',
    )


class QAResponse(BaseModel):
    """Response envelope returned by the case-manager Q&A endpoint.

    Attributes
    ----------
    answer:
        The LLM-generated answer string.
    retrieved_resources:
        Primary top-k chunks used as context (role="primary").
    expansion_resources:
        One-hop reference-expansion chunks appended after the primary context
        (role="expansion").  Empty list when no references were found.
    latency_ms:
        Wall-clock milliseconds from when the HTTP handler received the request
        to when ``SystemResponse`` was constructed inside System C.  Includes
        FHIR indexing time on the first call for a given patient, but subsequent
        calls are served from the ChromaDB cache.
    tokens_in:
        Prompt tokens consumed by the answer LLM (Qwen 3 32B).
    tokens_out:
        Completion tokens produced by the answer LLM.
    cache_hit:
        Whether the answer LLM cache was hit (True = no Groq call was made).
    type_filter:
        Resource types used by System C's QUESTION_TYPE_ROUTER for this question.
        Empty list means the fallback (no-filter) path was taken.
    """

    answer: str = Field(..., description="LLM-generated answer text.")
    retrieved_resources: list[RetrievedChunk] = Field(
        ...,
        description="Primary top-k chunks (role=primary) used as LLM context.",
    )
    expansion_resources: list[RetrievedChunk] = Field(
        default_factory=list,
        description="Reference-expansion chunks (role=expansion) appended after primary context.",
    )
    latency_ms: float = Field(..., description="End-to-end wall-clock latency in milliseconds.")
    tokens_in: int = Field(..., description="Answer LLM prompt tokens consumed.")
    tokens_out: int = Field(..., description="Answer LLM completion tokens produced.")
    cache_hit: bool = Field(
        default=False,
        description="True if the answer LLM cache was hit and no Groq call was made.",
    )
    type_filter: list[str] = Field(
        default_factory=list,
        description="Resource types applied by the question router (empty = no filter).",
    )


# ---------------------------------------------------------------------------
# Module-level System C instance
# ---------------------------------------------------------------------------

# A single StructuredRAGAware instance is shared across all requests within
# a process.  EmbeddingClient (sentence-transformers) is expensive to load;
# sharing it avoids repeated model loads per request.
# Thread safety: EmbeddingClient.embed_* methods are stateless; ChromaDB
# PersistentClient is also safe to share across threads for read-heavy workloads.
_system_c: StructuredRAGAware | None = None


def _get_system() -> StructuredRAGAware:
    """Return the module-level System C instance, constructing it on first use."""
    global _system_c
    if _system_c is None:
        _system_c = StructuredRAGAware()
    return _system_c


# ---------------------------------------------------------------------------
# Router (mountable into a parent FastAPI app)
# ---------------------------------------------------------------------------

router = APIRouter()


@router.post(
    "/ask",
    response_model=QAResponse,
    summary="Case-manager Q&A via resource-aware FHIR RAG (System C)",
    description=(
        "Submit a natural-language question about a patient. "
        "System C (resource-type-filtered + reference-expanded FHIR RAG) retrieves "
        "relevant FHIR chunks and returns an LLM-generated answer together with the "
        "retrieved resources and latency metadata."
    ),
)
def ask_question(body: QARequest) -> QAResponse:
    """POST /ask — answer a case-manager question using System C.

    Raises
    ------
    HTTPException 404:
        If no FHIR bundle exists on disk for ``patient_id``.
    HTTPException 500:
        For any unexpected retrieval or LLM error.
    """
    system = _get_system()

    try:
        response = system.answer(question=body.question, patient_id=body.patient_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Retrieval error: {exc}") from exc

    # Unpack extras written by System C
    extras: dict[str, Any] = response.extras or {}
    expansion_raw: list[dict[str, Any]] = extras.get("expansion_chunks", [])

    return QAResponse(
        answer=response.answer,
        retrieved_resources=[RetrievedChunk(**chunk) for chunk in response.retrieved],
        expansion_resources=[RetrievedChunk(**chunk) for chunk in expansion_raw],
        latency_ms=response.latency_ms,
        tokens_in=response.tokens_in,
        tokens_out=response.tokens_out,
        cache_hit=bool(extras.get("cache_hit", False)),
        type_filter=extras.get("type_filter", []),
    )


# ---------------------------------------------------------------------------
# Standalone FastAPI app (for ``uvicorn mh_integration.case_manager_qa:app``)
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    """Application factory — returns a FastAPI instance with the QA router mounted.

    metricCONNECT should call this factory and mount the result, or import
    ``router`` directly and call ``app.include_router(router, prefix="/qa")``.
    """
    application = FastAPI(
        title="metricCONNECT Case-Manager Q&A",
        description=(
            "System C (resource-aware structured FHIR RAG) packaged as a "
            "FastAPI service for the metricCONNECT integration layer."
        ),
        version="0.1.0",
    )
    application.include_router(router, prefix="/qa", tags=["case-manager-qa"])
    return application


# Module-level app for uvicorn direct invocation:
#   uvicorn mh_integration.case_manager_qa:app --reload --port 8080
app: FastAPI = create_app()


# ---------------------------------------------------------------------------
# __main__ entry point — local smoke run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "mh_integration.case_manager_qa:app",
        host="127.0.0.1",
        port=8080,
        reload=False,
        log_level="info",
    )
