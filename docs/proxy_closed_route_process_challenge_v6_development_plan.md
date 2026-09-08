# Proxy-closed matched-route process challenge v6 — development plan

## Status

**Post-outcome development only. Product A is not reopened and the eight real positive controls are consumed development evidence, not fresh validation.**

The goal is no longer to stop at `empirical_confirmation_not_supported`. The failed controls are used to identify *why* the v1 process counterfactual failed, convert those causes into explicit method changes, and then freeze a successor before any new biological validation labels are opened.

## What the failed controls diagnosed

### 1. Declared variable exclusion was not process-information exclusion

The v1 real-positive-control registry represented temperature by four temperature rasters, water by four precipitation rasters and a supposedly neutral channel by radiation plus wind. A candidate counted as `water`-excluded whenever the four precipitation predictors were absent.

That is weaker than the process-information-closure principle already implemented elsewhere in SDMR. Retained predictors can remain correlated with the excluded process and therefore preserve enough of its environmental information to act as a substitute.

Development diagnostics on the consumed raw feature caches confirmed this problem. For *Silene ciliata*, neutral predictors alone reconstruct the four frozen water predictors with mean cross-validated R2 of about 0.25–0.42 across M, with maximum rank correlations about 0.67–0.86. Temperature plus neutral predictors reconstruct still more water information. Quercus also retains reconstructable water information through the nominally excluded channels.

The failure is therefore not equivalent to "water is not identifiable from occurrence data." The implemented knockout often did not actually remove water information.

### 2. Water was represented as precipitation-only although the controls concern drought/water balance

The v1 water registry contains `bio12`, `bio14`, `bio17` and `gsp`. Yet the *Silene ciliata* external control is explicitly a summer-drought mortality result, and the wider SDMR CHELSA registry already contains `vpd`, `pet` and `cmi`.

The successor water closure must therefore be reviewed prospectively as a many-to-many information closure spanning at least:

- precipitation amount / dry-season precipitation;
- atmospheric dryness (`vpd`);
- potential evapotranspiration (`pet`);
- climatic moisture balance (`cmi`).

`pet` may legitimately belong to more than one process closure. That is not a conflict; it is the reason the registry is many-to-many.

### 3. More flexible response curves alone did not solve the water failures

As a fixed diagnostic, replacing the frozen degree-1 logistic response by degree 2 (squares and interactions) did not restore the raw v1 water counterfactual. Quercus remained negative across all three M outer comparisons and *Silene ciliata* remained approximately zero.

Thus v6 does not treat nonlinear model flexibility as the primary rescue. Degree 1/2 can remain predeclared robustness contexts, but the main change is the process intervention.

### 4. The outer answer-check split itself failed for one taxon

For *Plantago alpina*, the frozen outer role contains only two occurrence rows, of which only **one** has a complete ten-variable environmental audit vector. Schoener-D therefore cannot be evaluated on the outer answer-check side.

This is not a negative temperature result. It is an outer-coverage failure that the original taxon-level split contract did not prevent.

Future empirical contracts therefore require a pre-feature-extraction outer coverage gate. The current development default is at least 10 complete sealed occurrences and at least two sealed spatial blocks per taxon; failure returns `unavailable`, never negative ecological evidence. The consumed Plantago split is not retroactively repaired for validation.

### 5. v5 summary counters compress away route information

The v5 audit showed that 56 unresolved process cells collapse into only nine six-counter signatures and that several signatures contain both true and false cells. Threshold tweaking on those counters therefore cannot recover all true abstentions without also promoting false ones.

v6 keeps raw matched-route evidence as the inference object. Summary counters remain reporting fields, not the only state supplied to the decision rule.

## v6 intervention

For a process `p` and one baseline ModelSpec:

1. fit the ordinary baseline route;
2. remove every declared direct/derived/proxy/composite representation of `p`;
3. on **training background environments only**, fit a fixed degree-2 ridge map from the process closure to every retained ecological predictor;
4. replace each retained predictor by its residual from that map;
5. refit the **same ModelSpec** on those purged retained predictors;
6. compare baseline versus purged knockout on the same folds/routes;
7. preserve v5 `noninferior / inferior / indeterminate / incomplete` interval states;
8. if any viable purged route is indeterminate or incomplete, process status is `unresolved` rather than positive.

