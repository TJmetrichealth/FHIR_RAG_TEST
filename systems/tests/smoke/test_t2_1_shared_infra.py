"""Smoke tests for T2.1 shared infrastructure.

Tests verify:
1. EmbeddingClient round-trip + cache hit on second call.
2. Chunker produces expected chunks for a short text.
3. answer_llm.ask() makes one live Groq call then returns cache hit.
4. Harness skeleton runs 3 questions for 1 patient via the stub system,
   writing output to results/raw/stub.jsonl.

Run with::

    pytest systems/tests/smoke/test_t2_1_shared_infra.py -v

Note: The answer-LLM test (test_answer_llm_cache) makes one real Groq API
call on the first run; subsequent runs are free (cache hit).  Set
GROQ_API_KEY in your environment before running.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# 1. Embedding client — round-trip + cache hit
# ---------------------------------------------------------------------------

def test_embedding_roundtrip_and_cache(tmp_path: Path) -> None:
    from systems.common.embedder import EmbeddingClient

    client = EmbeddingClient(cache_dir=tmp_path / "emb_cache")

    sentence = "The patient received 400 mg of medication X on 2025-03-15."

    vec1 = client.embed_one(sentence)
    assert isinstance(vec1, np.ndarray)
    assert vec1.dtype == np.float32
    assert vec1.ndim == 1
    assert vec1.shape[0] > 0

    # Second call must be a cache hit — no model call needed
    cache_before = client.cache_stats()["entries"]
    vec2 = client.embed_one(sentence)
    cache_after = client.cache_stats()["entries"]

    np.testing.assert_array_equal(vec1, vec2, err_msg="Cached embedding differs from original")
    assert cache_after == cache_before, "Cache should not grow on hit"


def test_embedding_batch_consistent_with_single(tmp_path: Path) -> None:
    from systems.common.embedder import EmbeddingClient

    client = EmbeddingClient(cache_dir=tmp_path / "emb_cache2")
    texts = [
        "Patient is on a q8w injection schedule.",
        "Next dose due 2025-06-10.",
    ]
    singles = [client.embed_one(t) for t in texts]
    batch = client.embed_batch(texts)

    for s, b in zip(singles, batch):
        np.testing.assert_array_almost_equal(s, b, decimal=5)


# ---------------------------------------------------------------------------
# 2. Chunker
# ---------------------------------------------------------------------------

def test_chunker_basic() -> None:
    from systems.common.chunker import chunk_text

    text = "Patient A has been on therapy since January. " * 80  # ~640 words
    chunks = chunk_text(text, source_id="pid-001")

    assert len(chunks) >= 2, "Text should produce at least 2 chunks"
    for chunk in chunks:
        assert chunk.source_id == "pid-001"
        assert len(chunk.text) > 0
        assert chunk.token_estimate() <= 650  # some slack for the estimate


def test_chunker_short_text() -> None:
    from systems.common.chunker import chunk_text

    text = "Single sentence."
    chunks = chunk_text(text, source_id="pid-short")
    assert len(chunks) == 1
    assert chunks[0].text == text


def test_chunker_empty_text() -> None:
    from systems.common.chunker import chunk_text

    assert chunk_text("", source_id="pid-empty") == []
    assert chunk_text("   ", source_id="pid-ws") == []


# ---------------------------------------------------------------------------
# 3. Answer LLM wrapper (one live call → cache; second call is free)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not os.environ.get("GROQ_API_KEY"),
    reason="GROQ_API_KEY not set — skipping live LLM test",
)
def test_answer_llm_cache(tmp_path: Path) -> None:
    from systems.common.answer_llm import ask

    context = (
        "The patient received their last injection on 2025-03-15. "
        "The next scheduled dose is 2025-05-10 (q8w schedule)."
    )
    question = "When is the patient's next scheduled dose?"

    cache_dir = tmp_path / "ans_cache"

    result1 = ask(question, context, cache_dir=cache_dir)
    assert result1.answer, "Answer should not be empty"
    assert result1.tokens_in > 0
    assert not result1.cache_hit, "First call should not be a cache hit"

    result2 = ask(question, context, cache_dir=cache_dir)
    assert result2.cache_hit, "Second call with identical prompt must be a cache hit"
    assert result2.answer == result1.answer, "Cached answer must match original"
    assert result2.tokens_in == result1.tokens_in


# ---------------------------------------------------------------------------
# 4. Harness skeleton — stub system, 1 patient, first 3 questions
# ---------------------------------------------------------------------------

def test_harness_stub_run(tmp_path: Path) -> None:
    from eval.harness import run_harness
    from eval.config import QUESTIONS_PATH
    from systems.base import BaseSystem

    output_path = tmp_path / "stub.jsonl"

    # Pick one patient from questions.jsonl
    first_patient = None
    with open(QUESTIONS_PATH, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                first_patient = json.loads(line)["patient_id"]
                break
    assert first_patient is not None, "questions.jsonl must not be empty"

    from eval.harness import _StubSystem  # type: ignore

    stub = _StubSystem()
    assert isinstance(stub, BaseSystem), "StubSystem must satisfy BaseSystem protocol"

    records = run_harness(
        system=stub,
        system_name="stub",
        questions_path=QUESTIONS_PATH,
        patient_ids=[first_patient],
        output_path=output_path,
        limit=3,
        resume=False,
    )

    assert len(records) == 3, f"Expected 3 records, got {len(records)}"
    assert output_path.exists(), "Output JSONL must exist"

    with open(output_path, encoding="utf-8") as fh:
        lines = [json.loads(l) for l in fh if l.strip()]

    assert len(lines) == 3
    for rec in lines:
        assert rec["answer"] == "N/A"
        assert rec["system"] == "stub"
        assert rec["patient_id"] == first_patient
        assert "question_id" in rec
        assert "ground_truth" in rec
        assert "tokens_in" in rec and rec["tokens_in"] == 0
        assert "retrieved" in rec and rec["retrieved"] == []


def test_harness_resume(tmp_path: Path) -> None:
    """Second run with same output file should skip already-done IDs."""
    from eval.harness import run_harness
    from eval.config import QUESTIONS_PATH
    from eval.harness import _StubSystem

    output_path = tmp_path / "stub_resume.jsonl"
    stub = _StubSystem()

    first_patient = None
    with open(QUESTIONS_PATH, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                first_patient = json.loads(line)["patient_id"]
                break

    # First run: write 2 records
    run_harness(
        system=stub,
        system_name="stub",
        questions_path=QUESTIONS_PATH,
        patient_ids=[first_patient],
        output_path=output_path,
        limit=2,
        resume=False,
    )

    # Second run: resume=True, limit=5 — should only ADD 3 more (skip the 2 done)
    records2 = run_harness(
        system=stub,
        system_name="stub",
        questions_path=QUESTIONS_PATH,
        patient_ids=[first_patient],
        output_path=output_path,
        limit=5,
        resume=True,
    )

    assert len(records2) == 3, f"Expected 3 new records on resume, got {len(records2)}"

    # File should have 5 total lines
    with open(output_path, encoding="utf-8") as fh:
        total = sum(1 for l in fh if l.strip())
    assert total == 5
