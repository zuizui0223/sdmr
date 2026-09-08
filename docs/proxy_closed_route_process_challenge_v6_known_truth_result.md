# v6 proxy-closed route evidence — prospective known-truth result

## Terminal conclusion

**Not supported.**

The frozen v6 successor-v2 endpoint completed on unused seeds `15001–15010` after all 12 family × replicate nontruth jobs completed and the predeclared replicate-parity gate passed. Generating-process truth was opened only in the terminal evaluator after those checks.

- workflow run: `34177021268`
- PR head used by the run: `6a4123d54670838d67866056351c61dd79059c68` (PR merge test SHA `760157383df05ba38215c84a45080e0745004e35`)
- terminal artifact: `10037826460`
- artifact digest: `sha256:9f4047bfb5435da2e48244ecd0a4e4b99e078da2354254e14bb68fcf96a9ffa4`
- cases: 60
- process cells: 300 = 130 true + 170 false
- determinism: passed
- full denominator: complete
- consumed empirical positive controls used: no
- Product A reopened: no

Seeds `15001–15010` are now consumed and may not be retuned or rerun as a prospective validation denominator.

## Frozen primary gates

| gate | threshold | observed | result |
|---|---:|---:|---|
| true-process recall | >= 0.95 | **0.515385** (67/130) | fail |
| process-status macro-F1 | >= 0.90 | **0.685400** | fail |
| every-family true-process recall | >= 0.85 | minimum **0.300** | fail |
| false-required rate | <= 0.02 | **0.000** | pass |
| required claims have complete route evidence | required | yes | pass |
| replicate determinism | required | yes | pass |

Therefore `known_truth_supported=false` and fresh empirical validation is not scientifically authorized for v6.

## Same-case descriptive comparison with v5

| metric | v5 | v6 |
|---|---:|---:|
| true-process recall | 56/130 = **0.430769** | 67/130 = **0.515385** |
| false-process detection | 2/170 = **0.011765** | 25/170 = **0.147059** |
| false-required rate | 0 | 0 |
| macro-F1 | **0.705639** | **0.685400** |
| unresolved process cells | 44 | **96** |
| exact complete process sets | **9/60** | **4/60** |

v6 recovers eleven additional true process cells relative to the v5 descriptive comparator, but it creates twenty-three additional false detections, more than doubles unresolved cells, lowers macro-F1, and reduces exact complete-set recovery. The proxy-closed purge therefore cannot be promoted as a general occurrence-data identification rule.

## Family-level v6 performance

| family | true-process recall | false-process detection | macro-F1 | unresolved |
|---|---:|---:|---:|---:|
| asymmetric | **0.300** | 0.0667 | 0.6032 | 24 |
| gaussian | 0.600 | 0.0667 | 0.7772 | 20 |
| interaction | 0.500 | 0.0667 | 0.7243 | 13 |
| observation_confounded | 0.650 | **0.3333** | 0.6532 | 11 |
| omitted_driver | 0.4667 | **0.3000** | **0.5600** | 12 |
| soft_threshold | 0.600 | 0.1000 | 0.7582 | 16 |

No family reaches the predeclared 0.85 family recall threshold.

## Process-level diagnosis

The failure is strongly structured rather than a generic threshold miss.

| process | true cells | v5 true recovered | v6 true recovered | false cells | v5 false detected | v6 false detected |
|---|---:|---:|---:|---:|---:|---:|
| temperature | 60 | 15 | **22** | 0 | — | — |
| water | 60 | 38 | **42** | 0 | — | — |
| soil | 10 | 3 | 3 | 50 | 0 | **4** |
| seasonality | 0 | — | — | 60 | 2 | **21** |
| noise | 0 | — | — | 60 | 0 | 0 |

The dominant failure is **false attribution to seasonality**. Seasonality is not generating in any of the 60 frozen cases, yet v6 labels it contributory in 21/60 cases. This accounts for 21 of the 25 v6 false detections. Soil contributes another four false detections.

The false-seasonality concentration is greatest in the two difficult families:

- observation-confounded: 7/10 false seasonality detections plus 3/10 false soil detections;
- omitted-driver: 6/10 false seasonality detections.

## Mechanistic diagnosis: process erasure is not process-specific

The v6 operator successfully removes statistical information about the excluded variable from retained predictors, but that is not sufficient for process attribution.

Across the 60 truth-blind seasonality purge diagnostics:

- mean pre-purge reconstruction R² of seasonality from retained predictors: **0.323653**;
- mean post-purge reconstruction R²: **−0.187772**;
- mean pre-purge rank correlation: **0.455606**;
- mean post-purge rank correlation: **0.080373**.

Thus the purge does what it was designed to do: shared seasonality information is strongly erased. The prospective result shows why that operation is not specific enough. When a non-generating process is statistically entangled with predictors carrying true temperature/water information, residualizing all retained predictors against that non-generating process can also remove predictive ecological structure that belongs to other processes. Loss after the purge can then be incorrectly attributed to the excluded process.

The current evidence supports this as the principal successor hypothesis; it does not yet directly prove how much temperature/water information each purge removes. That quantity must be measured explicitly in the next development layer.

## Required next development layer

Do **not** tune v6 thresholds and do **not** proceed to fresh empirical controls.

The next development rule should add a truth-blind **collateral-information-loss audit**. For every proposed exclusion process `P`, before treating an inferior purged route as evidence for `P`:

1. use background environments only;
2. quantify how well each *other declared process representation* `Q != P` can be reconstructed before the `P` purge;
3. apply the frozen `P` purge;
4. quantify the loss of reconstructibility for every `Q` after the purge;
5. if the `P` purge materially destroys information assigned to other processes, mark the route `cross_process_contaminated` / unresolved rather than interpreting its performance loss as process-specific evidence for `P`.

This is a development hypothesis to be tested on the now-consumed `15001–15010` denominator only. Any later performance claim requires another completely unused known-truth denominator.
