# Feature Documentation — O6 Feature Arm

All features are patient-level (one row per patient). Calculations reference
`features/adherence_metrics.py` where applicable.

## FS-Structured

| Name | Source | Formula / derivation | Motivation |
|------|--------|----------------------|------------|
| mpr_90d | FHIR MedicationAdministration | `compute_mpr(admins_90d, interval, 90)` | Medication Possession Ratio over the final 90 days |
| mpr_180d | FHIR MedicationAdministration | `compute_mpr(admins_180d, interval, 180)` | MPR over the final 180 days |
| mpr_full | FHIR MedicationAdministration | `compute_mpr(admins_before_ref, interval, days_since_first)` | MPR over the full observation window |
| pdc_90d | FHIR MedicationAdministration | `compute_pdc(admins_90d, interval, ref-90d, ref)` | Proportion of Days Covered over final 90 days |
| pdc_full | FHIR MedicationAdministration | `compute_pdc(admins_before_ref, interval, first_dose, ref)` | PDC over the full observation window |
| gap_mean_90d | FHIR MedicationAdministration | `mean(consecutive_dose_gaps_in_final_90d)` | Mean inter-dose gap as proxy for regularity |
| gap_std_90d | FHIR MedicationAdministration | `std(consecutive_dose_gaps_in_final_90d)` | Variability in dosing intervals |
| gap_max_90d | FHIR MedicationAdministration | `max(consecutive_dose_gaps_in_final_90d)` | Captures single worst dropout event |
| n_events_60d | FHIR MedicationAdministration | Count of spec-adm events with effectiveDateTime in [ref-60d, ref] | Intensity of recent medication activity |
| days_since_last | FHIR MedicationAdministration | `days_since_last_dose(admins_before_ref, ref)` | Recency of most recent dose |
| tier_1 | questions.jsonl / CarePlan | One-hot for tier == 1 | Regimen complexity indicator |
| tier_2 | questions.jsonl / CarePlan | One-hot for tier == 2 | Regimen complexity indicator |
| tier_3 | questions.jsonl / CarePlan | One-hot for tier == 3 | Regimen complexity indicator |
| age_years | FHIR Patient.birthDate | `(reference_date - birthDate).days / 365.25` | Demographic confounder |
| n_MedicationRequest | FHIR Bundle | Count of MedicationRequest resources | Regimen breadth |
| n_MedicationAdministration | FHIR Bundle | Count of MedicationAdministration resources | Overall adherence volume |
| n_CarePlan | FHIR Bundle | Count of CarePlan resources | Structured care plan presence |
| n_Observation | FHIR Bundle | Count of Observation resources | Monitoring intensity |
| n_Condition | FHIR Bundle | Count of Condition resources | Disease burden |
| n_Procedure | FHIR Bundle | Count of Procedure resources | Intervention history |

## FS-Narrative

All features are computed by deterministic regex over `narratives/llm_narratives/{patient}.txt`.
No LLM scoring is used.

| Name | Source | Formula / derivation | Motivation |
|------|--------|----------------------|------------|
| n_date_mentions | LLM narrative | `len(re.findall(r"\b\d{4}-\d{2}-\d{2}\b", text))` | Narrative specificity; more dates → richer temporal content |
| n_miss_words | LLM narrative | Count of missed/gap/discontinue/delay/skip and synonyms | Direct non-adherence signal in the narrative |
| n_dose_count_mentions | LLM narrative | Count of "X doses"/"X administrations" patterns | Quantitative dose count signals |
| n_tier_mentions | LLM narrative | Count of "tier 1/2/3" or "T1/T2/T3" mentions | Regimen complexity signal |
| narrative_length_tokens | LLM narrative | `len(text) // 4` (char-level estimate) | Narrative completeness proxy |
| n_negation_near_dose | LLM narrative | Count of negation cues (no/not/never) within 30 chars of a dose-event word | Proxy for narrated missed doses |

## FS-Aware

Features aggregated per patient over all 69 questions in `results/raw/c.jsonl`.

| Name | Source | Formula / derivation | Motivation |
|------|--------|----------------------|------------|
| mean_expansion_chunks | System C trace | `mean(extras.n_expansion_chunks)` across all questions | Reference-graph expansion depth; higher → more cross-resource connections found |
| mean_distinct_rtypes | System C trace | `mean(len(set(chunk.resource_type for chunk in retrieved)))` | Diversity of retrieved resource types per query |
| mean_score_top5 | System C trace | `mean(retrieved[:5][i].score)` averaged across questions | Average similarity of top-5 retrieved chunks |
| frac_type_filter_nonempty | System C trace | `mean(bool(extras.type_filter))` | Fraction of queries where System C invoked a resource-type filter |
| mean_rt_MedAdmin | System C trace | Mean count of MedicationAdministration chunks per question | Administration-data retrieval intensity |
| mean_rt_MedReq | System C trace | Mean count of MedicationRequest chunks per question | Prescription-data retrieval intensity |
| mean_rt_CarePlan | System C trace | Mean count of CarePlan chunks per question | Care-plan retrieval intensity |
| mean_rt_other | System C trace | Mean count of other resource type chunks per question | Residual resource diversity |
