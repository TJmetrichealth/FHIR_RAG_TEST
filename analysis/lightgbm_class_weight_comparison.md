# LightGBM class_weight=balanced re-run (reviewer revision #8)

> Source: `features/results_aggregate.csv` (new, class-weighted) and
> `features/results_aggregate_unweighted_backup.csv` (old, default LightGBM).

The reviewer flagged an inconsistency in the feature-extraction arm: logistic
regression used `class_weight='balanced'` while LightGBM used defaults. Both
classifiers are now run with `class_weight='balanced'` in lightgbm 4.6.0
(sklearn-compatible API).

## AUC-ROC comparison (5-fold CV, all patients)

| Feature set | LightGBM (old, unweighted) | LightGBM (new, balanced) | Delta | Logistic (balanced) |
|---|---|---|---|---|
| FS-Structured | 0.997 [0.986, 1.000] | 0.997 [0.983, 1.000] | 0.000 | 1.000 [0.999, 1.000] |
| FS-Narrative | 0.843 [0.771, 0.896] | 0.846 [0.761, 0.889] | +0.003 | 0.836 [0.764, 0.897] |
| FS-Aware | 0.793 [0.680, 0.865] | 0.769 [0.660, 0.844] | -0.024 | 0.708 [0.634, 0.799] |

CIs are 10,000-resample bootstrap. All inter-method CI overlaps are heavy; no
delta is statistically distinguishable from zero.

## AUPRC comparison

| Feature set | LightGBM (old) | LightGBM (new) | Delta |
|---|---|---|---|
| FS-Structured | 0.971 | 0.971 | 0.000 |
| FS-Narrative | 0.538 | 0.501 | -0.037 |
| FS-Aware | 0.455 | 0.412 | -0.043 |

## Interpretation

The class-weighting change does not materially affect the qualitative results:

1. **Relative ordering preserved:** FS-Structured >> FS-Narrative > FS-Aware
   in both runs.
2. **FS-Structured remains tautologically high** (AUC 0.997 unchanged); this is
   the partly-entailed result the Discussion already concedes.
3. **FS-Narrative vs FS-Aware delta** widens slightly with class-weighting
   (0.846 vs 0.769, delta +0.077) compared to the unweighted run (0.843 vs
   0.793, delta +0.050). Both CIs still overlap; the comparison remains a tie
   within bootstrap uncertainty.
4. **AUPRC drops modestly for the narrative and aware feature sets** under
   class-weighting. With 14.5% positive prevalence the threshold-dependent
   metric is more sensitive to weighting than AUC-ROC. AUPRC is reported only
   as a secondary metric (per the original decisions-log entry).

## Conclusion

Standardising LightGBM to `class_weight='balanced'` for parity with logistic
regression preserves every qualitative claim in the original feature-arm
analysis. No abstract or contribution-list claim depends on which weighting was
used. Paper edits report the new (balanced) numbers and note the change inline
in Section 4.7 plus a Discussion sentence.
