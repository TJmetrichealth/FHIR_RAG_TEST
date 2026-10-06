# Revision re-analysis (paper v2)

> Reproduce: `python analysis/run_revision_reanalysis.py`

## 1. Aggregate accuracy (%)

- A: 5600/13800 = 40.58% [39.8, 41.4]
- B: 4873/13800 = 35.31% [34.5, 36.1]
- C: 4605/13800 = 33.37% [32.6, 34.2]
- AT: 5702/13800 = 41.32% [40.5, 42.1]
- N: 3473/13800 = 25.17% [24.4, 25.9]
- Constant N/A predictor: 5623/13800 = 40.75% [39.9, 41.6]

## 2. Pairwise differences, all questions

Patient-level cluster bootstrap (primary):

- A minus B: +5.27 pp, cluster 95% CI [+4.30, +6.22] (200 patients, 13800 questions)
- A minus C: +7.21 pp, cluster 95% CI [+5.70, +8.72] (200 patients, 13800 questions)
- B minus C: +1.94 pp, cluster 95% CI [+0.75, +3.09] (200 patients, 13800 questions)
- AT minus A: +0.74 pp, cluster 95% CI [+0.16, +1.33] (200 patients, 13800 questions)
- A minus N: +15.41 pp, cluster 95% CI [+14.86, +15.98] (200 patients, 13800 questions)
- B minus N: +10.14 pp, cluster 95% CI [+9.28, +11.04] (200 patients, 13800 questions)
- C minus N: +8.20 pp, cluster 95% CI [+6.92, +9.50] (200 patients, 13800 questions)

Question-level paired bootstrap (previous version):

- A minus B: +5.27 pp, question-level 95% CI [+4.52, +6.01]
- A minus C: +7.21 pp, question-level 95% CI [+6.46, +7.96]
- B minus C: +1.94 pp, question-level 95% CI [+1.35, +2.53]
- AT minus A: +0.74 pp, question-level 95% CI [+0.14, +1.35]
- A minus N: +15.41 pp, question-level 95% CI [+14.60, +16.23]
- B minus N: +10.14 pp, question-level 95% CI [+9.32, +10.99]
- C minus N: +8.20 pp, question-level 95% CI [+7.34, +9.07]

## 3. Per-tier cluster bootstrap


Tier 1:

- A minus B: +6.86 pp, cluster 95% CI [+5.45, +8.17] (63 patients, 4347 questions)
- A minus C: +13.09 pp, cluster 95% CI [+10.51, +15.53] (63 patients, 4347 questions)
- B minus C: +6.23 pp, cluster 95% CI [+4.32, +8.03] (63 patients, 4347 questions)
- AT minus A: +3.43 pp, cluster 95% CI [+2.62, +4.23] (63 patients, 4347 questions)

Tier 2:

- A minus B: +9.13 pp, cluster 95% CI [+7.09, +10.95] (63 patients, 4347 questions)
- A minus C: +9.36 pp, cluster 95% CI [+6.28, +12.33] (63 patients, 4347 questions)
- B minus C: +0.23 pp, cluster 95% CI [-2.58, +2.92] (63 patients, 4347 questions)
- AT minus A: -0.07 pp, cluster 95% CI [-1.29, +1.15] (63 patients, 4347 questions)

Tier 3:

- A minus B: +0.63 pp, cluster 95% CI [-0.45, +1.68] (74 patients, 5106 questions)
- A minus C: +0.37 pp, cluster 95% CI [-0.88, +1.55] (74 patients, 5106 questions)
- B minus C: -0.25 pp, cluster 95% CI [-1.27, +0.74] (74 patients, 5106 questions)
- AT minus A: -0.86 pp, cluster 95% CI [-1.59, -0.16] (74 patients, 5106 questions)

## 4. Per-family cluster bootstrap, A-T minus A


cross_resource:

- AT minus A: -2.25 pp, cluster 95% CI [-4.88, +0.38] (200 patients, 1600 questions)

regimen_aggregation:

- AT minus A: -7.29 pp, cluster 95% CI [-8.54, -6.04] (200 patients, 2400 questions)

regimen_compliance:

- AT minus A: +1.79 pp, cluster 95% CI [+0.76, +2.86] (200 patients, 4200 questions)

temporal_comparison:

- AT minus A: +10.21 pp, cluster 95% CI [+8.71, +11.71] (200 patients, 2400 questions)

temporal_lookup:

