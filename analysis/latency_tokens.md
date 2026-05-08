# FHIR-RAG Latency, Tokens, and Cost

> Source: `results/latency_tokens.csv` and `results/raw/{a,b,c}.jsonl` (cache_hit filtering)
> Groq pricing: input $0.29/M tokens, output $0.59/M tokens (qwen-3-32b Developer plan).

## Latency Percentiles (ms)

| System | p50 | p95 | p99 |
|--------|-----|-----|-----|
| A (narrative_rag) | 1060 | 6031 | 53038 |
| B (structured_naive) | 1354 | 17890 | 46301 |
| C (structured_aware) | 1056 | 4538 | 8513 |

## Token Usage (mean per call)

| System | Mean tokens_in | Mean tokens_out | Ratio (in/out) |
|--------|---------------|-----------------|----------------|
| A (narrative_rag) | 490 | 342 | 1.4 |
| B (structured_naive) | 4463 | 402 | 11.1 |
| C (structured_aware) | 2175 | 391 | 5.6 |

## Groq Cost (live calls only, cache hits excluded)

| System | Live calls | Tokens in | Tokens out | Estimated cost (USD) |
|--------|-----------|-----------|------------|----------------------|
| A (narrative_rag) | 13,790 | 6,758,334 | 4,708,726 | $4.74 |
| B (structured_naive) | 13,764 | 61,393,652 | 5,529,603 | $21.07 |
| C (structured_aware) | 10,035 | 15,669,340 | 3,957,602 | $6.88 |
| **Total** | | | | **$32.68** |

Cache hit counts (excluded from cost): A=10, B=36, C=3765.

## Interpretation

System B (structured_naive) is the most expensive system by a significant margin at
$21.07 — 4.4x the cost of System A
($4.74). This is driven almost entirely by its large input context:
B serialises the full FHIR bundle (mean 4463 tokens_in vs
A's 490), whereas A retrieves only the relevant narrative chunk.
System C ($6.88) is intermediate — its resource-aware retrieval
prunes the context more aggressively than B's naive approach, reducing mean tokens_in from
4463 to 2175.

Critically, System B's 4.4x cost premium delivers
35.3% exact-match accuracy versus System A's
40.6% — a 5.3% deficit at
more than 4.4x the price. System C achieves a similar
accuracy (33.4%) at 1.5x
A's cost. None of the structured systems is "worth" the extra latency or token cost
relative to System A under the current FHIR representation design.

Latency: B also has the highest median latency (1354 ms p50) and
extreme tail latency (46301 ms p99). System C is the fastest
(p50=1056 ms, p99=8513 ms),
likely because its smaller context reduces LLM generation time.
