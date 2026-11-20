# HF453 prior species, stem diameter and health controls — first post-outcome result (2026-11-20)

**Disposition:** exploratory positive **predictive information**, extremely small in magnitude, and negative fixed-overlap **associational** death-status difference. This is one Harvard Forest, **not** ecological causal process identification or independent generalization, and is separate from the already opened original field-status result.

## Source and execution receipts

- The original 2019 Harvard Forest HF253 (v6) source is SHA-256 \`bb48448b8a2cd920fcac7df21a352a0c70174652f11d76423b03770a565ce2e7\` (12,687,409 bytes); its original provider-published MD5 was **not** independently verified.
- The 2021–2024 Harvard Forest HF453 (v1) original is SHA-256 \`0b5fd6072fc5a5b5a315dca4609e3023a85430e5e24a96a2cfa3307a0d431e74\` (5,524,386 bytes), publisher MD5 \`c6be7aa99e31ded2041a0aaea07c0205\`.
- Fixed [pre-result scientific design](SDMR_HF453_PRIOR_SPECIES_SIZE_POSTOUTCOME_V1.md), exact source-locked first [run #44747246917](https://github.com/zuizui0223/sdmr/actions/runs/44747246917) at \`c487b2538084702bed18d8cad8992c24fc0ae0ac\`, **SUCCESS** after source-blind synthetic tests.
- Result artifact **#14633317466**, ZIP SHA-256 \`63e4e32ec18e15396ceee5981e660807c5821bea55f62be85226b41e19c3798b\`. Original JSON SHA-256 \`cd1b4b42b99bd6dcb380718199a35fa22c3cbab8bb8d3e047c02308647f770e1\`; preflight JSON SHA-256 \`1120c75e4949f3dd7d4d3f758dbe3f49ab3f057dfd87f3d0d40d6b5eee988c61\`.
- [Frozen machine-checkable aggregate checkpoint](../evidence/hf453_postoutcome_prior_species_size_first_result_v1.json). No original \`StemTag\`, \`tree.id\`, species-level response record, source file, individual OOF prediction or raw 2019/2022 tree response was archived. This is **not** an independent new forest sample or a reclassification of previous results.

## Original denominator and covariate admission

- Preserved the original 2021 observed-alive source-stem denominator **21,846**, consisting of **461** recorded next-year \`DC/DS\` and **5** next-year unknown \`DN\` status. Four baseline stem observations had no measured canopy CP; the CP-assessed denominator was **21,842**.
- Original HF253 2019 \`sp\` was available for **all CP-assessed baseline-alive stems**. Original 2019 \`dbh\` was missing/unusable for **68/21,842** CP-assessed stems (~0.31%). Thus **21,774** retained complete prior species/DBH covariates and measured CP; this preserves five next-year unknown source statuses.
- On this fixed complete-covariate subset, **21,769** original stem transitions had known binary 2022 status (454 recorded \`DC/DS\`, 21,315 recorded \`A/AU\`), grouped under **19,872** distinct original parent \`tree.id\`. **30** distinct original 2019 species mnemonic codes appeared among the covariate-complete stems.
- HF253 2019 includes 61,985 source rows with missing/unusable DBH **across its entire 123,218-row forest-wide source**, largely outside this exact 2021 HF453 ≥10cm-tagged and alive/CP-assessed cohort. That full-file missing count is **not** the covariate exclusion rate of the analysis. It is crucial to keep both denominators separate.

## Primary: fixed parent-heldout incremental CP prediction

Five exact original-parent GroupKFold splits ensured **zero parent IDs in both training and test**. Training and scoring gave every parent equal total weight, not every stem independent weight.

| Fixed response model | Heldout log loss (lower better) | Heldout Brier (lower better) |
| --- | ---: | ---: |
| 2019 species mnemonic + log1p(2019 DBH cm) + 2021 prior health A/AU | 0.0892572113 | 0.0197102229 |
| Same baseline **+ 2021 prior canopy CP1/2 vs CP3/4/5** | **0.0885619743** | **0.0197032788** |
| Baseline minus +CP | **+0.0006952370** | **+0.000006944** |

**Result:** CP retains a very small positive predictive increment for previously untrained **parent tree IDs within this one forest**, conditional on the declared historical predictors. This is not a realized external biological transfer, causal light/competition/health inference, a quantified uncertainty interval or a guarantee for other learners or biomes. The original binary status had already been inspected before the predictor-comparator design, so the positive delta is explicitly **post-outcome exploratory**, not a prospective independent scientific test.

## Secondary: exact species × original size-band × start-health common support

Fixed prior DBH bands \((0,10)\), \([10,20)\), \([20,40)\), \([40,\infty)\) cm and the literal species mnemonic and baseline \`A/AU\` define **114** original covariate strata.

| Frozen CP overlap rule | Strata with both CP groups | Original complete-covariate stems retained | Excluded complete-covariate stems | Sharp unknown-next-status standardized difference (more exposed minus understory) |
| --- | ---: | ---: | ---: | --- |
| **≥10 stems per CP group per stratum** (primary) | 30/114 | **19,063/21,774** | 2,711 | **−1.789087 to −1.767032 percentage points** |
| ≥1 stem per CP group per stratum (sensitivity) | 69/114 | **21,300/21,774** | 474 | **−1.586203 to −1.566464 percentage points** |

Both identification intervals exclude zero. They allow **arbitrary binary reassignment of missing next-year status among included stems**, but are **not confidence intervals**, do not measure sampling error, and exclude original strata that lack fixed common CP support. They remain associations in partly selected source cohorts, not causal estimates of canopy/light effects. Historical species labels or a coarse DBH band and an A/AU proxy do not measure soil quality, competition pressure, disease history, size-specific survival processes, forest spatial autocorrelation or latent measurement selection.

## Methodological interpretation for SDMR

This source illustrates **three distinct scientific barriers** rather than providing a universal process answer:

1. **Information:** a measured environmental or structural variable may contribute small genuinely heldout predictive information even after three important prior measured proxies. Here the extra heldout log-loss gain is \(0.000695\), not a strong effect.
2. **Observability:** the association's sign survives the *five recorded unknown next-year states*, but this does not prove no unseen selection/measurement bias outside the published cohort. The partial-identification bounds are not probability-calibration scores, causal effects or sampling confidence intervals.
3. **Physical grain:** original stem tags are nested within original parent tree IDs. Parent-GroupKFold is preferable to individual-stem random holdout for estimating transport to unseen parent IDs, yet geographic neighbors still share forest conditions.

A new within-forest **100m spatial-block holdout**, frozen only after inspecting the above original gain, is proposed as a separate **developmental sensitivity** in [the exact geometry protocol](SDMR_HF453_SPATIAL100_POSTOUTCOME_V1.md). Its result cannot retrospectively convert this first positive exploratory result into confirmatory independent inference.

**Publication ceiling:** one-forest method/application vignette, not broad species SDM advantage, causal competition process or a replicated forest mechanism. Product-A remains \`not_promoted\`, Product B blocked; original M5 71/80 and Structural 30/30 synthetic results unchanged. [PR #287](https://github.com/zuizui0223/sdmr/pull/287) remains Draft and stacked on the distinct methods PR #286.