- AT minus A: -0.22 pp, cluster 95% CI [-1.12, +0.66] (200 patients, 3200 questions)

## 5. N/A prevalence by tier

|   tier |   sum |   size |     mean |
|-------:|------:|-------:|---------:|
|      1 |  2357 |   4347 | 0.542213 |
|      2 |  2562 |   4347 | 0.589372 |
|      3 |   704 |   5106 | 0.137877 |

Overall N/A share: 40.75%

## 6. Accuracy by tier x N/A status (%)

|            |    n |    A |    B |    C |   AT |    N |
|:-----------|-----:|-----:|-----:|-----:|-----:|-----:|
| (1, False) | 1990 | 18.2 | 17.8 | 17.5 | 16.8 |  3.2 |
| (1, True)  | 2357 | 83.9 | 71.7 | 60.4 | 91.5 | 62   |
| (2, False) | 1785 | 19.3 | 17.1 | 18.8 | 18.9 |  0   |
| (2, True)  | 2562 | 73.1 | 59.1 | 57.5 | 73.2 | 62.3 |
| (3, False) | 4402 | 13.6 | 13.1 | 13.4 | 12.2 |  0.2 |
| (3, True)  |  704 | 63.2 | 61.8 | 61.4 | 65.6 | 48.9 |

Overall, substantive only (%):
|    |     0 |
|:---|------:|
| A  | 15.96 |
| B  | 15.1  |
| C  | 15.6  |
| AT | 14.77 |
| N  |  0.87 |

Overall, N/A only (%):
|    |     0 |
|:---|------:|
| A  | 76.38 |
| B  | 64.7  |
| C  | 59.2  |
| AT | 79.92 |
| N  | 60.5  |

## 7. Accuracy by family x N/A status (%)

|                                |    n |    A |    B |    C |   AT |    N |
|:-------------------------------|-----:|-----:|-----:|-----:|-----:|-----:|
| ('cross_resource', False)      | 1348 | 34.1 | 39.6 | 42.5 | 34.5 |  4.7 |
| ('cross_resource', True)       |  252 | 92.9 | 70.6 | 48.4 | 76.6 | 50   |
| ('regimen_aggregation', False) | 1822 | 15.8 |  4   |  3.1 |  6   |  0.1 |
| ('regimen_aggregation', True)  |  578 | 82.4 | 68.3 | 64.4 | 82.9 | 21.8 |
| ('regimen_compliance', False)  | 2425 |  2.4 |  0.6 |  1   |  1   |  0.3 |
| ('regimen_compliance', True)   | 1775 | 69.8 | 59.8 | 58.5 | 75.9 | 82.3 |
| ('temporal_comparison', False) |  818 |  0   |  0   |  0   |  0   |  0   |
| ('temporal_comparison', True)  | 1582 | 66.2 | 66.3 | 52.1 | 81.7 | 39.8 |
| ('temporal_lookup', False)     | 1764 | 28.3 | 34.8 | 35.3 | 34.5 |  0   |
| ('temporal_lookup', True)      | 1436 | 90.4 | 66.5 | 67.7 | 82.3 | 73.8 |

## 8. Share of each arm's correct answers that are N/A-truth questions

- Tier 1 A: 84.5% (n correct = 2341)
- Tier 1 B: 82.7% (n correct = 2043)
- Tier 1 C: 80.3% (n correct = 1772)
- Tier 1 N: 95.9% (n correct = 1525)
- Tier 2 A: 84.5% (n correct = 2216)
- Tier 2 B: 83.2% (n correct = 1819)
- Tier 2 C: 81.5% (n correct = 1809)
- Tier 2 N: 100.0% (n correct = 1596)
- Tier 3 A: 42.7% (n correct = 1043)
- Tier 3 B: 43.0% (n correct = 1011)
- Tier 3 C: 42.2% (n correct = 1024)
- Tier 3 N: 97.7% (n correct = 352)

## 9. Per-family modal baseline (N/A admitted as a label)

- Tier 1: all questions 54.2%; substantive only 28.1%
- Tier 2: all questions 58.9%; substantive only 21.8%
- Tier 3: all questions 29.5%; substantive only 28.7%

## 10. Cluster bootstrap, substantive questions only

