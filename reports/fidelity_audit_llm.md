# Fidelity Audit - Aggregate

**O1 gate (>=90% weighted entity recall): PASS**

## Headline stats

| Metric | Value |
| --- | --- |
| n (patients audited) | 200 |
| Weighted entity recall | 1.0000 (100.0%) |
| Macro-average score | 1.0000 (100.0%) |
| Median score | 1.0000 |
| Stdev | 0.0000 |
| Min score | 1.0000 |
| Max score | 1.0000 |
| % patients scoring >= 0.90 | 100.0% |
| Total entity checks | 2403 |
| Total entities found | 2403 |
| Total entities missed | 0 |

## Score distribution
```
  [0.0-0.1)   (0)
  [0.1-0.2)   (0)
  [0.2-0.3)   (0)
  [0.3-0.4)   (0)
  [0.4-0.5)   (0)
  [0.5-0.6)   (0)
  [0.6-0.7)   (0)
  [0.7-0.8)   (0)
  [0.8-0.9)   (0)
  [0.9-1.0)  ######################################## (200)
```

## Per-tier breakdown

| Tier | n | Mean score | Median | % >= 0.90 | Weighted recall |
| --- | --- | --- | --- | --- | --- |
| 1 | 63 | 1.0000 | 1.0000 | 100.0% | 1.0000 (PASS) |
| 2 | 63 | 1.0000 | 1.0000 | 100.0% | 1.0000 (PASS) |
| 3 | 74 | 1.0000 | 1.0000 | 100.0% | 1.0000 (PASS) |

## Per-entity-class breakdown

| Entity class | Total checks | Found | Missed | Pass-rate |
| --- | --- | --- | --- | --- |
| `tier_description` | 200 | 200 | 0 | 1.000 (100.0%) |
| `regimen_start` | 200 | 200 | 0 | 1.000 (100.0%) |
| `regimen_end` | 200 | 200 | 0 | 1.000 (100.0%) |
| `descriptor` | 348 | 348 | 0 | 1.000 (100.0%) |
| `schedule` | 285 | 285 | 0 | 1.000 (100.0%) |
| `admin_date` | 822 | 822 | 0 | 1.000 (100.0%) |
| `admin_count` | 274 | 274 | 0 | 1.000 (100.0%) |
| `prn_indication` | 74 | 74 | 0 | 1.000 (100.0%) |

## Top-10 missing-item categories (by miss count)


## Top-10 worst-performing narratives (spot-check list)

| Rank | Patient ID | Tier | Score | n_checks | n_found | Missing categories |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `014abeea-627d-f33c-834c-e2a6605046ee` | 2 | 1.0000 | 9 | 9 |  |
| 2 | `02dc5960-eec7-7c95-977a-fbfef0c7318a` | 3 | 1.0000 | 18 | 18 |  |
| 3 | `03a54374-164b-4769-e60f-da6c62772663` | 3 | 1.0000 | 18 | 18 |  |
| 4 | `05ab7b8b-6463-79a7-b060-2dfcc8ed4f51` | 1 | 1.0000 | 8 | 8 |  |
| 5 | `076af3f3-4441-9c72-e459-b9c59305846c` | 2 | 1.0000 | 9 | 9 |  |
| 6 | `082fded1-1ba0-9bf2-6dee-a033676dd040` | 1 | 1.0000 | 8 | 8 |  |
| 7 | `086c349f-0899-9a6c-984d-63268dfd200b` | 2 | 1.0000 | 9 | 9 |  |
| 8 | `09869e74-030e-5a53-b592-bbee5458ab64` | 1 | 1.0000 | 8 | 8 |  |
| 9 | `0b2a436c-3571-c712-e925-75e895a5b489` | 3 | 1.0000 | 18 | 18 |  |
| 10 | `0b2e2350-4d13-3a5e-901d-f59e68f47b3c` | 3 | 1.0000 | 18 | 18 |  |

## All patients below 0.90
_None._

