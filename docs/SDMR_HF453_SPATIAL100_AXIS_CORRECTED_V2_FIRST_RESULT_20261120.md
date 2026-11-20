# HF453 original-axis-corrected spatial100 vs parent heldout — first complete v2 result (2026-11-20)

**Status: complete post-outcome exploratory spatial sensitivity, with mixed predictive score evidence. Not a new independent forest, not a causal canopy-light or competition result, not promotion of original SDMR methods.**

## Source and immutable execution

- Harvard Forest HF253 2019 v6 source SHA-256 `bb48448b8a2cd920fcac7df21a352a0c70174652f11d76423b03770a565ce2e7`; HF453 2021–2024 v1 SHA-256 `0b5fd6072fc5a5b5a315dca4609e3023a85430e5e24a96a2cfa3307a0d431e74`. No other provider/source version, predictor universe or study opened.
- The earlier x500/y700 spatial geometry [source STOP #44749714741](https://github.com/zuizui0223/sdmr/actions/runs/44749714741) remained immutable and fitted **zero** new CV models. Separate [source-only XY diagnosis #44750670871](https://github.com/zuizui0223/sdmr/actions/runs/44750670871) found full actual original x=0–700m, y=0–500m source support, 30,808/30,808 stem tags, 27,688/27,688 parent IDs and all 35 potential 100m source blocks; no 2022 biological outcomes read.
- [Scientifically frozen v2 axis-corrected source protocol](SDMR_HF453_SPATIAL100_AXIS_CORRECTED_V2_PREFREEZE.md) changes only the erroneous interpretation of original plot x/y extents. **Same original 100m block width, model pair, C=1, same 2019 species/DBH, same 2021 A/AU and CP, same 2021→2022 known-status response, same parent weighting and five GroupKFold splits.**
- Authoritative first complete corrected run: [GitHub Actions #44752128595](https://github.com/zuizui0223/sdmr/actions/runs/44752128595), locked source commit `09a622c8cf470ccb8ef7fafcf66fc0244a9e8753`, **SUCCESS**. Original result artifact **#14636880470**, ZIP SHA-256 `599e98a6fc590da964dddce6e95372d4b6921251614f1c392b52963c2c121213`, inner result JSON SHA-256 `440f35179a90d50a8fc7a5b1014d6e349ed71a62029b9d518334fe39730de303`; preflight SHA-256 `ddbf3985b3a4b32774ca5d24bee9867b9caa5aa36d156771000371061352c2a9`. [Frozen machine-readable receipt](../evidence/hf453_spatial100_axis_corrected_v2_first_result.json).
- No stem-level original source CSV, individual coordinates, original tree or stem IDs, biological row outcomes, OOF predicted probabilities, species-specific coefficients or raw model data were exported. Saved evidence is a nonidentifying aggregate receipt.

## Original physically grouped validation denominator

**All 30,808 original stem tags** and all **27,688** original parent IDs have valid original HF253 source positions under x700/y500, with 35 original parent-centroid source cells. No source-coordinate exclusion was necessary.

The prior-covariate-complete, CP-known and next-year binary-status-known cohort is **exactly the same 21,769 stem observations from 19,872 original parent `tree.id` candidates**, including **454** recorded `DC/DS` outcomes, as in the previously opened [first parent CV](SDMR_HF453_PRIOR_SPECIES_SIZE_FIRST_RESULT_20261120.md). That is not 21,769 independent trees or geographically independent sampling units. Every parent stays entirely in one side of each training/test fold for both layouts; **zero** source parent IDs overlap train and test.

The spatial grouping uses original **100 m × 100 m** HF253 x/y cells, assigned by the mean source position of all originally matched stems under each parent. The 35 cells are distributed across 5 heldout folds of **7 cells per fold**. Each source stem was held out exactly once for each comparison. The spatial folds are spatially separated by source grid identity but adjacent cells, spatial dependence and one-forest effects remain possible.

## Primary fixed loss comparison, same original cohort

| Grouped validation | Baseline log loss | Baseline + CP log loss | Improvement, baseline − +CP |
| --- | ---: | ---: | ---: |
| Parent `tree.id` GroupKFold (5) | **0.0892572113** | **0.0885619743** | **+0.0006952370** |
| Original 100m spatial-block GroupKFold (5) | **0.0906779810** | **0.0901307564** | **+0.0005472246** |

Both **mean equal-parent negative log-loss increments are positive, but very small**. Positive means CP adds a little heldout probability information to this fixed learner beyond species code, 2019 stem diameter and 2021 health; the lower spatial delta implies sensitivity to validation geometry. The spatial result is *not* an independent dataset; it is the same source records partitioned into a coarser geographic holdout.

## Critical scoring-rule disagreement

| Grouped validation | Baseline Brier score | Baseline + CP Brier score | Improvement, baseline − +CP |
| --- | ---: | ---: | ---: |
| Parent groups | 0.0197102229 | 0.0197032788 | +0.0000069440 |
| **Spatial 100m groups** | **0.0200428677** | **0.0200696558** | **−0.0000267881** |

The spatial **Brier score worsens when CP is added**, despite improvement in log loss. These are different proper scoring rules with different sensitivity to predictions; such disagreement is legitimate, especially for rare events and a weak additive contribution. Accordingly **do not** write “CP consistently improves independent prediction,” “CP improves all SDM evaluation metrics,” or “spatial validation proves an ecological light process.” The supported narrower statement is: **a tiny conditional CP increment exists under log loss in both this parent and one source-defined 100m spatial split, but there is no consistent gain across scoring rules.**

All fold-level first-run counts are in the original immutable artifact. No p-value or statistical confidence interval was calculated, and outcome/forest-space generalization was not established.

## Relation to the original HF453 biological association

The original first 2021→2022 HF453 per-stem recorded death association (understory CP1/2 **323/10,452** versus more-exposed CP3/4/5 **138/11,390**, with very few unknown next-year states) is **not changed**. A subsequent **post-outcome exploratory** species × fixed 2019 diameter × 2021 health stratification yielded a negative signed missingness partial-identification interval on its restricted shared-support cohort, but this remains noncausal. The v2 spatial prediction check does not tell whether stem size, species composition, hidden site quality, disease, historical mortality selection, local competition or measurement process generates that association.

The source frame is **one 35-ha Harvard forest**, not multiple independent forest replicates. Spatial blocking and parent grouping are safeguards for specific kinds of leakage, not interventions or ecological process identification.

## Consequence for SDMR methods

Separate three dimensions:
1. **Incremental out-of-block predictive information:** CP has tiny log-loss gain for this fixed source, conditional on the chosen model and available covariates.
2. **Score/estimand sensitivity:** the sign of *incremental improvement* depends on whether log loss or Brier is the endpoint; report both.
3. **Real-world process identification:** source hash, original parent IDs and spatial opportunity auditing prevent some misinterpretations but do not identify causal ecological mechanisms or independent geographic transfer.

The correct next methods paper stage is an independently sourced forest with prospectively untouched outcome and a source-verified observation/effort frame, if aiming for generality. Do not reopen consumed HF453, tune 50/100/200m block widths for favorable outcome, add more predictors by searching the same Y, or relabel this as a second replication.

Original Product A `not_promoted`, Product B blocked, original M5 71/80 and Structural prospective synthetic 30/30 unchanged. Keep the exploration [PR #287](https://github.com/zuizui0223/sdmr/pull/287) **Draft**, stacked on the separate methods Draft [PR #286](https://github.com/zuizui0223/sdmr/pull/286).
