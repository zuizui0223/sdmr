# Product-A v2.7.2 concrete process-identification audit

Status: **reporting-only audit of frozen v2.7.2 evidence / no new experiment / no endpoint change**.

## Why this audit exists

Pooled precision/recall values do not by themselves answer the biological-method question: **what process information was actually identified?** This audit decomposes the frozen 60-case v2.7.2 artifact into exact hidden-truth recovery, process-specific classification and worked examples.

Frozen source: workflow `32629842082`, replicate-A artifact `9490817718`; no selector, threshold, seed, generator or truth label was changed.

## Concrete result 1 — exact generating-process sets were recovered in 55/60 cases

For each frozen case, the `stable_process_core` was compared as a set directly with `true_processes`.

- stable process core exactly equalled the hidden generating-process set in **55/60 cases (91.7%)**;
- canonical selector process set exactly matched truth in **52/60 (86.7%)**;
- perturbation-robust selector process set exactly matched truth in **54/60 (90.0%)**.

The five stable-core errors were completely localized:

- omitted-driver family: 3/10 cases missed true soil from the stable core;
- soft-threshold family: 2/10 cases retained false soil in the stable core;
- asymmetric, Gaussian, interaction and observation-confounded families: **40/40 exact process-set recovery**.

This is a more concrete statement than pooled process precision/recall: the reported output returned the complete hidden process set correctly in 55 of the 60 unused cases.

## Concrete result 2 — process truth often survived exact-model disagreement

Exact fitted-model consensus occurred in only 38/60 cases, so the two ecological selectors selected different fitted candidates in **22/60** cases.

Within those 22 model-disagreement cases:

- the stable process core still exactly equalled hidden process truth in **19/22 (86.4%)**;
- canonical selector process sets were exact in 16/22;
- robust selector process sets were exact in 18/22.

Thus the concrete positive result is not merely that two models sometimes agreed on a process label. In most cases where the fitted models themselves differed, the intersection of their process interpretations still recovered the complete generating-process set.

## Concrete result 3 — worked example: different models, correct process set

`asymmetric`, seed `3103`:

- canonical candidate: `climate_soil_quadratic`;
- canonical processes: `{soil, temperature, water}`;
- robust candidate: `tw_quadratic`;
- robust processes: `{temperature, water}`;
- stable process core: `{temperature, water}`;
- contested: `{soil}`;
- hidden truth: `{temperature, water}`.

The fitted models disagreed and one selector introduced soil, but the set-valued certificate isolated soil as contested and returned the correct stable process set.

## Concrete result 4 — the discriminating process in this frozen test was soil

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

Here the method does not confidently recover the omitted true driver; it downgrades soil to contested. This is the source of the family-level recall loss.

### Soft-threshold boundary

`soft_threshold`, seed `3106`:

- stable core: `{soil, temperature, water}`;
- truth: `{temperature, water}`.

Here soil survives both selectors and becomes a false stable process. This is the source of the family-level precision loss.

## What v2.6 did and did not solve

The preceding v2.6 exclusion certificate should not be described as a positive process-discovery result. In all nine validation taxa the frozen `required_processes` set was empty. Its achievement was **false-necessity control**: no false process was declared required, all true processes remained in the broad possible set, and insufficient calibration could remain unavailable.

Therefore Product A has two different concrete achievements:

1. **v2.6:** prevents unsupported necessity claims but does not positively isolate a required driver in the tested panels;
2. **v2.7.2:** positively recovers the complete generating process set in 55/60 unused cases and in 19/22 cases where exact fitted models disagree, while explicitly exposing its soil-specific false-positive and false-negative boundaries.

## Manuscript consequence

The positive Results section should lead with **exact process-set recovery and worked process examples**, not only pooled P/R values. The manuscript should also state explicitly that selective process truth varied only for soil in this frozen generator suite, so the current result is a strong proof of concept for process-level recovery under model ambiguity rather than a broad demonstration across many independently varying ecological drivers.

Source tables:

- `source_data/nature_v272_exact_process_recovery.csv`;
- `source_data/nature_v272_process_identification_summary.csv`;
- `source_data/nature_v272_worked_process_examples.csv`.