The purge sees no occurrence class, external label, process truth, selected-model coefficient or variable importance. It is an outcome-blind environmental information-erasure operator. It is also **not causal residualization**: it may remove shared environmental structure too aggressively, which is exactly why a new known-truth denominator is required before promotion.

## Consumed-control outer diagnostic

The pinned original plant artifact `9989319865` and nonplant artifact `9989754054` preserve model-pool and outer-sealed occurrence/background feature tables. `scripts/diagnose_proxy_closed_positive_controls_v6.py` computes both temperature and water challenges for every taxon before opening the expected-process labels.

The process-specific matched routes are:

- temperature: `temperature_only -> purged neutral` and `temperature_water -> purged (water + neutral)`;
- water: `water_only -> purged neutral` and `temperature_water -> purged (temperature + neutral)`.

No across-candidate span normalization or +/-1 boundary code is used in this diagnostic. The reporting quantity is the raw outer Schoener-D loss `D_baseline - D_purged` in the original frozen ten-variable audit space.

Current deterministic development readout from those consumed feature caches:

| lane | taxon | expected process | mean outer D loss | positive M | outer status |
|---|---|---|---:|---:|---|
| plant | *Quercus robur* | water | 0.0367 | 3/3 | scorable |
| plant | *Silene ciliata* | water | 0.0019 | 2/3 | scorable, only 8 complete sealed occurrences |
| plant | *Plantago alpina* | temperature | unavailable | — | only 1 complete sealed occurrence |
| plant | *Silene acaulis* | temperature | 0.0364 | 3/3 | scorable |
| nonplant | *Bombus terrestris* | temperature | 0.0254 | 3/3 | scorable |
| nonplant | *Ochotona princeps* | temperature | 0.0150 | 3/3 | scorable, only 8 complete sealed occurrences |
| nonplant | *Plethodon cinereus* | water | 0.0085 | 2/3 | scorable |
| nonplant | *Cepaea nemoralis* | water | 0.0331 | 3/3 | scorable |

Seven of eight consumed controls therefore point in the expected direction under the descriptive old sign/count criterion; the eighth is outer-unavailable rather than negative. **This is development evidence only.** In particular, the planned future outer floor of 10 complete sealed occurrences would also classify the present *Silene ciliata* and *Ochotona princeps* outer readouts as too small for a future primary endpoint. No threshold or minimum count was chosen to maximize the 7/8 number.

The strongest single mechanistic diagnostic is Quercus: the raw water-exclusion outer gap was approximately `+0.0046, -0.0154, -0.0084` across the three M values; after purging water information from the retained route it became approximately `+0.0784, +0.0256, +0.0456`. This directly links the old failure to residual water information in the supposed water-free alternatives.

## What v6 does **not** claim yet

The current evidence does not establish:

- prospective empirical recovery rate;
- specificity on biological data (the controls are positive-only);
- causal or physiological process necessity;
- that degree-2 ridge purging is the final optimal operator;
- that all real-world proxies are closed;
- that the seven descriptive recoveries are independent validation successes.

## Promotion sequence

1. **Implementation / consumed diagnosis:** freeze the v6 code path and reproduce the eight consumed-control diagnosis without using labels in fitting.
2. **Fresh known truth:** use new unused simulation seeds after the v6 source and contract are frozen. Measure true-process recall, false-process challenge and unresolved rates. If proxy purging inflates false challenges, v6 fails.
3. **Freeze empirical registry and outer coverage contract:** include drought/water-balance representations prospectively; freeze minimum sealed coverage before raster extraction.
4. **Fresh biological controls:** use a new literature-backed taxon panel never used in v1/v6 development. Do not add/drop taxa after seeing SDM results and do not reuse the eight consumed labels as fresh truth.
5. **Only then update the manuscript claim:** if the prospective successor succeeds, the empirical statement changes from a boundary result to a supported process-identification result. If it fails, retain the failure and its newly localized cause.
