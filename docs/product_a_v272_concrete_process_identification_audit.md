# Product-A v2.7.2 concrete process-identification audit

Status: **reporting-only audit of frozen v2.7.2 evidence / no new experiment / no endpoint change**.

## Why this audit exists

Pooled precision/recall values do not by themselves answer the biological-method question: **what process information was actually identified?** This audit decomposes the frozen 60-case v2.7.2 artifact into exact hidden-truth recovery, process-specific classification, comparator performance and worked examples.

Frozen source: workflow `32629842082`, replicate-A artifact `9490817718`; no selector, threshold, seed, generator or truth label was changed.

## Concrete result 1 — exact generating-process sets were recovered in 55/60 cases

For each frozen case, the `stable_process_core` was compared as a set directly with `true_processes`.

- stable process core exactly equalled the hidden generating-process set in **55/60 cases (91.7%)**;
- canonical ecological selector process set exactly matched truth in **52/60 (86.7%)**;
- perturbation-robust ecological selector process set exactly matched truth in **54/60 (90.0%)**;
- the AUC-selected candidate had exact driver-process recovery in **50/60 (83.3%)**.

The stable process certificate therefore recovered the complete process set in five more cases than the AUC-selected fitted candidate under the same frozen controlled-truth suite. This is a descriptive reporting comparison of already frozen outcomes, not a newly preregistered superiority endpoint.

Family-level exact process-set recovery (stable core versus AUC-selected candidate):

- asymmetric: **10/10 vs 9/10**;
- Gaussian: **10/10 vs 9/10**;
- interaction: **10/10 vs 9/10**;
- observation-confounded: **10/10 vs 5/10**;
- omitted-driver: **7/10 vs 10/10**;
- soft-threshold: **8/10 vs 8/10**.

Thus the process certificate is not uniformly superior. Its strongest gain is under observation confounding, whereas the conventional AUC role is better in the omitted-driver family.

## Concrete result 2 — observation confounding was actually corrected

The observation-confounded family supplies the clearest positive mechanism result.

Hidden ecological truth in all ten cases was `{temperature, water}`, while a separate `recording_bias` predictor affected where records were observed.

For the AUC-selected role:

- `niche_plus_observer` selected in 5/10 cases → driver-process F1 = 1.0;
- `observer_only` selected in **5/10** cases → driver-process precision = recall = F1 = **0.0**.

Thus ordinary discrimination selection sometimes explained the records entirely through the observation process and discarded the ecological niche drivers.

For Product A's ecological selectors:

- canonical ecological selector chose `niche_plus_observer` in **10/10**;
- perturbation-robust selector chose `niche_plus_observer` in **10/10**;
- observation-process information was not promoted to the ecological process set;
- stable process core = `{temperature, water}` in **10/10**;
- exact hidden process-set recovery = **10/10**.

This is a concrete problem solved by the method: **record-prediction success caused process misattribution in half of the observation-confounded AUC cases, while the ecological/observation separation recovered the generating ecological process set in every case.**

## Concrete result 3 — process truth survived exact-model disagreement

Exact fitted-model consensus occurred in only 38/60 cases, so the two ecological selectors selected different fitted candidates in **22/60** cases.

Within those 22 model-disagreement cases:

- the stable process core still exactly equalled hidden process truth in **19/22 (86.4%)**;
- canonical selector process sets were exact in 16/22;
- robust selector process sets were exact in 18/22.

Thus the positive result is not merely that two models sometimes agree. In most cases where the fitted models themselves differed, the intersection of their process interpretations still recovered the complete generating-process set.

## Concrete result 4 — worked example: different models, correct process set

`asymmetric`, seed `3103`:

- canonical candidate: `climate_soil_quadratic`;
- canonical processes: `{soil, temperature, water}`;
- robust candidate: `tw_quadratic`;
- robust processes: `{temperature, water}`;
- stable process core: `{temperature, water}`;
- contested: `{soil}`;
- hidden truth: `{temperature, water}`.

The fitted models disagreed and one selector introduced soil, but the set-valued certificate isolated soil as contested and returned the correct stable process set.

## Concrete result 5 — the discriminating process in this frozen test was soil

The frozen process registry represented three ecological process labels: `temperature`, `water`, and `soil`.

Important limitation: temperature and water were true generating processes in **all 60 cases** and were present in the stable core in **all 60 cases**. Their perfect precision/recall therefore demonstrates retention of invariant true processes, not presence-versus-absence discrimination.

Soil is the process that actually tested selective identification because its truth status varied:

### Soil truly generating: 10 cases

- stable core: **7/10**;
- contested: **3/10**;
- absent from both ecological selector process sets: **0/10**.

Thus all 10 true-soil cases were retained somewhere in the set-valued certificate; seven were promoted to stable and three were explicitly left contested rather than silently dropped.

### Soil not generating: 50 cases

- incorrectly stable: **2/50**;
- contested: **7/50**;
- absent from both selector process sets: **41/50**.

For a strict stable/not-stable interpretation of soil:

- stable-soil precision = **7/9 = 77.8%**;
- stable-soil recall = **7/10 = 70.0%**;
- specificity = **48/50 = 96.0%**.

The set-valued interpretation is more informative than this binary summary: all three stable-core false negatives were retained as `contested`, while 41/50 non-generating soil cases were excluded by both ecological selectors.

## Concrete failure envelope

### Omitted-driver boundary

`omitted_driver`, seed `3101`:

- stable core: `{temperature, water}`;
- contested: `{soil}`;
- truth: `{soil, temperature, water}`.

Here the method does not confidently recover the omitted true driver; it downgrades soil to contested. Across the family, exact stable-core recovery is 7/10 while the AUC-selected role is exact in 10/10. This is the clearest case where the Product-A certificate is more conservative but less complete than the conventional comparator.

### Soft-threshold boundary

`soft_threshold`, seed `3106`:

- stable core: `{soil, temperature, water}`;
- truth: `{temperature, water}`.

Here soil survives both selectors and becomes a false stable process. This is the source of the family-level precision loss.

## What v2.6 did and did not solve

The preceding v2.6 exclusion certificate should not be described as a positive process-discovery result. In all nine validation taxa the frozen `required_processes` set was empty. Its achievement was **false-necessity control**: no false process was declared required, all true processes remained in the broad possible set, and insufficient calibration could remain unavailable.

Therefore Product A has two different concrete achievements:

1. **v2.6:** prevents unsupported necessity claims but does not positively isolate a required driver in the tested panels;
2. **v2.7.2:** positively recovers the complete generating process set in 55/60 unused cases and in 19/22 cases where exact fitted models disagree, with the clearest gain over AUC occurring when observation bias otherwise selects an observation-only explanation.

## Manuscript consequence

The positive Results section should lead with **exact process-set recovery, the observation-confounding correction and worked process examples**, not pooled P/R values alone. The manuscript must also state that selective process truth varied only for soil in this frozen generator suite, so the current result is a strong proof of concept for process-level recovery under model ambiguity rather than broad validation across many independently varying ecological drivers.

Source tables:

- `source_data/nature_v272_exact_process_recovery.csv`;
- `source_data/nature_v272_process_identification_summary.csv`;
- `source_data/nature_v272_selector_process_comparison.csv`;
- `source_data/nature_v272_worked_process_examples.csv`.
