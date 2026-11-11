# Product A real positive controls: resolved outcomes and numerical diagnosis

Status: **both frozen v1 empirical lanes completed; both NOT SUPPORTED**.
This is an audit of consumed results, not a new scientific run and not a rescue.
The earlier `65/70` controlled-truth result and v2.8.4 endpoint remain unchanged.

## Actual empirical results

The historical rule requires all three M scores to be available, expected-process
mean score > 0, and at least two positive M scores. Each separate four-taxon lane
requires at least three recovered taxa and at least one recovery in both process
groups. Missing M evidence cannot be dropped. Literature labels are positive
controls, not complete generating-process truth or negative labels.

| Lane | Species | External positive process | Mean across all 3 M | Positive finite M | Missing M | Recovered |
|---|---|---|---:|---:|---:|---|
| plant | Quercus robur | water | -0.276692 | 1 | 0 | no |
| plant | Silene ciliata | water | -0.000704 | 2 | 0 | no |
| plant | Plantago alpina | temperature | 0.366303 | 3 | 0 | yes |
| plant | Silene acaulis | temperature | 0.453130 | 3 | 0 | yes |
| nonplant | Bombus terrestris | temperature | unavailable | 2 | 1 | no |
| nonplant | Ochotona princeps | temperature | 0.793852 | 3 | 0 | yes |
| nonplant | Plethodon cinereus | water | unavailable | 0 | 1 | no |
| nonplant | Cepaea nemoralis | water | unavailable | 2 | 1 | no |

Plant endpoint: **2/4 recovered; temperature 2, water 0; unavailable 0**.
Nonplant endpoint: **1/4 recovered; temperature 1, water 0; unavailable 3**.
Both fail their original >=3/4 and process-group support rules.
The descriptive combined count is 3/8, not a new pooled primary endpoint.
These are positive-control recovery counts, not accuracy/specificity estimates.
An always-positive rule would recover every positive control; this design alone
cannot establish false-positive control or complete process identification.

## What was actually completed

Plant source: 1,759,683 coordinate-valid focal records, four taxa, all 9,705
snapshot shards, exact disjoint-shard union. Nonplant source: 989,156 focal
records and class-matched footprints for Insecta, Mammalia, Amphibia and
Gastropoda. These are source counts, not independent observations used by SDMs.

All **24/24 taxon x M pipelines** returned technical availability. Only **21/24**
had at least one prediction-adequate candidate. The missing three score cells
are not unfinished downloads: they are empty adequate-model classes.

## Numerical failure diagnosis (post-outcome, no retuning)

### 1. Three nonplant cells fail prediction adequacy before recovery comparison

For Bombus / 150 km, Plethodon / 500 km, and Cepaea / 300 km, **all four**
predeclared candidates fail mean rank >=0.51 and mean-minus-SEM >=0.50.
The fitted candidates are four process-group combinations of the same
C=0.1 degree-1 logistic model. This identifies a bottleneck in the present
candidate/gate combination; it does not prove that nonlinearity alone fixes it.

Bombus and Cepaea have positive expected-process scores in two available M
conditions, but the third is unavailable. They remain not recovered. Do not
replace the all-three-M requirement with an available-case calculation.

### 2. Water fails even where all three M values are available

For Quercus, the best adequate excluded candidate is `neutral_only` in every M.
The water-containing minus water-excluded raw Schoener-D gaps are
**-0.125988, -0.012101, +0.002753**. A working pipeline is not the same as
successful recovery of the literature-backed process.

For Silene ciliata, raw water gaps are **+0.000312, +0.000452, -0.000546**.
Normalized scores are +0.005740, +0.009025, -0.016877, giving mean -0.000704.
Two positive signs do not override the negative mean. No new tolerance,
rounding rule or favorable M subset is introduced.

These observations do not show that water is biologically absent. Whether
precipitation channels represent the external experiment's water limitation,
whether geographic/life-stage scales align, and whether correlated retained
channels substitute are separate, unresolved explanations.

### 3. Full taxon x M coverage did not imply full requested fold coverage

Plant tables contain **140/144 nominal fold rows**. All four Quercus / 150-km
candidates have two evaluated folds rather than the requested three. Nonplant
tables contain 144/144. The historical summary accepted the available folds;
the original endpoint is retained, with this limitation explicitly exposed.
A successor needs a label-blind fold-support check and a declared handling rule,
not an after-the-fact relaxation.

