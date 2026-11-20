# HF453: can prior canopy information transport across 100m blocks *inside one forest*?

**Second post-outcome developmental sensitivity, fixed 2026-11-20.** The original 2021→2022 CP-associated field result and first parent-tree-heldout gain \(\Delta\)logloss \(+0.000695237\) were **already seen**. This is **NOT** a prospective confirmatory ecological test. The source and learner remain unchanged; only the heldout geometry is altered under an explicitly fixed new protocol.

## Precise question

Does the very small incremental predictive information associated with 2021 canopy position remain positive when validation removes **geographically separate 100×100 m source plot blocks**, rather than holding out individual parent-tree IDs? This is **within the same 35-ha Harvard Forest**, not a new stand, biome, species sampling frame, forest population or causal light/competition test.

## Original source and fixed geometry (before opening original coordinates in this stage)

- HF253 original 2019 \`hf253-06-stems-2019.csv\`: full-byte SHA-256 \`bb48448b8a2cd920fcac7df21a352a0c70174652f11d76423b03770a565ce2e7\`, **12,687,409 bytes**; original source \`stem.tag\`, \`tree.id\`, \`gx\`, \`gy\` only used for pre-outcome geographic grouping. HF253 official documentation defines \`gx,gy\` in **meters within the 500×700m plot**. The original 2019 file's first computed MD5 is **not publisher verified**.
- HF453 original 2021–2024 source: full-byte SHA-256 \`0b5fd6072fc5a5b5a315dca4609e3023a85430e5e24a96a2cfa3307a0d431e74\`, MD5 \`c6be7aa99e31ded2041a0aaea07c0205\` (publisher-referenced), **5,524,386 bytes**.
- Restore exactly the prior 30,808 2021 \`StemTag\` values and 27,688 original source parent \`tree.id\` candidates **before inspecting any 2019 coordinate or previously opened 2022 outcome**.
- Use the fixed plot origin (0m,0m). \`gx\` must be finite within [0,500]m and \`gy\` finite within [0,700]m; otherwise exclude that **original parent tree ID** from geometric eligibility. Every original stem belonging to a parent must have a valid coordinate, even if the eventual scored stem would be eligible.
- Compute original parent-tree mean position over **all** the original matched 2019 stems (not selected by 2022 status). Its block is \`floor(mean_gx/100),floor(mean_gy/100)\`, with exact x=500 and y=700 included in the last original plot block. This fixed rule produces a maximum of 5×7=35 100m blocks, not tuned for the later CP signal.
- If fewer than 10 distinct geographically eligible blocks or fewer than **80%** of the original known-outcome species/DBH-complete cohort are covered, report **unavailable under fixed spatial design** and stop before model refitting. Report all exclusions, including missing stem coordinates and parents.

## Same cohort and frozen model pair, two split strategies

The 2019 \`sp\` species code, 2019 \`log1p(dbh_cm)\` and 2021 baseline \`AU\` indicator remain the **same baseline model** as original postoutcome run [#44747246917](https://github.com/zuizui0223/sdmr/actions/runs/44747246917). Candidate adds only the original 2021 binary CP1/2 versus CP3/4/5. Same fixed sklearn L2 logistic (\`C=1\`, \`lbfgs\`, max_iter1000, no class weights) and original parent-equal training/scoring weights. Next-year \`DN\` remains unknown and is not imputed to a binary outcome.

Use **exactly the same geographic-eligible stems** for two independent 5-fold layouts:

1. **Original-parent-heldout comparator**: GroupKFold=5 by original 2019 parent \`tree.id\`.
2. **New within-forest spatial heldout**: GroupKFold=5 by the **100m source block assigned to each complete original parent**, never by individual stem.

For each layout, calculate heldout equal-parent mean negative log loss and Brier difference \(\mathrm{loss}_{baseline}-\mathrm{loss}_{+CP}\), with all scored original known-status stems covered once. A negative score means adding CP does not improve that frozen algorithm in that layout. Parent IDs must never appear across train/test partitions in either layout. Spatial cells near each other may still be ecologically correlated; this design is **not** proof of geographic independence.

No other raster, covariate, threshold, regularization parameter or alternate block resolution is tested. The previously reported +0.000695237 cannot be directly compared to a new geometric subset with potentially different original stems; the **paired parent-heldout result on exactly the same geographically eligible subset** is the proper comparator.

## Interpretation rules

- If the CP increment remains positive in both, write only **conditional predictive information stable to one prespecified within-forest blocking geometry**. Still not mechanistic, causal or broadly transferable.
- If positive under parent holdout but zero/negative under spatial blocks, the result indicates **validation-geometry sensitivity**; site structure may explain the apparent CP information, but spatial blocks do not identify a particular causal mechanism.
- If both are weak or negative on the new common subset, prioritize **source availability/estimand shift** rather than claiming spatial blocking automatically destroyed a real biological signal.
- If the field source is incomplete under the frozen spatial eligibility gate, preserve unavailable and count the denominator; do not change grid origin, shift 100m cells, lower coverage thresholds or select species after Y opening.
- Report raw/logical source identity and group counts, no row-level coordinates, raw tree tags, individual predictions, p-values or statistical confidence intervals. Any gain is evaluated **within one original forest** with earlier biological Y already consumed.

## Reproducibility

- [Fixed design](../configs/hf453_spatial_block_priorcov_postoutcome_v1.json)
- [Source SHA and heldout comparison implementation](../scripts/hf453_priorcov_spatial100_postoutcome_v1.py)
- [Synthetic source-only, grouping and mutation tests](../tests/test_hf453_priorcov_spatial100_postoutcome_v1.py)
- One-shot locked source execution after synthetic CI and exact code SHA gates; no opportunistic future reruns seeking positive numbers.
- Original first HF453 [biological result](../docs/SDMR_HF453_FIRST_STATUS_RESULT_20261119.md), source [parent grain](../evidence/hf253_hf453_parent_tree_grain_v1.json), and the [first prior covariate result](../evidence/hf453_postoutcome_prior_species_size_first_result_v1.json) remain immutable.

**Never promote:** Product A remains not promoted; Product B blocked; original M5 71/80 and Structural 30/30 known-truth results unchanged. PR #287 is post-outcome exploratory and stacked on Draft #286.
