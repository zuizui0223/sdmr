# SDMR fresh empirical v3 — SoilGrids-support-eligible prefreeze

## Why v3 exists

The SDMR v6 process-identification method has already passed its fresh prospective known-truth gate on seeds 74001–74020:

- 71/80 ODO-positive states recovered;
- 0/700 false positives on ODO-replaceable cells;
- 0/60 over-resolution on unresolved cells;
- 0/60 structural-refusal violations;
- all six informative control worlds authorized 20/20;
- KT-A–KT-F all passed.

The first empirical 50-taxon programme then stopped **before model fitting and before sealed answer-check access** because 13/50 taxa lacked enough complete support across the four frozen SoilGrids topsoil layers.

That is a source-support design problem, not evidence against the method.

## New design

v3 makes support eligibility part of taxon admission **before the final 50 taxa are chosen**.

The selection has three locked stages.

### Stage 1 — finite metadata-only candidate roster

Build exactly 200 candidate plant taxa from the same GBIF monthly snapshot and the same occurrence/QC rules, after excluding:

- every historical Product-A taxon/candidate;
- all 50 taxa consumed by the v2 empirical programme.

No environmental values are used at this stage.

### Stage 2 — technical feature-support eligibility

For each of the 200 candidates, construct only:

- model-pool occurrence coordinates;
- the primary 300-km target-group background.

The sealed answer-check remains unavailable.

Extract the same frozen 46 predictors and apply the already-audited structural CHELSA source-decoding rules.

A taxon is support-eligible only if, across all 46 predictors:

- model-pool complete-case retention >= 0.80;
- model-pool complete rows >= 50;
- primary-background complete rows >= 4000.

This is a binary technical gate. Passing by a wide margin cannot improve a taxon's rank.

### Stage 3 — final 50

From support-eligible candidates only, select exactly 50 using a second frozen SHA-256 ordering with max one taxon per genus and max two per family.

If 50 cannot be filled, v3 terminates unavailable. The roster is not expanded and thresholds are not relaxed.

## Information barrier

Before the final 50 are frozen, v3 may not read:

- sealed answer-check coordinates or features;
- prediction metrics;
- model fits;
- process states;
- empirical promotion metrics.

Therefore the redesign prevents a known technical support failure without selecting taxa for favorable ecological outcomes.

## Scientific role

A successful v3 freeze would not itself validate SDMR empirically. It would only create the first empirical cohort in which the frozen 46-predictor procedure is technically evaluable by construction.

Only a later, separately frozen EMP-A–EMP-F run may open the sealed answer-check.
