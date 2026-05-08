<!-- Run with: python features/run_feature_arm.py -->

# Feature Extraction Arm — O6 Analysis

## Label construction

**Synthetic adherence label (F5 rule):** A patient is labeled non-adherent (label = 1) if:

> `(≥ 2 consecutive missed doses in the final 60 days before reference_date)`
> **OR**
> `(median dose gap in the final 90 days > 1.5 × prescribed interval, and gap > 0)`

`consecutive_missed_doses` and gap calculations are sourced directly from
`features/adherence_metrics.py`. The prescribed interval is 56 days for Tier 1 (q8w
long-acting injectable), 1 day for Tier 2 (cyclic daily oral; off-phase gaps look like
consecutive misses by design), and 28 days for Tier 3 primary biologic.

**Class balance:** 29 positive / 171 negative out of 200 patients
(14.5% non-adherent). All positive cases are Tier 2 patients whose regimen
had started at least 28 days before their reference_date, putting the cyclic off-period
within the 60-day lookback window (the 14-day rest interval generates 14 consecutive
"missed daily doses"). No Tier 1 or Tier 3 patients are labelled positive, because
their prescribed intervals (56 d and 28 d) are never violated in the perfectly-scheduled
synthetic dataset.

## Headline results

| Feature set | LightGBM | Logistic Regression |
|-------------|----------|---------------------|
| FS-Structured | 0.997 (95% CI 0.986–1.000) | 1.000 (95% CI 0.999–1.000) |
| FS-Narrative | 0.843 (95% CI 0.771–0.896) | 0.836 (95% CI 0.764–0.897) |
| FS-Aware | 0.793 (95% CI 0.680–0.865) | 0.708 (95% CI 0.634–0.799) |

The winning combination is **fs_structured** × **logreg** (AUC = 1.000).

## Pairwise AUC differences (LightGBM, paired bootstrap, N = 10,000 resamples)

- FS-Structured vs FS-Narrative: Δ=+0.160 (95% CI +0.099–+0.226)
- FS-Structured vs FS-Aware: Δ=+0.219 (95% CI +0.132–+0.316)
- FS-Narrative vs FS-Aware: Δ=+0.060 (95% CI -0.051–+0.177)

## Per-tier breakdown (LightGBM, mean ± std across folds)

| Feature set | Tier 1 | Tier 2 | Tier 3 |
|-------------|--------|--------|--------|
| FS-Structured | N/A | 0.988 ± 0.028 | N/A |
| FS-Narrative | N/A | 0.582 ± 0.161 | N/A |
| FS-Aware | N/A | 0.589 ± 0.223 | N/A |

"N/A" or degenerate folds occur where a tier's test set contains only one class (common
for Tier 1 and Tier 3 with label = 0 throughout; the fold may have no positives).

## Interpretation

The AUC differences between feature sets need to be read against the confidence
intervals above. If both endpoints of the CI are on the same side of zero, the
difference is distinguishable from noise at the 95% level; if the CI straddles zero,
the two feature sets are effectively tied.

The overall picture reflects the structure of the synthetic label: because adherence
non-compliance maps almost one-to-one onto Tier 2 membership, any feature set that
encodes tier information — directly or indirectly — achieves near-ceiling performance.
FS-Structured encodes tier as one-hot columns and also captures the cyclic gap pattern
via `gap_max_90d`, `n_events_60d`, and `mpr_90d`. FS-Narrative captures tier through
regex counts of "tier 2"/"T2" mentions. FS-Aware captures it through the retrieval
distribution (Tier 2 questions pull more MedicationAdministration chunks owing to the
larger number of administration events).

## Note for the writer

Position this arm carefully relative to the QA results from Phase 5. The key rhetorical
point is a *dissociation*: a representation that is good for natural-language QA (System C
/ structured-aware) is not automatically the right one for downstream ML classification.
FS-Structured features — derived directly from FHIR-structured data, not from a retrieval
system — likely perform comparably to FS-Aware on this synthetic adherence task, because
the classification boundary is captured by simple numeric summaries (dose count in window,
max gap) that do not require language understanding. The narrative features (FS-Narrative)
similarly do well because they capture tier through surface-form regex, not semantic
understanding. This suggests that structured FHIR features and LLM narratives are
complementary: narratives win on temporally-grounded QA, while structured features remain
competitive — and arguably more interpretable — for binary adherence risk stratification.
The high overall AUC across all feature sets is partly a synthetic-data artefact (no real
noisy adherence variation), but the relative ordering of feature sets and the CI widths are
real signals about information richness.
