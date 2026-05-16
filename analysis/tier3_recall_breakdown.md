# Tier-3 Retrieval Recall vs Accuracy Breakdown

> Source: `results/recall_at_k.csv` + `results/scored.csv`
>
> Addresses reviewer revision #4. Tier 3 is the multi-drug regimen tier
> where all three systems sit below the per-family most-frequent-class
> baseline (24.8% [23.6%, 26.0%]). This document decomposes whether the
> failure is upstream (retriever) or downstream (answer LLM reasoning).

## Tier-3 recall@5 vs Tier-3 exact-match accuracy

Per (system, family). Recall numbers are from `results/recall_at_k.csv`
(family rows where `tier == 3` and `k == 5`). Accuracy is exact-match on
Tier-3 questions only.

| family | B recall@5 | B 95% CI | C recall@5 | C 95% CI | A acc | B acc | C acc |
|---|---|---|---|---|---|---|---|
| cross_resource | 89.7% | [87.0%, 91.9%] | 99.7% | [98.8%, 99.9%] | 29.7% [26.2%, 33.5%] | 48.5% [44.5%, 52.5%] | 49.8% [45.8%, 53.8%] |
| regimen_aggregation | 83.2% | [80.6%, 85.5%] | 94.1% | [92.4%, 95.5%] | 27.6% [24.8%, 30.6%] | 15.1% [12.9%, 17.6%] | 12.4% [10.4%, 14.7%] |
| regimen_compliance | 76.6% | [74.5%, 78.7%] | 89.9% | [88.3%, 91.3%] | 5.3% [4.3%, 6.6%] | 4.7% [3.8%, 5.9%] | 2.6% [1.9%, 3.5%] |
| temporal_comparison | 80.0% | [77.2%, 82.5%] | 77.4% | [74.5%, 80.0%] | 3.9% [2.8%, 5.4%] | 6.4% [5.0%, 8.2%] | 7.1% [5.6%, 9.0%] |
| temporal_lookup | 78.0% | [75.5%, 80.2%] | 76.5% | [74.0%, 78.8%] | 42.6% [39.8%, 45.4%] | 38.9% [36.1%, 41.7%] | 43.6% [40.8%, 46.4%] |

## Tier-3 retrieval recall vs overall recall (means across families)

| Slice | B recall@5 | C recall@5 |
|---|---|---|
| Overall (all tiers, all families) | 76.1% | 83.9% |
| Tier 1 | 63.5% | 72.5% |
| Tier 2 | 83.8% | 92.4% |
| Tier 3 | 80.2% | 86.5% |

## Per-system Tier-3 accuracy (cross-reference)

| System | Tier-3 accuracy | 95% CI | n questions |
|---|---|---|---|
| A (narrative) | 20.4% | [19.3%, 21.6%] | 5106 |
| B (naive struct) | 19.8% | [18.7%, 20.9%] | 5106 |
| C (aware struct) | 20.1% | [19.0%, 21.2%] | 5106 |

Per-family modal baseline at Tier 3 (from `analysis/tier3_baseline.md`): **24.8% [23.6%, 26.0%]**. All three system Tier-3 accuracies sit below this baseline CI.

## Interpretation: retriever vs answer LLM

Tier-3 retrieval recall stays high for both B and C across every family except `temporal_lookup`. For `cross_resource`, `regimen_aggregation`, `temporal_comparison`, and `regimen_compliance`, recall@5 at Tier 3 exceeds 70% (System B) or 75% (System C). The Tier-3 evidence is therefore not absent from the retrieved context; the answer LLM has the supporting passages in its window in most cases and still produces wrong answers.

This isolates the bottleneck to **downstream reasoning under multi-component context**, not retrieval. The hypothesis-level architectural implications:

- Longer outputs alone are insufficient. The 1024-token sweep (Section 4.8) moved B by +3.8 pp and C by +5.1 pp on a stratified subsample but did not clear Tier 3 above the modal baseline.
- Per-component decomposition is the next architectural step worth testing: answer the question separately per regimen component (primary, adjunct, PRN) and aggregate, rather than reasoning over a concatenated multi-component context.
- Chain-of-thought scaffolding or structured intermediate steps (e.g., explicit per-component date enumeration before aggregation) may help. The current answer prompt provides retrieved chunks and asks for the answer in one step.
- `temporal_lookup` is the one family where C does not beat B at Tier-3 recall@5. Worth inspecting whether the resource-aware temporal pre-filter is over-pruning candidate Observation/MedicationAdministration resources at Tier 3.
