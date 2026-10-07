# SDMR fresh empirical v5 — sealed validation freeze

This stage is frozen **before the v5 model-pool result and before any sealed answer-check coordinate or environmental value is opened**.

The evaluation denominator remains exactly 50 taxa. A taxon that cannot be evaluated is not dropped. Its primary reconstruction gain is set to zero for EMP-A/EMP-B, while EMP-C fails because all 50 taxa are required to have an evaluable primary SDMR route and matched primary comparator.

## Evaluation rows

For each taxon:

- sealed presences are the frozen `outer_role=answer_check` occurrence IDs;
- those IDs are materialized exactly once from the same GBIF 2026-08-01 snapshot and frozen occurrence QC;
- no missing or duplicate sealed ID may be substituted;
- numeric values use the unchanged 46-predictor registry and six predeclared structural source-decoding rules;
- occurrence scoring uses every sealed occurrence that is complete across all 46 decoded predictors;
- evaluation background is the already-frozen 300-km background with `background_rank % 5 == 0`, restricted only by the already-frozen complete-case flag;
- answer-check rows never enter fitting, process-state identification, comparator selection, or any refit.

## Primary comparison

The primary paired taxon outcome is

`balanced log score(SDMR process-first) - balanced log score(matched-learner flat predictive selector)`.

The same occurrence and background rows are used for both routes within a taxon. ROC AUC on those same rows is the prediction-safety guardrail.

## Promotion

- EMP-A: mean gain over all 50 declared taxa >= 0.01.
- EMP-B: 20,000-replicate paired taxon bootstrap, seed 20260926, 95% lower bound > 0.
- EMP-C: all 50 taxa evaluable and mean paired AUC difference >= -0.02.
- EMP-D: stable sharp process fraction >= 0.80 over the frozen 50 x 6 denominator.
- EMP-E: abstention-integrity violations = 0.
- EMP-F: exactly all 50 taxa remain in the evaluation table.

No failed gate may be repaired after sealed data are opened.