### 4. Numerical score 1 is not necessarily a measured complete ecological loss

Four nonplant expected-process cells use boundary codes because either the
containing or excluded adequate subset is empty. These +/-1 codes are retained
for exact reproduction but separately marked in the audit table. Only **17/24**
expected-process cells have a two-sided recovery comparison (12 plant + 5
nonplant). A normalized score of 1 can also arise from a small raw difference
when only two adequate candidates remain; raw gaps and statuses must accompany it.

## Information boundary found in the implemented endpoint

`EmpiricalNichePerturbation.from_preassigned_outer_roles` separates model-pool
`presence/background` from `sealed_presence/sealed_background`.
`real_positive_control._candidate_fold_metrics` evaluates **model-pool inner CV**,
and `run_endpoint` aggregates those scores before reading the external labels.
There is no outer-sealed performance-evaluation call in this v1 endpoint.

Therefore this result is **inner spatial-CV process scores checked against
independent literature-backed positive controls**, not a demonstrated outer
spatial-transfer result. Outer feature values were already materialized by the
pipeline, so they should not be described as physically unread; the claim here
is that they were not used in these score calculations. This audit reads only
saved result tables and never opens raw feature tables or evaluates outer scores.
The external labels have now been consumed and cannot be reused as fresh truth
for a retuned successor.

## Reproduction and provenance

Audited sources (no run chosen by favorable recovery):

- plant: run `34028927021`, artifact `9989319865`, archive SHA-256
  `833324aedad4a49875d7d433e69530bf4792ac1ce8cb26e472607dd34409ed20`;
- nonplant: run `34030629917`, artifact `9989754054`, archive SHA-256
  `1e36b9dca17e09265bd35f08cfce4fba202eb3ac70478728ee845b7db8fe7e0d`.

The later plant run `34030629859`, artifact `9989659303`, SHA-256
`8103e50b0e81ff5cf9a11c8d0145a4e8adb40b9e996f9d9cf07e820684034229`
has the same formal decision and categorical outputs. It is repeated execution,
not independent biological replication. Raw fold rank maximum absolute difference
is 2.0756922e-6 and normalized process score difference is 1.3115836e-6.
Consequently real-data bitwise identity is **not** claimed. This does not alter
v2.7.2's separately scoped deterministic-reproduction result.

`scripts/audit_real_positive_control_results.py` independently recomputes the
96 candidate summaries from 284 stored fold rows, all 48 process x M scores,
eight taxon outcomes and both decisions. It verifies archive digests, keys,
labels, denominators, numeric scores and categorical statuses. Scientific
non-support is a successful audit, not a Python exception.

```bash
python scripts/audit_real_positive_control_results.py \
  --plant-zip sdmr_plant_positive_control_9989319865.zip \
  --nonplant-zip sdmr_nonplant_positive_control_9989754054.zip \
  --output-dir audit_results
python -m pytest -q tests/test_real_positive_control_result_audit.py
```

Local audit: PASS for both archives. Audit safeguard tests: **10 passed**.
No SDM refit, additional taxon, new score threshold, or new scientific endpoint
was executed during this audit. Publication of this reporting-only commit uses
`[skip ci]` to avoid automatically rerunning consumed, expensive empirical PR
workflows; no new-head Actions success is claimed.

## Next active scientific goal

**Develop an empirical successor addressing adequate-alternative availability
and water-process recovery; do not declare Product A empirically validated.**

The next development comparison should separate candidate-family adequacy from
process-representation adequacy, on development data only. Keep raw ecological
effect size, availability, and evidence for each side separate. Complete folds
and explicit outer-transfer evaluation must be planned before outcome. Any
method/representation/threshold changes learned from these eight controls are
post-outcome development and require a new independently frozen biological
validation set. The current four-plus-four denominator, labels, models and
terminal non-support remain in the permanent record.

Do not increase taxonomic scope simply to search for a favorable result. No
improved empirical recovery fraction is available yet. The present contribution
is actual result recovery plus an executable, quantified diagnosis of why the
current real-data method does not meet its own validation target.
