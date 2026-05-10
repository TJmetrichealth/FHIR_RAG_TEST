# Tier 3 Most-Frequent-Class Baseline

> Reproduce: see `analysis/tier3_baseline.py` (or the inline computation in
> the paper-revision session log).

## Method

For each question family, compute the modal ground-truth string within Tier 3 and
score that constant prediction against the actual ground truth (exact match). Wilson
95% CIs are reported per cell and overall.

## Results

| Family | n | modal ground_truth | modal freq | baseline acc | Wilson 95% CI |
|---|---|---|---|---|---|
| cross_resource | 592 | `'yes'` | 222 | 0.3750 | [0.337, 0.415] |
| regimen_aggregation | 888 | `'0'` | 138 | 0.1554 | [0.133, 0.181] |
| regimen_compliance | 1554 | `'0'` | 540 | 0.3475 | [0.324, 0.372] |
| temporal_comparison | 888 | `'oral adjunct'` | 246 | 0.2770 | [0.249, 0.307] |
| temporal_lookup | 1184 | `'0'` | 118 | 0.0997 | [0.084, 0.118] |

**Overall Tier 3 per-family modal baseline:** 1,264 / 5,106 = **0.2476 [0.2359, 0.2596]**

**Single global modal baseline (ignoring family; predict `'0'` for every question):**
796 / 5,106 = 0.1559 [0.1462, 0.1661]

## System accuracies at Tier 3 (from `results/scored.csv`)

| System | k | n | acc | Wilson 95% CI |
|---|---|---|---|---|
| A (narrative_rag) | 1,043 | 5,106 | 0.2043 | [0.1934, 0.2155] |
| B (structured_naive) | 1,011 | 5,106 | 0.1980 | [0.1873, 0.2092] |
| C (structured_aware) | 1,024 | 5,106 | 0.2005 | [0.1898, 0.2118] |

## Interpretation

All three system 95% CIs sit strictly below the per-family modal baseline 95% CI
[0.2359, 0.2596]: the upper edge of each system's CI is at most 0.2155 (System A),
which lies 2.0 pp below the baseline lower edge of 0.2359. Non-overlap of the 95%
CIs corresponds approximately to p < 0.005 for pairwise comparison.

The headline therefore strengthens from "Tier 3 is unsolved by the current
architectures at the 512-token budget" to "Tier 3 accuracy is *significantly worse
than* a per-family most-frequent-class baseline." A trivial predictor that always
returns the modal answer in each family beats every system on Tier 3 multi-drug
regimens.
