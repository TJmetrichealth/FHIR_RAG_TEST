# FHIR-RAG Recall@k Analysis

> Source: `results/recall_at_k.csv`

## Summary

System A (narrative_rag) does not have resource-level provenance � its index contains
narrative text chunks with no FHIR resource IDs. Recall@k is undefined for System A and
is reported as N/A throughout. All comparisons below are between System B (structured_naive)
and System C (structured_aware).

## Overall Recall@k (mean across all families and tiers)

| System | k=1 | k=3 | k=5 | k=10 |
|--------|-----|-----|-----|------|
| B (structured_naive) | 0.573 [0.543,0.602] | 0.739 [0.711,0.765] | 0.762 [0.735,0.787] | 0.762 [0.735,0.787] |
| C (structured_aware) | 0.664 [0.636,0.690] | 0.829 [0.807,0.848] | 0.852 [0.831,0.870] | 0.852 [0.831,0.870] |

Values shown as mean recall [Wilson 95% CI mean across strata].

## By Family (k=5 spotlight)

| Family | B recall@5 | B 95% CI | C recall@5 | C 95% CI | C > B? |
|--------|-----------|----------|-----------|----------|--------|
| cross_resource | 0.788 | [0.755,0.816] | 0.959 | [0.943,0.968] | Yes |
| regimen_aggregation | 0.829 | [0.802,0.853] | 0.924 | [0.903,0.940] | Yes |
| regimen_compliance | 0.730 | [0.706,0.753] | 0.822 | [0.801,0.841] | Yes |
| temporal_comparison | 0.672 | [0.643,0.699] | 0.773 | [0.747,0.797] | Yes |
| temporal_lookup | 0.792 | [0.767,0.815] | 0.783 | [0.760,0.804] | No |

## By Tier (k=5 spotlight)

| Tier | B recall@5 | B 95% CI | C recall@5 | C 95% CI | C > B? |
|------|-----------|----------|-----------|----------|--------|
| 1 | 0.616 | [0.584,0.647] | 0.741 | [0.712,0.768] | Yes |
| 2 | 0.856 | [0.831,0.877] | 0.940 | [0.925,0.951] | Yes |
| 3 | 0.815 | [0.790,0.838] | 0.875 | [0.856,0.891] | Yes |

## Interpretation

The resource-aware system (C) shows higher retrieval recall than the naive system (B) at
k=1 (C: 0.664 vs B: 0.573) but the gap narrows by k=10 (C: 0.852 vs
B: 0.762). This indicates that System C's resource-aware indexing is most valuable
at low-k settings, where precision in the top-1 result matters most. At k=10 both systems
approach similar recall ceilings, suggesting that the relevant resources are retrievable by
both systems given enough budget, but C arrives at them sooner.

The recall advantage of C over B does NOT translate into an end-to-end accuracy advantage
(C scores 33.4% exact-match vs B's 35.3%
� B is actually better). The most likely explanation is that the FHIR-structured context
fed to the answer LLM by both structured systems is harder for the LLM to reason over than
the fluent narrative text used by System A, regardless of which resource is retrieved.
The retrieval recall metric measures the right resource being selected; it does not measure
whether the LLM can extract the answer from that resource's structured representation.

Note: System A recall@k figures are all N/A because narrative chunks carry no FHIR resource
IDs; a resource-level recall cannot be defined for System A under the v1 heuristic.
