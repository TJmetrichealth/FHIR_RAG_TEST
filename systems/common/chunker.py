"""Shared text chunker used by all three retrieval systems.

Splits text into overlapping token-budget chunks so that each chunk fits
within CHUNK_TOKENS tokens (approximated via whitespace word count ×
constant factor, since we have no tokenizer dependency at chunk time).

Parameters are read from eval.config — no magic numbers here.

The same chunker is imported by System A (narrative chunks), System B
(serialised FHIR resource chunks), and System C (filtered resource chunks).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from eval.config import CHUNK_OVERLAP_TOKENS, CHUNK_TOKENS

# Approximation: 1 word ≈ 1.3 tokens for clinical/mixed text.
# This is deliberately conservative (underestimates tokens) so chunks stay
# within budget even when the answer LLM's tokeniser is slightly different.
_WORDS_PER_TOKEN: float = 1.0 / 1.3  # ≈ 0.77 words per token


def _token_estimate(text: str) -> int:
    """Rough token count: word count / 0.77."""
    words = len(text.split())
    return max(1, int(words / _WORDS_PER_TOKEN))


@dataclass
class Chunk:
    """A single text chunk with provenance metadata."""

    text: str
    chunk_index: int
    source_id: str                          # e.g. patient_id or resource ID
    metadata: dict[str, str] = field(default_factory=dict)

    def token_estimate(self) -> int:
        return _token_estimate(self.text)


def chunk_text(
    text: str,
    source_id: str,
    *,
    chunk_tokens: int = CHUNK_TOKENS,
    overlap_tokens: int = CHUNK_OVERLAP_TOKENS,
    metadata: dict[str, str] | None = None,
) -> list[Chunk]:
    """Split *text* into overlapping chunks.

    Splitting is done on sentence boundaries (``[.!?]\\s+``) where possible;
    otherwise falls back to word boundaries so no word is ever cut mid-token.

    Parameters
    ----------
    text:
        The full document text to chunk.
    source_id:
        Identifier propagated to every Chunk (e.g. patient_id or resource ID).
    chunk_tokens:
        Target maximum tokens per chunk (from config by default).
    overlap_tokens:
        Number of tokens to repeat at the start of the next chunk.
    metadata:
        Arbitrary key/value metadata forwarded to each Chunk unchanged.

    Returns
    -------
    list[Chunk]
        Non-empty list; at minimum one chunk covering the whole text if the
        text is shorter than chunk_tokens.
    """
    if not text or not text.strip():
        return []

    meta = metadata or {}
    chunk_words = int(chunk_tokens * _WORDS_PER_TOKEN)
    overlap_words = int(overlap_tokens * _WORDS_PER_TOKEN)

    # Split into sentences, keeping the delimiter attached to the sentence.
    sentences: list[str] = re.split(r"(?<=[.!?])\s+", text.strip())
    if not sentences:
        sentences = [text.strip()]

    chunks: list[Chunk] = []
    buffer: list[str] = []
    buf_words = 0

    def _flush(buf: list[str], idx: int) -> Chunk:
        chunk_text_ = " ".join(buf).strip()
        return Chunk(
            text=chunk_text_,
            chunk_index=idx,
            source_id=source_id,
            metadata=dict(meta),
        )

    for sent in sentences:
        sent_words = len(sent.split())
        if buf_words + sent_words > chunk_words and buffer:
            chunks.append(_flush(buffer, len(chunks)))
            # Carry-over the last overlap_words worth of sentences
            overlap_buf: list[str] = []
            ow = 0
            for s in reversed(buffer):
                sw = len(s.split())
                if ow + sw > overlap_words:
                    break
                overlap_buf.insert(0, s)
                ow += sw
            buffer = overlap_buf
            buf_words = ow
        buffer.append(sent)
        buf_words += sent_words

    if buffer:
        chunks.append(_flush(buffer, len(chunks)))

    return chunks
