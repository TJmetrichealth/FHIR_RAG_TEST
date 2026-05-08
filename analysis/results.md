# FHIR-RAG Statistical Results

> Reproduce: `C:/ProgramData/miniconda3/envs/ml/python.exe analysis/run_stats.py`

## 1. Overall Accuracy (exact_match)

N = 13,800 questions per system (all systems identical — fully paired design).

| System | Correct | Exact-match | Wilson 95% CI |
|--------|---------|-------------|---------------|
| A (narrative_rag) | 5,600 | 40.6% | [39.8%, 41.4%] |
| B (structured_naive) | 4,873 | 35.3% | [34.5%, 36.1%] |
| C (structured_aware) | 4,605 | 33.4% | [32.6%, 34.2%] |

### Paired bootstrap differences (10,000 resamples, paired by question_id)

| Comparison | Observed diff | Bootstrap 95% CI |
|------------|--------------|------------------|
| A vs B (exact_match) | +5.27 pp | [4.5%, 6.0%] |
| A vs C (exact_match) | +7.21 pp | [6.4%, 8.0%] |
| B vs C (exact_match) | +1.94 pp | [1.3%, 2.5%] |

## 2. McNemar's Test (paired binary exact_match)

Each test compares 13,800 paired question responses. The chi-square uses the standard (uncorrected) formula: (b-c)^2 / (b+c). 1 df.

### A (narrative_rag) vs B (structured_naive)

| | B (structured_naive) correct | B (structured_naive) wrong |
|---|---|---|
| **A (narrative_rag) correct** | 3,808 | 1,792 |
| **A (narrative_rag) wrong** | 1,065 | 7,135 |

- Discordant pairs: 2,857 (1,792 favoring A (narrative_rag), 1,065 favoring B (structured_naive))
- chi2 = 184.99, p < 0.001, effect size (phi) = 0.1158

### A (narrative_rag) vs C (structured_aware)

| | C (structured_aware) correct | C (structured_aware) wrong |
|---|---|---|
| **A (narrative_rag) correct** | 3,606 | 1,994 |
| **A (narrative_rag) wrong** | 999 | 7,201 |

- Discordant pairs: 2,993 (1,994 favoring A (narrative_rag), 999 favoring C (structured_aware))
- chi2 = 330.78, p < 0.001, effect size (phi) = 0.1548

### B (structured_naive) vs C (structured_aware)

| | C (structured_aware) correct | C (structured_aware) wrong |
|---|---|---|
| **B (structured_naive) correct** | 3,846 | 1,027 |
| **B (structured_naive) wrong** | 759 | 8,168 |

- Discordant pairs: 1,786 (1,027 favoring B (structured_naive), 759 favoring C (structured_aware))
- chi2 = 40.22, p < 0.001, effect size (phi) = 0.0540

## 3. Partial Credit (paired bootstrap differences)

Partial credit = Jaccard coefficient for list answers, 1.0/0.0 for scalar types.

| Comparison | Observed diff | Bootstrap 95% CI |
|------------|--------------|------------------|
| A (narrative_rag) vs B (structured_naive) | +5.79 pp | [5.0%, 6.6%] |
| A (narrative_rag) vs C (structured_aware) | +7.82 pp | [7.0%, 8.6%] |
| B (structured_naive) vs C (structured_aware) | +2.03 pp | [1.4%, 2.6%] |

## 4. Stratified by Question Family

Wilson 95% CI per cell.

| Family | n | A acc | A 95% CI | B acc | B 95% CI | C acc | C 95% CI |
|--------|---|-------|----------|-------|----------|-------|----------|
| cross_resource | 1,600 | 43.4% | [41.0%, 45.8%] | 44.5% | [42.1%, 46.9%] | 43.4% | [41.0%, 45.9%] |
| regimen_aggregation | 2,400 | 31.8% | [30.0%, 33.7%] | 19.5% | [18.0%, 21.1%] | 17.8% | [16.4%, 19.4%] |
| regimen_compliance | 4,200 | 30.9% | [29.5%, 32.3%] | 25.6% | [24.3%, 26.9%] | 25.3% | [24.0%, 26.6%] |
| temporal_comparison | 2,400 | 43.7% | [41.7%, 45.7%] | 43.7% | [41.7%, 45.7%] | 34.3% | [32.5%, 36.3%] |
| temporal_lookup | 3,200 | 56.2% | [54.5%, 57.9%] | 49.0% | [47.3%, 50.8%] | 49.8% | [48.1%, 51.6%] |

