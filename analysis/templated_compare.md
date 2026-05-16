# Templated-Narrative QA Arm: Comparison vs Canonical System A

> Source: `results/scored_templated/scored.csv` and `results/scored.csv` (A only)
>
> Addresses reviewer revision #1. The templated-narrative arm runs the same
> System A pipeline against deterministic templated narratives (no LLM) to
> disambiguate 'narrative format wins' from 'LLM-generated narratives win.'

## Headline

- **Templated A-T accuracy**: 41.3% [40.5%, 42.1%]
- **Canonical A accuracy**: 40.6% [39.8%, 41.4%]
- **Paired delta (A-T - A)**: +0.74pp 95%CI=[+0.13pp, +1.34pp]
- **Decision rule outcome**: H1 (templated matches LLM-narrative within +/-2pp)

## Per-tier breakdown

| Tier | n | A-T acc | A acc | Delta | 95% CI |
|---|---|---|---|---|---|
| 1 | 4347 | 57.3% | 53.9% | +3.43pp | [+2.42pp, +4.44pp] |
| 2 | 4347 | 50.9% | 51.0% | -0.07pp | [-1.33pp, +1.20pp] |
| 3 | 5106 | 19.6% | 20.4% | -0.86pp | [-1.70pp, -0.04pp] |

## Per-family breakdown

| Family | n | A-T acc | A acc | Delta | 95% CI |
|---|---|---|---|---|---|
| cross_resource | 1600 | 41.1% | 43.4% | -2.25pp | [-4.25pp, -0.25pp] |
| regimen_aggregation | 2400 | 24.5% | 31.8% | -7.29pp | [-8.92pp, -5.75pp] |
| regimen_compliance | 4200 | 32.6% | 30.9% | +1.79pp | [+0.81pp, +2.79pp] |
| temporal_comparison | 2400 | 53.9% | 43.7% | +10.21pp | [+8.62pp, +11.75pp] |
| temporal_lookup | 3200 | 56.0% | 56.2% | -0.22pp | [-1.28pp, +0.84pp] |

## Interpretation rule used

- **H1 (narrative format wins, no LLM-specific advantage):** Paired-delta CI straddles zero, or both endpoints within +/-2pp. Implication: 'narrative format wins' is supported; LLM-narrative-specific lexical regularity is not the driver.
- **H2 (LLM-narrative specific advantage):** Paired-delta CI lower bound below -3pp. Implication: LLM narratives are doing more than the format alone; framing should soften to 'LLM-generated narratives win, beyond format.'

**This run:** H1 (templated matches LLM-narrative within +/-2pp)
