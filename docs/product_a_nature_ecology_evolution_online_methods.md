# Online Methods — Product A Nature Ecology & Evolution submission

Status: **submission-production document; counterfactual controlled-truth successor integrated; frozen empirical endpoint unchanged**.

## Study objective and inferential targets

Product A evaluates environmental-process claims from occurrence-only species distribution models (SDMs) without equating predictive success with ecological truth. The final manuscript distinguishes three process-level objects.

1. **Predictive adequacy.** Candidate models must transfer above chance to withheld occurrence evidence before ecological interpretation.
2. **Process membership.** The final counterfactual estimator asks how much attainable held-out ecological niche recovery is lost when every declared representation of one environmental process is removed from the adequate candidate class.
3. **Process necessity.** A separate, stronger falsification certificate asks whether any adequate ecological explanation survives process-information exclusion. `required_by_frozen_evidence_contract` is contract-relative and is not physiological, causal or fundamental-niche necessity.

These objects are not combined into a weighted prediction–ecology super-score.

## Prospective information barriers

Within each empirical focal taxon, admitted occurrence records were processed before tuning and assigned by whole spatial blocks to `model` or `sealed` roles. Sealed rows could not influence predictor/universe selection, regularization, response complexity, stopping, accessible-area/background construction, candidate choice or promotion criteria. Discovery evidence could be used to develop a procedure only when later validation evidence remained unused and was prospectively frozen before opening.

The original Product-A empirical contract used a minimum of 80 admitted occurrences and 50 unique 0.05° cells per species. Accessible-area assumptions were treated as sensitivity conditions rather than optimized by score.

## Occurrence and environmental evidence

The empirical evidence was tied to the GBIF monthly occurrence snapshot dated 1 August 2026, DOI `10.15468/dl.fs3btq`, download key `0020258-260721160103020`, with repository-recorded citation SHA-256 `022a524b59c4c037b28f252c08294e0f22c5eb7b3bce5c52a0a5fc6016f17050`.

The active empirical environmental manifest contained 43 predictors. Three nested universes were predeclared: `bioclim19`, `chelsa_bioclim` and `active_all`. Conventional predictor/model strategies included all variables, iterative VIF filtering and predictive forward selection. Model complexity and regularization were tuned only inside the model pool.

## Accessible-area and background sensitivity

The empirical programme used 150, 300 and 500 km occurrence buffers as a matched accessible-area (`M`) sensitivity set. Each M specification requested up to 2,000 target-group background cells at 0.05° resolution. Target-group Plantae records came from the same GBIF snapshot. The complete focal panel was excluded from the target-group source before splitting to prevent sealed focal records from re-entering through background.

Target-group background is an observation/reference frame, not biological absence or a niche answer key.

## Conventional comparators and ecological recovery metrics

Conventional criteria included AUC-equivalent presence–background rank discrimination, Boyce/CBI, OR10, AICc where a valid likelihood/parameter count existed, and nested spatial cross-validation. These were retained as model diagnostics/comparators, not ecological truth.

Ecological recovery used a common environmental audit space and included environmental centroid error, niche breadth error, quantile-profile error and Schoener-D environmental overlap. Known-truth experiments additionally evaluated response structure and process recovery.

## Predecessor controlled-truth sequence

Earlier Product-A stages supplied two pieces of evidence that motivated the final counterfactual estimator.

First, predictive transfer and stable environmental response surfaces could coexist with incorrect generating-process attribution. Second, ecological Pareto filtering of adequate models could narrow retained response ranges while losing truth coverage and creating false necessary-process claims.

The v2.4–v2.6 necessity branch therefore used explicit process knockouts. In the complete v2.6 controlled-truth validation, false-required processes were zero and possible-process recall was 1.0, but possible-process precision was approximately 0.467 and `required_processes` was empty in all nine validation taxa. This branch is a false-necessity safety result, not the final process-membership estimator.