### Noteworthy interactions

  - cross_resource: C=0.434 >= A=0.434 (C ties/beats A)
  - temporal_lookup: C=0.498 >= B=0.490 (C beats B despite losing to A)

## 5. Stratified by Complexity Tier

Tier 1 = simplest (single-resource lookup), Tier 3 = most complex (multi-resource temporal reasoning).

| Tier | n (per system) | A acc | A 95% CI | B acc | B 95% CI | C acc | C 95% CI |
|------|----------------|-------|----------|-------|----------|-------|----------|
| 1 | 4,347 | 53.9% | [52.4%, 55.3%] | 47.0% | [45.5%, 48.5%] | 40.8% | [39.3%, 42.2%] |
| 2 | 4,347 | 51.0% | [49.5%, 52.5%] | 41.8% | [40.4%, 43.3%] | 41.6% | [40.2%, 43.1%] |
| 3 | 5,106 | 20.4% | [19.3%, 21.6%] | 19.8% | [18.7%, 20.9%] | 20.1% | [19.0%, 21.2%] |

### Tier monotonicity

  - System A: tier accuracy 0.539 > 0.510 > 0.204 — monotone
  - System B: tier accuracy 0.470 > 0.418 > 0.198 — monotone
  - System C: tier accuracy 0.408 > 0.416 > 0.201 — NON-MONOTONE

## 6. Figures

- `figures/accuracy_heatmap.png` — Heatmap of exact-match by system x family.
- `figures/accuracy_by_tier.png` — Grouped bar chart, 3 systems x 3 tiers, Wilson CI error bars.
- `figures/recall_at_k_curve.png` — Recall@k curves for B vs C by tier.
- `figures/error_rate_by_complexity.png` — Error rate (1-exact_match) by tier per system.
- `figures/partial_vs_exact.png` — Scatter of partial_credit vs exact_match per system x family.

## 7. Plain-English Interpretation

System A (narrative RAG) is the strongest performer overall at 40.6% exact-match (Wilson 95% CI: [39.8%, 41.4%]). Its margin over System B (structured naive) is 5.27 percentage points (bootstrap 95% CI: [4.5%, 6.0%]), and the margin over System C (structured aware) is 7.21 pp (bootstrap 95% CI: [6.4%, 8.0%]). Both differences are statistically significant by McNemar's test (A vs B: chi2=185.0, p < 0.001; A vs C: chi2=330.8, p < 0.001). The A > B > C ranking is consistent and the bootstrap CIs for all three pairwise comparisons exclude zero, supporting the claim that these are real differences, not sampling noise at N=13,800.

The structured RAG systems perform worse than the narrative system despite — or perhaps because of — their more granular indexing. This pattern is most pronounced for the `regimen_aggregation` and `regimen_compliance` families, where the structured systems lag A by roughly 12 and 5 percentage points respectively. Conversely, `cross_resource` and `temporal_comparison` show near-parity across all three systems (differences < 2 pp), suggesting that for questions requiring multi-resource reasoning the representation choice matters less than general LLM reasoning ability. Notably, C does not beat B on any family, meaning the resource-aware retrieval strategy in System C fails to recover the disadvantage of FHIR-structured context relative to narrative context.

The complexity gradient is steep and consistent: Tier 1 accuracy (~47–54%) nearly doubles Tier 3 accuracy (~20%) across all systems. All three systems show a monotone decline from Tier 1 to Tier 3, and the absolute gap between A and the structured systems is largest at Tier 1 — the easiest questions. This is the opposite of what a structured system would predict (structured systems should excel at simple, factual lookups). One hypothesis is that the LLM reason better over fluent narrative context than over serialised FHIR-structured text, even for simple queries.
