# HF453 100 m spatial validation v2: original-axis correction, pre-execution freeze

**Version:** 2026-11-20, **before corrected-v2 biological scoring**. This is a source-defined technical successor to a *failed source-geometry admission*, not a new ecological replication, not a confirmatory study, and not a retuning after a weak or adverse model result.

## Earlier attempts are immutable

- First one-shot activation, Actions [#44749425699](https://github.com/zuizui0223/sdmr/actions/runs/44749425699), failed GitHub YAML syntax and launched **zero jobs**.
- Runtime-only first scientific attempt, Actions [#44749714741](https://github.com/zuizui0223/sdmr/actions/runs/44749714741), reached original source opportunity only, yielding `original_source_geometry_coverage_unavailable` for **14,519/21,769 = 66.69576%** of the fixed 2019 species/DBH-complete and known-status stems, below the prespecified ≥80% source threshold. **Zero new CV model fits**, no geometric CP information claim. [First STOP receipt](../evidence/hf453_spatial100_first_geometry_source_hold_v1.json).
- Original source-only XY audit, Actions [#44750670871](https://github.com/zuizui0223/sdmr/actions/runs/44750670871), **read no biological status, CP, species, DBH or fitted models**. Its fixed 30,808 source stems had original 2019 `gx` range **0.13165–699.94897 m**, `gy` range **0.01786–499.978 m**, no missing coordinates, **35** original parent-centroid cells under x700/y500, and all **27,688** parent IDs in that frame. The old x500/y700 source assumption was reversed. [Source-only axis receipt](../evidence/hf253_xy_axis_source_diagnosis_first_v1.json).

## Authorized differences from first scientific code v1

**Only the source coordinate orientation changes.** Preserve:
- Complete original HF253 SHA-256 `bb48448b8a2cd920fcac7df21a352a0c70174652f11d76423b03770a565ce2e7`, original HF453 SHA-256 `0b5fd6072fc5a5b5a315dca4609e3023a85430e5e24a96a2cfa3307a0d431e74`; reject source/version drift before reading coordinates or Y.
- Same 2019 original `stem.tag → tree.id` parent registry, no new matching keys, the **21,769** fixed prior-species/DBH-complete known-next-status stem events, original baseline and added CP representations, same parent-equal scoring, L2 logistic C=1 maxiter1000.
- Same **100×100 m** source grid (origin 0,0), same GroupKFold K=5, same complete-parent-geometry rule, same ≥10 source-block and ≥80% retained-stem eligibility gate. No alternative block widths, origins, taxa, source cohorts or learners.
- Original `gx` now constrained to **0–700 m** and `gy` to **0–500 m**, because this is what the independently opened original coordinate source supports; edge points x=700 and y=500 are included in final x-bin6 and y-bin4. Source frame comprises **7×5 = 35** geometrically possible 100m blocks.
- Exact source-only axis run #44750670871 and the earlier source STOP #44749714741 must be part of v2's code/config/lock receipt.

## Fixed questions and decisions

The result is **two model-pair scores on exactly the same original geographically eligible stems**: (1) parent `tree.id` GroupKFold5 and (2) source 100m spatial-block GroupKFold5. The main metric is equal-parent heldout log loss, compared baseline species/2019 diameter/2021 health **minus** baseline+2021 CP. Brier score is secondary. The two GroupKFold partitions may score the same stems but need not assign folds identically.

Original source geography is evaluated **before** any biological response/refitting. If complete-parent coordinates, source census IDs, 35 original 100m cells, ≥10 eligible blocks, ≥80% stem coverage, no shared parent train/test, or fixed learner convergence fail, report the appropriate STOP/UNAVAILABLE, not a selective lower threshold or geometric retry.

**Valid possible conclusions:** gain positive in both (conditional geometric stability), gain positive only under parent holdout (spatial sensitivity), no gain in either (weak on the common cohort), or unavailable source/learner. All are **post-2022-outcome exploratory**, one-forest algorithmic prediction, never a verified causal light/competition effect, independent forest transfer, Product A promotion or Product B unblocking. Do not pool this with original prospective synthetic M5 or Structural results.

## Reproducibility

- Frozen [v2 config](../configs/hf453_spatial_block_priorcov_axis_corrected_v2.json), [new v2 implementation](../scripts/hf453_priorcov_spatial100_axis_corrected_v2.py) and [synthetic contract tests](../tests/test_hf453_priorcov_spatial100_axis_corrected_v2.py).
- A dedicated source-free CI must pass before separate one-shot activation. Exact Git blob hashes of config/script/tests are checked in the locked workflow, with JSON-only output and hard fail on missing artifact.
- The v1 scientific source STOP is preserved and **never** retroactively reclassified as a biological test.
