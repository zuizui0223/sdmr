# Alignment transport v15 — development plan

## Current obstruction

The frozen v9 denominator contains 13 shared-candidate cells. Authoritative v14 matched-null diagnosis classified them as 4 shrinkage-reproduced, 7 conditioning-alignment-required, and 2 mixed, with denominator drift 0.

v11-v12 already showed that this alignment cannot be interpreted as a stable transportable P<-Q environmental carrier. v13 explained only 3/13 cells by functional compensation. Therefore the next identifiable question is whether the *intervention effect* of the P<-Q alignment transports across background environments.

## Estimand

For each v14 `conditioning_alignment_required` or `mixed` cell, hold the v8 intervention and all v5 evidence thresholds fixed. Refit the conditional P<-Q map using a single background source environment that is disjoint from the evaluation environment, then apply that map in another held-out environment.

The object of interest is not prediction R2 for P. It is whether the transported intervention reproduces the same transition from v5 contributory to v8 non-contributory under the frozen four-metric evidence classifier.

## Source-target construction

- Source environments are background spatial blocks only.
- Evaluation environments are different held-out blocks.
- Source/target pairing uses no occurrence outcome, suitability score, generating-process truth, or v8 status.
- At least 10 complete source-background rows are required to fit the conditional map.
- At least 3 evaluable source-target pairs are required for a cell-level decision.

## Frozen cell-level classification

- `transported`: all evaluable source-target pairs reproduce the v8 non-contributory transition.
- `local_alignment_only`: none reproduce it.
- `heterogeneous`: some but not all reproduce it.
- `insufficient`: fewer than 3 evaluable source-target pairs.

No new biological or statistical threshold is introduced. The existing v5 adequacy and four-metric interval-evidence rules remain authoritative.

## Interpretation

A `transported` result would support a stable context-dependent alignment effect even though direct P<-Q reconstruction fails out of sample. `local_alignment_only` would identify the v8 shared-candidate transition as environment-local manifold regularization rather than a transportable process relation. `heterogeneous` would imply effect modification by environmental context and retain partial identification.

This stage is development-only and uses only consumed seeds 15001–15010. Fresh known-truth and empirical validation remain unauthorized.
