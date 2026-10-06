# Post-think re-scoring (paper v2)

> Reproduce: `python analysis/run_postthink_rescore.py`

Scoring applied to the text after `</think>` only; unclosed responses scored as empty.

## Closed think blocks

- a: 9534/13800 = 69.1%
- b: 8835/13800 = 64.0%
- c: 9037/13800 = 65.5%
- n: 13600/13800 = 98.6%
- at: 9698/13800 = 70.3%

## Exact-match accuracy, original vs post-think scoring (%)

| arm   |   orig_all |   post_all |   orig_subst |   post_subst |   orig_na |   post_na |   orig_correct_post_wrong |   orig_wrong_post_correct |
|:------|-----------:|-----------:|-------------:|-------------:|----------:|----------:|--------------------------:|--------------------------:|
| a     |      40.58 |      44.67 |        15.96 |        28.65 |     76.38 |     67.95 |                       665 |                      1229 |
| b     |      35.31 |      33.59 |        15.1  |        16.79 |     64.7  |     58.01 |                       693 |                       455 |
| c     |      33.37 |      33    |        15.6  |        17.67 |     59.2  |     55.29 |                       663 |                       612 |
| n     |      25.17 |      23.26 |         0.87 |         0.93 |     60.5  |     55.74 |                       337 |                        74 |
| at    |      41.32 |      47    |        14.77 |        26.87 |     79.92 |     76.28 |                       407 |                      1191 |

## Post-think accuracy by tier (%)

|   tier |    a |   at |    b |    c |    n |
|-------:|-----:|-----:|-----:|-----:|-----:|
|      1 | 53.5 | 58.9 | 43.1 | 39.1 | 30.7 |
|      2 | 51.9 | 52.4 | 38.1 | 38.7 | 33.8 |
|      3 | 30.9 | 32.2 | 21.7 | 23   |  7.9 |

## Post-think accuracy by family x N/A (%)

|                                |    a |   at |    b |    c |    n |
|:-------------------------------|-----:|-----:|-----:|-----:|-----:|
| ('cross_resource', False)      | 39.5 | 31.4 | 38.9 | 40.6 |  0   |
| ('cross_resource', True)       | 92.1 | 73   | 66.3 | 50.4 | 50   |
| ('regimen_aggregation', False) | 34.6 | 31.8 | 17.9 | 18.9 |  4.1 |
| ('regimen_aggregation', True)  | 72.1 | 80.8 | 64   | 67.1 | 21.8 |
| ('regimen_compliance', False)  | 16.2 | 15.8 |  1.5 |  2.6 |  0.1 |
| ('regimen_compliance', True)   | 53.9 | 74.8 | 48.9 | 50.4 | 82.3 |
| ('temporal_comparison', False) |  0   |  0   |  0   |  0   |  0   |
| ('temporal_comparison', True)  | 60.4 | 73.6 | 63   | 46.8 | 39.8 |
| ('temporal_lookup', False)     | 44.6 | 46   | 27.5 | 27.8 |  0   |
| ('temporal_lookup', True)      | 87.8 | 79.8 | 60   | 66.8 | 55.2 |