- A minus B: +0.86 pp, cluster 95% CI [+0.37, +1.34] (200 patients, 8177 questions)
- A minus C: +0.35 pp, cluster 95% CI [-0.11, +0.82] (200 patients, 8177 questions)
- B minus C: -0.50 pp, cluster 95% CI [-0.91, -0.09] (200 patients, 8177 questions)
- AT minus A: -1.19 pp, cluster 95% CI [-1.61, -0.75] (200 patients, 8177 questions)
- A minus N: +15.09 pp, cluster 95% CI [+14.58, +15.63] (200 patients, 8177 questions)
- B minus N: +14.24 pp, cluster 95% CI [+13.74, +14.76] (200 patients, 8177 questions)
- C minus N: +14.74 pp, cluster 95% CI [+14.24, +15.24] (200 patients, 8177 questions)

## 11. Cluster bootstrap, N/A questions only

- A minus B: +11.68 pp, cluster 95% CI [+9.66, +13.54] (200 patients, 5623 questions)
- A minus C: +17.18 pp, cluster 95% CI [+13.89, +20.30] (200 patients, 5623 questions)
- B minus C: +5.50 pp, cluster 95% CI [+2.83, +8.03] (200 patients, 5623 questions)
- AT minus A: +3.54 pp, cluster 95% CI [+2.26, +4.81] (200 patients, 5623 questions)
- A minus N: +15.88 pp, cluster 95% CI [+14.52, +17.21] (200 patients, 5623 questions)
- B minus N: +4.20 pp, cluster 95% CI [+2.24, +6.21] (200 patients, 5623 questions)
- C minus N: -1.30 pp, cluster 95% CI [-4.14, +1.68] (200 patients, 5623 questions)

## 12. Output-budget audit (billed tokens_out >= 512)

- a: 31.7% overall; by tier {1: 21.8, 2: 25.2, 3: 45.8}
- b: 38.2% overall; by tier {1: 42.1, 2: 41.9, 3: 31.8}
- c: 36.1% overall; by tier {1: 41.9, 2: 38.2, 3: 29.4}
- templated: 30.6%
- no-retrieval: 1.4%

Prompt tokens (billed):

| system   |   count |   mean |   std |   min |   25% |   50% |   75% |    max |
|:---------|--------:|-------:|------:|------:|------:|------:|------:|-------:|
| a        |   13800 |    490 |    79 |   349 |   429 |   483 |   531 |    817 |
| b        |   13800 |   4463 |  6117 |     0 |  1988 |  2597 |  4064 | 128385 |
| c        |   13800 |   2175 |  3589 |   353 |   501 |  1649 |  2053 |  74257 |

## 13. Pooled recall@k (Wilson CI over 13,800 questions)

- b recall@1: 0.570 [0.562, 0.578]
- b recall@3: 0.739 [0.732, 0.746]
- b recall@5: 0.761 [0.753, 0.768]
- b recall@10 identical to recall@5: True
- c recall@1: 0.653 [0.645, 0.661]
- c recall@3: 0.816 [0.810, 0.823]
- c recall@5: 0.839 [0.833, 0.846]
- c recall@10 identical to recall@5: True

## 14. 1024-token sweep split by N/A status

- a substantive (n=288): 17.4% -> 17.7% (delta +0.3 pp)
- a N/A (n=207): 81.6% -> 81.2% (delta -0.5 pp)
- b substantive (n=288): 14.2% -> 14.6% (delta +0.3 pp)
- b N/A (n=207): 64.3% -> 72.9% (delta +8.7 pp)
- c substantive (n=288): 15.6% -> 15.6% (delta +0.0 pp)
- c N/A (n=207): 57.5% -> 69.6% (delta +12.1 pp)

## 15. Fisher exact tests on the earlier 50-failure taxonomy counts

- temporal-anchor 15/50 (A) vs 9/50 (B): p = 0.241
- temporal-anchor 15/50 (A) vs 5/50 (C): p = 0.023

## 16. Post-think scoring (final answer only), N/A-stratified

Accuracy (%) by tier x N/A status:

|            |    n |    A |    B |    C |   AT |    N |
|:-----------|-----:|-----:|-----:|-----:|-----:|-----:|
| (1, False) | 1990 | 28.1 | 19.2 | 21   | 22   |  0   |
| (1, True)  | 2357 | 75   | 63.2 | 54.3 | 90.1 | 56.7 |
| (2, False) | 1785 | 33.1 | 17.6 | 16.6 | 26.9 |  0   |
| (2, True)  | 2562 | 65.1 | 52.3 | 54.1 | 70.2 | 57.4 |
| (3, False) | 4402 | 27.1 | 15.3 | 16.6 | 29.1 |  1.7 |
| (3, True)  |  704 | 54.8 | 61.4 | 62.9 | 52.1 | 46.6 |

