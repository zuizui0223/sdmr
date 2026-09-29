# SDMR fresh empirical v3 — SoilGrids support-eligibility design

## Motivation

SDMR v6 prospective known-truth v2 passed KT-A through KT-F.

The first 50-taxon fresh empirical programme nevertheless stopped before model fitting:

- 37/50 taxa passed the frozen 46-predictor complete-case gate;
- 13/50 failed;
- every individual blocker belonged to the four frozen SoilGrids topsoil layers;
- no CHELSA predictor was an individual blocker;
- answer-check access remained false;
- model fitting remained false.

The failure was therefore an **eligibility-design problem**, not empirical evidence against the SDMR method.

## v3 change

v3 makes one prospective design change:

> SoilGrids **support availability** becomes a taxon-eligibility criterion before the final 50 taxa are frozen.

It does not delete soil predictors or relax completeness thresholds.

## Two-stage denominator

1. Select exactly **80 candidate taxa** using GBIF metadata/coordinate criteria only.
2. For all 80, freeze the same coordinate-only outer split and 300-km model-pool-only target-group background.
3. At model-pool and background coordinates only, read the four SoilGrids layers but persist only **finite versus missing bits**.
4. A candidate is support-eligible only if:
   - model-pool joint four-layer finite fraction ≥0.80;
   - model-pool joint finite rows ≥50;
   - 300-km background joint finite rows ≥4000/5000.
5. Take the first 50 eligible candidates in the already frozen hash order.

If fewer than 50 of 80 pass, the programme terminates unavailable. No extra candidate search is allowed.

## Information boundary

Before the final 50 are frozen, v3 may use:

- GBIF identity/count/coordinate metadata;
- coordinate-only outer split membership;
- model-pool-only background geometry;
- SoilGrids finite/missing bits.

It may not use:

- numeric SoilGrids values;
- CHELSA values;
- answer-check SoilGrids support or environmental values;
- model fit;
- prediction metrics;
- process states;
- EMP-A through EMP-F outcomes.

## Scientific consequence

This preserves the original 46-predictor process registry and the exact v2 complete-case thresholds while moving a known source-support condition to the only place where it belongs: **pre-outcome cohort eligibility**.

The positive SDMR v6 known-truth result remains unchanged.
