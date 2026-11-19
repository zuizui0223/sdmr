# Synthetic structural-process prospective KT v1 — pre-outcome freeze

**Target:** unopened seeds 96001–96010, eight fixed worlds each, 80 world×seed cases. This prospective task evaluates the *development-selected inferential rules*, not whether real tree crowding or deadwood resources cause growth or beetle composition.

## Frozen design and thresholds

Canonical source: `configs/structural_process_kt_prospective_v1.json`, execution program `experiments/structural_known_truth_prospective_v1.py`.

- **30 truth-positive world×seed cases**: `direct_structure`, `shared_carrier`, `temporal_transfer`. In those synthetic models, a structural component has a nonzero within-site coefficient.
- **50 truth-null or unsupported cases**: `measured_site_proxy`, `observation_selection`, `spatial_only`, `operator_mismatch` (tree endpoint), `omitted_driver`.
- **Prospective success gates** (conjunction, no post-outcome change): positive cases recovered **>=27/30**; false favorable candidate calls **<=1/50**; `observation_selection` held unresolved **10/10**; `omitted_driver` held unavailable **10/10**; shared-carrier world recovered **>=9/10**; all 80 original cases retained; no causal/empirical promotion labels.
- Same fixed 8 independent geographical blocks, 64 physical sites per block, two observed visits and region-equal additive squared error. Same learner and train-only preprocessing as development; one-step individual B addition, complete all-carrier exclusion, spatial versus same-interval temporal change, reference adequacy, observation flag and four comparator rules are all fixed.
- *No fresh field or real observation data are opened.* Original M5, Product-A, real-v5, Structural forest response and blocked Product B remain unchanged.

## Scientific ceilings explicitly frozen

The structural observation-selection quality flag is supplied by the **known-truth generator**, not estimated from sampled data. It is a **source-audit gate**, not an automatic detector of unobserved bias. Positive synthetic performance depends on accurate external selection/attrition documentation. In a real source with unmeasured selection, the correct state is unresolved; the synthetic success alone does not justify calling it measured.

A true process's within-site coefficient is known only because these are generated worlds. The temporal route uses contemporaneously measured two-visit changes, **not prior-only prediction of a future response**. Its positive information is not a proof of causal interventions.

This benchmark is deliberately tailored to eight specified confounding/representation failure families and includes developer-selected margins. Strong performance on new seeds is **conditional synthetic-method generalization across random draws of these same eight worlds**, not new world-family generalization, a physiological mechanism, or universal forest ecology.

The original M5 71/80 and 0/700 arise from a **different known-truth estimand/denominator** and are not added to the synthetic counts in this benchmark.

## One-shot execution gate (before any seed opens)

Scientific source files, exact contract, thresholds, schema and one-shot workflow must be committed and pass tests with **only burned development seeds**. A separate source execution receipt then pins Git blob SHA-1 of exactly seven scientific files plus that source commit SHA. Finally, a commit modifying **only** `configs/structural_process_kt_prospective_v1_activate.lock` can activate the GitHub Actions job. The runner verifies:

1. `HEAD^^` is the frozen scientific source commit, and `HEAD^` changed only the execution receipt.
2. `HEAD` changed only the activation lock with the exact source SHA/10 unused seeds/8 worlds.
3. All seven source blobs match the frozen hashes before any generator call.
4. No already archived prospective result exists in the source branch.

The workflow reports both PASS and FAIL endpoints and archives its first opened result with SHA-256. A failed benchmark is retained without seed/threshold substitution; repeating a run is not independent confirmation.

## Decision ladder

- **If all prospective synthetic gates pass**: advance to a source-and-observation-adequacy adapter, and an *independent* real forest response test under frozen reference/holdout/effort. Do NOT claim empirical method promotion yet.
- **If any synthetic gate fails**: archive as `synthetic_prospective_not_supported`, locate the exact failure, and treat later changes as a new method version with new independent seeds; do not retroactively re-score.
- **If source or run identity fails**: scientific STOP before truth opening, no favorable/null/adverse result.

Developer benchmark (1201–1203) had 24 synthetic cases; single predictor spatial 6/9 positive vs 8/15 false; single predictor spatial+change 6/9 vs 2/15; all-carrier no observation audit 9/9 vs 2/15; all-carrier plus accurate observation audit 9/9 vs 0/15. These are *development results only*. They motivated this preregistration but are not prospective evidence.