A later v2.7.2 consensus-first certificate intersected process sets from canonical and perturbation-robust ecological selectors. Across six niche families and unused seeds `3101`–`3110`, it exactly recovered hidden generating-process sets in 55/60 cases and process-set consensus exceeded exact fitted-model consensus (50/60 versus 38/60). Two independent computational processes reproduced all audited outputs exactly. However, temperature and water were true in every one of these 60 cases, so the suite did not provide independent presence/absence truth for all three ecological processes.

## Factorial process-membership generator

A stronger process-identification experiment was therefore prospectively declared in `configs/product_a_factorial_process_recovery_contract.json`.

The ecological process universe was `temperature`, `water` and `soil`. All seven non-empty process combinations were generated:

- temperature (`T`);
- water (`W`);
- soil (`S`);
- `T+W`;
- `T+S`;
- `W+S`;
- `T+W+S`.

The discovery denominator used seeds `4201`–`4205`, yielding 35 cases. Each case used 3,000 environmental cells, 260 occurrences, 950 target-group observations, six spatial blocks, three inner folds, outer holdout fraction 0.20 and minimum background support 70.

The environmental landscape retained correlated representations. The fixed candidate library contained 12 model specifications representing individual processes and combinations, including direct temperature and a correlated `temp_proxy`, plus a broad linear candidate containing irrelevant seasonality/noise terms. The predeclared process mapping collapsed `temp_proxy` into the temperature process.

Five exogenous perturbations were frozen:

- sampling bias strength 0.50 at access radius 0.35;
- canonical sampling bias 1.15 at radius 0.35;
- sampling bias 2.00 at radius 0.35;
- tight background radius 0.20 at sampling bias 1.15;
- broad background radius 0.80 at sampling bias 1.15.

Hidden generating-process truth was never an input to candidate fitting or selection.

## Factorial falsification of the stable-process predecessor

The existing canonical ecological selector, perturbation-robust ecological selector and their stable process intersection were applied unchanged to the 35 discovery cases. The predecessor exact process-set recovery was 22/35 (62.9%), below its frozen support threshold; AUC-selected fitted candidates were exact in 25/35. The predecessor was therefore classified as not supported for the stronger independently varying process-membership problem. No threshold, seed, process combination or candidate was removed after this outcome.

## Counterfactual process-recovery score

The final process-membership estimator is implemented in `src/sdmr/counterfactual_process_recovery.py`.

For each case, process `p` and perturbation `q`, candidate models first pass the same prediction-adequacy criterion used by the ecological selector:

- mean presence-background rank ≥ `0.50 + 0.01 = 0.51`;
- lower evidence bound `mean − 1 × SEM` ≥ 0.50.

Among prediction-adequate candidates, each candidate's ecological predictor set is mapped to the frozen process registry after removing declared observation-process predictors. Candidates are split into:

- **process-containing:** at least one predictor mapped to `p`;
- **process-excluded:** no predictor mapped to `p`.

Because aliases are mapped before classification, exclusion of temperature excludes both direct `temperature` and `temp_proxy` representations.

For each class we compute the maximum mean held-out Schoener-D niche overlap. When both classes contain adequate candidates, the perturbation-level score is

`g_pq = (max D_containing − max D_excluded) / (max D_all − min D_all)`.

If no prediction-adequate process-excluded candidate exists, `g_pq=+1`. If no adequate process-containing candidate exists, `g_pq=−1`. If the overlap range is effectively zero, `g_pq=0`. The case-level process score is the arithmetic mean of finite `g_pq` values across the five frozen perturbations.

The score uses prediction and held-out ecological recovery only. It never reads generating-process truth.

## Discovery-only threshold calibration

Only the 35 `4201`–`4205` discovery cases were used to calibrate process-specific thresholds. For each process, true/false labels were opened only for threshold development after the counterfactual scores already existed.

Discovery separation was:

- temperature: maximum false `0.25219538006511455`, minimum true `0.278597493561282`;
- water: maximum false `0.052498317045248225`, minimum true `0.0818358826795079`;
- soil: maximum false `0.2067529450797926`, minimum true `0.46173022310388284`.

The midpoint between the maximum discovery false score and minimum discovery true score was frozen prospectively for validation:

- temperature threshold `0.26539643681319824`;
- water threshold `0.06716709986237807`;
- soil threshold `0.33424158409183774`.

These values were written to `configs/product_a_counterfactual_process_validation_contract.json` before fresh validation. Post-validation threshold changes, seed drops, process-set drops, candidate changes and perturbation changes were prohibited.

## Fresh 35-case counterfactual validation

Unused seeds `4301`–`4305` were evaluated across the same seven process sets, yielding 35 fresh cases.

The prospectively frozen primary support gate required:

- all 35 cases available;
- exact complete process-set recovery ≥0.80;
- temperature sensitivity and specificity ≥0.80;
- water sensitivity and specificity ≥0.80;
- soil sensitivity and specificity ≥0.80.

All checks passed. Exact counterfactual process-set recovery was 30/35 (0.857), versus 23/35 for the predecessor stable core and 25/35 for the AUC-selected candidate. Temperature sensitivity/specificity were 1.000/0.933, water 1.000/0.800 and soil 1.000/0.933. Canonical and robust ecological fitted models disagreed in 18 cases; counterfactual process truth remained exact in 15/18.

The authoritative validation was workflow `34015684015`, artifact `9983844728`, digest `sha256:9a53abc38c45e93eb8696f1de7af5051776881c59ec5079f45b4ecc029068554`.

## Unchanged 70-case independent replication

After successful 35-case validation, the estimator and thresholds were frozen unchanged in `configs/product_a_counterfactual_process_replication_contract.json`. No method changes were permitted.

The independent replication used unused seeds `4401`–`4410` across all seven process sets (`n=70`). Each process was therefore truly present in 40 cases and absent in 30.

All primary support checks again passed:

- exact complete process-set recovery: **65/70 = 0.929**;
- temperature sensitivity/specificity: **1.000/0.933** (TP=40, FN=0, TN=28, FP=2);
- water sensitivity/specificity: **1.000/0.933** (TP=40, FN=0, TN=28, FP=2);
- soil sensitivity/specificity: **0.975/1.000** (TP=39, FN=1, TN=30, FP=0).

For descriptive comparison on the identical 70 cases, AUC-selected fitted candidates exactly recovered 56/70 complete process sets and the predecessor stable core 49/70. The canonical and robust ecological selectors chose different fitted models in 30/70 cases, while counterfactual process truth was exact in 27/30.

Paired exact outcomes against AUC were 51 both exact, 14 counterfactual-only exact, 5 AUC-only exact and 0 both wrong. This paired comparison was not the predeclared replication gate and is reported descriptively rather than as a new universal-superiority test.

Exact counterfactual recovery by process combination was `T` 8/10, `W` 8/10, `S` 10/10, `T+W` 10/10, `T+S` 10/10, `W+S` 10/10 and `T+W+S` 9/10.

The authoritative replication was workflow `34015900603`, artifact `9983940439`, digest `sha256:af72b78f64e5160dbc96a1147769e83a0b21b461d9b7111ca2e663e8f786d3eb`.

## Observation-process separation

Product A separately models ecological suitability and occurrence-record observation. Declared observation nuisance variables can be marginalized from ecological predictions, and candidate-independent nuisance evidence can be used to correct held-out occurrence-environment targets when that nuisance signal is reproducible.

In the earlier v2.7.2 controlled-truth suite, observation correction activated in all 10 observation-confounded cases and none of the other 50. AUC selected an `observer_only` candidate in 5/10 confounded cases, giving driver-process precision/recall/F1 of zero in those cases, while both ecological selectors chose `niche_plus_observer` in 10/10 and recovered the true `{temperature,water}` ecological process set.