Overall (%):
|    |     0 |
|:---|------:|
| A  | 44.67 |
| B  | 33.59 |
| C  | 33    |
| AT | 47    |
| N  | 23.26 |

Substantive only (%):
|    |     0 |
|:---|------:|
| A  | 28.65 |
| B  | 16.79 |
| C  | 17.67 |
| AT | 26.87 |
| N  |  0.93 |

N/A only (%):
|    |     0 |
|:---|------:|
| A  | 67.95 |
| B  | 58.01 |
| C  | 55.29 |
| AT | 76.28 |
| N  | 55.74 |

Cluster bootstrap, all questions, post-think scoring:

- A minus B: +11.08 pp, cluster 95% CI [+10.04, +12.08] (200 patients, 13800 questions)
- A minus C: +11.67 pp, cluster 95% CI [+10.20, +13.09] (200 patients, 13800 questions)
- B minus C: +0.59 pp, cluster 95% CI [-0.64, +1.76] (200 patients, 13800 questions)
- AT minus A: +2.33 pp, cluster 95% CI [+1.70, +2.96] (200 patients, 13800 questions)
- A minus N: +21.41 pp, cluster 95% CI [+20.81, +21.98] (200 patients, 13800 questions)
- B minus N: +10.33 pp, cluster 95% CI [+9.30, +11.37] (200 patients, 13800 questions)
- C minus N: +9.74 pp, cluster 95% CI [+8.36, +11.15] (200 patients, 13800 questions)

Cluster bootstrap, substantive only, post-think scoring:

- A minus B: +11.86 pp, cluster 95% CI [+11.21, +12.53] (200 patients, 8177 questions)
- A minus C: +10.98 pp, cluster 95% CI [+10.34, +11.65] (200 patients, 8177 questions)
- B minus C: -0.88 pp, cluster 95% CI [-1.47, -0.30] (200 patients, 8177 questions)
- AT minus A: -1.79 pp, cluster 95% CI [-2.54, -1.07] (200 patients, 8177 questions)
- A minus N: +27.72 pp, cluster 95% CI [+27.19, +28.30] (200 patients, 8177 questions)
- B minus N: +15.86 pp, cluster 95% CI [+15.24, +16.50] (200 patients, 8177 questions)
- C minus N: +16.74 pp, cluster 95% CI [+16.25, +17.27] (200 patients, 8177 questions)

Cluster bootstrap, N/A only, post-think scoring:

- A minus B: +9.94 pp, cluster 95% CI [+7.56, +12.12] (200 patients, 5623 questions)
- A minus C: +12.66 pp, cluster 95% CI [+9.15, +15.91] (200 patients, 5623 questions)
- B minus C: +2.72 pp, cluster 95% CI [-0.11, +5.31] (200 patients, 5623 questions)
- AT minus A: +8.32 pp, cluster 95% CI [+6.80, +9.79] (200 patients, 5623 questions)
- A minus N: +12.22 pp, cluster 95% CI [+10.79, +13.57] (200 patients, 5623 questions)
- B minus N: +2.28 pp, cluster 95% CI [+0.22, +4.52] (200 patients, 5623 questions)
- C minus N: -0.44 pp, cluster 95% CI [-3.23, +2.68] (200 patients, 5623 questions)

Per-family substantive accuracy (%), post-think scoring:

| family              |    n |    A |    B |    C |   AT |   N |
|:--------------------|-----:|-----:|-----:|-----:|-----:|----:|
| cross_resource      | 1348 | 39.5 | 38.9 | 40.6 | 31.4 | 0   |
| regimen_aggregation | 1822 | 34.6 | 17.9 | 18.9 | 31.8 | 4.1 |
| regimen_compliance  | 2425 | 16.2 |  1.5 |  2.6 | 15.8 | 0.1 |
| temporal_comparison |  818 |  0   |  0   |  0   |  0   | 0   |
| temporal_lookup     | 1764 | 44.6 | 27.5 | 27.8 | 46   | 0   |

Per-tier modal baseline on substantive questions vs post-think accuracy:

- Tier 1: modal 28.1%; A 28.1%; B 19.2%; C 21.0%; AT 22.0%; N 0.0%
- Tier 2: modal 21.8%; A 33.1%; B 17.6%; C 16.6%; AT 26.9%; N 0.0%
- Tier 3: modal 28.7%; A 27.1%; B 15.3%; C 16.6%; AT 29.1%; N 1.7%
