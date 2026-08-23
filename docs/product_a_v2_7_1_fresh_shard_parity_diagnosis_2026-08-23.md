# Product-A v2.7.1 fresh shard parity diagnosis — 2026-08-23

## Current failure boundary

Fresh confirmation run `32552745281` successfully passed its source gate, raw-source verification and all six sealed-before-M materialization parts, but the monolithic model-pool matrix hit terminal job cancellations before pretruth. No recovered pretruth, final-fit, sealed-audit or scientific-decision artifact was produced.

A sealed-blind three-M parity experiment (`32574696718`) then recomputed the completed reference worker `taxon10 / seed 2026082201 / sealed 0.30` as three independent M shards. All three shard jobs succeeded and the reconstructed worker retained byte-identical predictor-coverage, evidence-balanced partition, audit-space and row-to-fold ledgers. The comparison failed only when floating model-output tables were required to be bitwise identical.

The first reported mismatch was `presence_rank`; 28.125% of that column's 96 rows differed, with the values remaining very close rather than showing a structural or categorical change.

## Diagnosis

The frozen Product-A fitting helper uses scikit-learn `LogisticRegression` with `solver="liblinear"` and does not explicitly set `random_state`. The already-frozen primary worker therefore does not define bitwise reproducibility of solver-dependent floating outputs across independent Python processes. Splitting the three M evaluations into separate jobs changes that process boundary even though the data, fold assignment, audit space, candidate library and scientific rules are unchanged.

Changing the fitted model code now to force a random seed would change the already-frozen fresh-confirmation implementation after model-pool evidence has been generated. That is not an acceptable parity repair.

## Predeclared repair

`configs/product_a_v2_7_1_fresh_sharded_parity_v2_contract.json` therefore changes only the **transport verification rule**, not Product-A science:

1. worker contract identity remains exact;
2. predictor, partition and audit ledgers remain byte-identical by SHA-256;
3. dataframe shape and column order remain exact;
4. integer, boolean and nonnumeric values remain exact;
5. non-finite locations remain exact;
6. only floating columns may differ within the frozen envelope `rtol=5e-4`, `atol=5e-4`;
7. any floating value outside that envelope fails closed;
8. the envelope may not be revised after the next parity outcome is observed.

The envelope is fixed at five times the frozen liblinear solver stopping tolerance (`1e-4`). It is a transport-equivalence tolerance, not a new ecological, predictive, process or promotion threshold.

## Scientific invariants

This repair does not change the fresh taxon panel, split seeds, sealed fractions, M grid, evidence-balanced partition, audit-space rule, procedure library, model specifications, prediction-adequacy rule, process domains, knockout semantics, pretruth selection, sealed metrics or six-part decision rule.

No sealed environmental value is opened by the parity workflow. Passing this parity check still does not promote Product A and does not unblock Product B.