## Fresh empirical endpoint

The final empirical scientific execution remains `product-a-v2-8-4-fresh-confirmation-v1`. Its candidate universe, taxa, thresholds and primary decision were consumed before the new factorial/counterfactual controlled-truth programme and are not retroactively changed.

Frozen invariants were:

- sealed fraction 0.25;
- split seeds `2026082201`, `2026082202`, `2026082203`;
- M sensitivity 150, 300 and 500 km;
- all 12 taxa and all three M specifications required in every part;
- model random state 0;
- prediction guardrail mean presence-rank delta versus AUC ≥−0.01;
- ecological nondomination required in at least two of three parts;
- strict ecological improvement required in at least two of three parts;
- process modal-status fraction ≥2/3.

The authoritative run was `33364164527`, frozen SHA `1496a6c63b19bf7711511a864ccb448fc123c963`, terminal artifact `9750071472`, digest `sha256:a4243eedae221e5ffd289062e27ec949b39f35a4f7a00849a56b047a3ccb8c9f`.

Prediction adequacy passed, ecological nondomination occurred in 3/3 parts, strict ecological improvement occurred in 0/3, and the terminal decision was `empirical_confirmation_not_supported`; Product A remained `not_promoted`.

## Reporting-only selector-contrast audit

After the empirical endpoint was frozen, its three finalized seed artifacts were inspected without changing any endpoint. Across 108 matched taxon × M × seed cells, ecological and AUC roles used identical candidate IDs and identical selected-predictor strings in 108/108 cells. All selected `all|logit_l2_C0.1_degree1_rs0`. Audited sealed presence rank, continuous Boyce, OR10, Schoener-D overlap, centroid distance, breadth error and quantile-profile error were likewise identical.

This explains the absence of realized empirical selector contrast. It does not imply that AUC identifies ecological process truth and does not change the formal empirical non-support.

## Statistical reporting

The factorial discovery lane (`n=35`) is method development and falsification evidence; it is not pooled with validation.

The fresh counterfactual validation (`n=35`) and unchanged independent replication (`n=70`) are reported separately. Primary outcomes are complete process-set exact recovery and per-process sensitivity/specificity. Process-level truth denominators in the 70-case replication are 40 positive and 30 negative labels for each of temperature, water and soil.

Descriptive Wilson intervals may be reported for exact-set proportions, but the prospectively frozen absolute support gates remain the primary validation criteria. Pairwise counts against AUC are descriptive because no post-validation universal-superiority threshold was introduced.

The empirical primary decision unit remains the frozen seed part (`n=3`); its 108 taxon × M × seed cells are reporting units for selector identity, not replacement inferential replicates.

## Software and computational environment

The repository package is `sdmr` version `0.3.0.dev0`, requires Python ≥3.10 and depends on NumPy, pandas and scikit-learn; optional geospatial/cloud paths use rasterio, pyarrow and duckdb. The repository is MIT licensed.

Counterfactual process scoring is implemented in `src/sdmr/counterfactual_process_recovery.py`; fresh validation and replication are implemented in `src/sdmr/counterfactual_process_validation.py` and `src/sdmr/counterfactual_process_replication.py`. Frozen contracts, workflow definitions, scientific receipts and source-data tables are retained in the repository.

## Claim boundary and no-rescue rules

The counterfactual result identifies **process membership under the declared candidate/process representation registry in controlled truth**. It does not identify physiological causation, fundamental-niche necessity or every possible real-world proxy channel.

The 35-case validation and 70-case replication may not be retuned by changing thresholds, seeds, process sets, candidate library or perturbations after their outcomes. The old factorial stable-core non-support remains part of the scientific record. The frozen v2.8.4 empirical endpoint remains `empirical_confirmation_not_supported` / `not_promoted` and is not rescued by the new controlled-truth result.
