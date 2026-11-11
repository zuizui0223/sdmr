# Online Methods — Product A Nature Ecology & Evolution submission

Status: **submission-production document synchronized to the controlled-truth counterfactual estimator and both completed frozen empirical endpoints**.

## Study objective and inferential targets

Product A evaluates environmental-process claims from occurrence-only SDMs without equating predictive success with ecological truth. The manuscript distinguishes:

1. **predictive adequacy** — candidate models must predict withheld occurrence evidence before ecological interpretation;
2. **process membership** — the counterfactual estimator asks how much attainable held-out ecological niche recovery is lost when every declared representation of one process is removed from the adequate candidate class;
3. **process necessity** — a separate stronger exclusion certificate asks whether any adequate explanation survives process-information removal.

These are not combined into a weighted prediction–ecology super-score. Process membership under a declared representation registry is not physiological causation or fundamental-niche necessity.

## Prospective information barriers

Within empirical focal taxa, admitted occurrence records were processed before tuning and assigned by whole spatial blocks to model or sealed roles. Sealed rows could not influence predictor/universe selection, regularization, response complexity, accessible-area/background construction, candidate choice or promotion criteria. Controlled-truth discovery evidence could develop/calibrate a method only when later validation evidence remained unused and prospectively frozen.

## Occurrence and environmental evidence

Empirical occurrence evidence was tied to the GBIF monthly snapshot dated 1 August 2026, DOI `10.15468/dl.fs3btq`, download key `0020258-260721160103020`, with repository-recorded citation SHA-256 `022a524b59c4c037b28f252c08294e0f22c5eb7b3bce5c52a0a5fc6016f17050`.

The active empirical environmental manifest contained 43 predictors. Three nested universes were predeclared: `bioclim19`, `chelsa_bioclim` and `active_all`. Conventional model strategies included all variables, iterative VIF filtering and predictive forward selection. Model complexity and regularization were tuned only inside the model pool.

## Accessible-area and background sensitivity

Empirical analyses used 150, 300 and 500 km occurrence buffers as a matched accessible-area (`M`) sensitivity set. Each M specification requested up to 2,000 target-group background cells at 0.05° resolution. Target-group background is an observation/reference frame, not biological absence or a niche answer key.

## Conventional comparators and ecological recovery

Conventional criteria included AUC-equivalent presence–background rank discrimination, Boyce/CBI, OR10, AICc where a valid likelihood/parameter count existed, and nested spatial cross-validation. These remained diagnostics/comparators rather than ecological truth.

Ecological recovery used a common environmental audit space and included environmental centroid error, niche breadth error, quantile-profile error and Schoener-D environmental overlap.

## Predecessor controlled-truth sequence

Early stages showed that predictive transfer and stable environmental responses could coexist with incorrect process attribution. v2.3 then showed that ecological Pareto filtering could narrow model-set uncertainty while losing truth coverage and creating false necessity.

The v2.4–v2.6 necessity branch therefore used explicit process knockouts. In complete v2.6 validation, false-required processes were zero and possible-process recall 1.0, but possible-process precision was approximately 0.467 and `required_processes` was empty in all nine validation taxa.

A v2.7.2 consensus-first certificate exactly recovered hidden process sets in 55/60 cases in a six-family suite, but temperature and water were true in all 60 cases. It therefore did not establish independent presence/absence identification for all processes.

## Factorial process-membership generator

A stronger experiment prospectively varied `temperature`, `water` and `soil` across all seven non-empty combinations: `T`, `W`, `S`, `T+W`, `T+S`, `W+S`, `T+W+S`.

Discovery seeds `4201`–`4205` produced 35 cases. Each case used 3,000 environmental cells, 260 occurrences, 950 target-group observations, six spatial blocks, three inner folds, outer holdout fraction 0.20 and minimum background support 70. The fixed candidate library contained 12 specifications, including direct temperature and correlated `temp_proxy`; prospective process mapping collapsed `temp_proxy` into temperature.

Five perturbations varied sampling bias and accessible/background radius while hidden generating-process truth remained unavailable to model fitting/selection.

## Factorial falsification of the predecessor

The existing stable process intersection recovered only **22/35 = 62.9%** complete generating sets, versus **25/35 = 71.4%** for AUC. This failure was retained. No process set, seed, candidate or threshold was removed after outcome.

## Counterfactual process-recovery score

For each case, process `p` and frozen perturbation `q`, candidates first pass the prediction-adequacy gate:

- mean presence-background rank >=0.51;
- lower evidence bound `mean − SEM` >=0.50.

Candidate predictor sets are mapped to the frozen process registry. Adequate candidates are separated into process-containing and process-excluded classes; exclusion of temperature removes both direct `temperature` and declared `temp_proxy` representations.

When both classes contain adequate candidates,

`g_pq = (max D_containing − max D_excluded) / (max D_all − min D_all)`,

where `D` is mean held-out Schoener-D niche overlap. Empty containing/excluded classes use the prospectively defined boundary statuses/codes, and a near-zero overlap range maps to zero. Case-level process score is the arithmetic mean across the five frozen perturbations. The score never reads hidden generating-process truth.

## Discovery-only threshold calibration

Only discovery seeds `4201`–`4205` were used to calibrate thresholds. Frozen midpoints were:

- temperature `0.26539643681319824`;
- water `0.06716709986237807`;
- soil `0.33424158409183774`.

They were written to the validation contract before seeds `4301+` were opened. Post-validation threshold, seed, process-set, candidate-library and perturbation changes were prohibited.

## Fresh 35-case validation

Unused seeds `4301`–`4305` yielded 35 fresh cases. The frozen gate required all 35 available, exact process-set recovery >=0.80, and sensitivity/specificity >=0.80 for T, W and S separately.

All gates passed. Counterfactual exact recovery was **30/35**, predecessor **23/35**, AUC **25/35**. Temperature sensitivity/specificity were 1.000/0.933, water 1.000/0.800, soil 1.000/0.933. Process sets remained exact in 15/18 cases where ecological fitted models disagreed.

Authoritative validation: workflow `34015684015`, artifact `9983844728`, digest `sha256:9a53abc38c45e93eb8696f1de7af5051776881c59ec5079f45b4ecc029068554`.

## Unchanged 70-case replication

After validation, estimator and thresholds were frozen unchanged. Unused seeds `4401`–`4410` yielded 70 cases, with each process present in 40 and absent in 30.

Results:

- exact complete process sets **65/70 = 0.929**;
- T TP/FN/TN/FP 40/0/28/2, sensitivity/specificity 1.000/0.933;
- W 40/0/28/2, 1.000/0.933;
- S 39/1/30/0, 0.975/1.000;
- AUC exact **56/70**;
- predecessor exact **49/70**;
- process set exact under fitted-model disagreement **27/30**.

The same-case AUC comparison is descriptive rather than a universal-superiority endpoint.

Authoritative replication: workflow `34015900603`, artifact `9983940439`, digest `sha256:af72b78f64e5160dbc96a1147769e83a0b21b461d9b7111ca2e663e8f786d3eb`.

## Observation-process separation

In the earlier observation-confounded controlled family, AUC selected `observer_only` in 5/10 cases and recovered no ecological driver there, while ecological/observation separation selected `niche_plus_observer` and recovered `{temperature,water}` in 10/10. This is mechanism evidence within the tested family, not a universal empirical rate.

## Frozen empirical endpoint v2.8.4

The final v2.8.4 scientific execution (`product-a-v2-8-4-fresh-confirmation-v1`) was consumed before the later counterfactual programme and is not retroactively changed.

Frozen invariants included sealed fraction 0.25; split seeds `2026082201`–`2026082203`; M=150/300/500 km; all 12 taxa and M conditions required; prediction guardrail mean presence-rank delta versus AUC >=−0.01; ecological nondomination >=2/3 parts; strict ecological improvement >=2/3 parts.

The authoritative run was `33364164527`, terminal artifact `9750071472`, digest `sha256:a4243eedae221e5ffd289062e27ec949b39f35a4f7a00849a56b047a3ccb8c9f`.

Prediction adequacy passed and ecological nondomination occurred in 3/3 parts, but strict ecological improvement occurred in 0/3. The terminal decision was `empirical_confirmation_not_supported`; Product A remained `not_promoted`.

A reporting-only audit then showed ecological/AUC candidate and selected-predictor identity in **108/108** matched taxon × M × seed cells. This explains the realized lack of selector contrast but does not imply AUC identifies ecological truth.

## Frozen real positive-control design

A later prospectively frozen audit supplied an external one-sided biological answer key for eight taxa. Plant controls were:

- *Quercus robur* — water;
- *Silene ciliata* — water;
- *Plantago alpina* — temperature;
- *Silene acaulis* — temperature.

Nonplant controls were:

- *Bombus terrestris* — temperature;
- *Ochotona princeps* — temperature;
- *Plethodon cinereus* — water;
- *Cepaea nemoralis* — water.

Each taxon was evaluated under M=150, 300 and 500 km. The unchanged taxon recovery rule required:

1. all three M-specific scores available;
2. mean expected-process score >0;
3. at least two of the three M-specific scores positive.

Each four-taxon lane was supported only if >=3/4 taxa recovered and at least one recovered taxon occurred in both the temperature and water groups. Missing M values remained in the denominator; no available-case rule or tolerance was introduced after outcome.

## Real positive-control process scoring and information boundary

The empirical process challenge used **model-pool inner spatial cross-validation**. For a target process, prediction-adequate process-containing and process-excluded candidates were compared using held-out Schoener-D ecological recovery under the frozen representation registry. When both adequate classes existed, the score represented measured relative recovery loss; empty adequate classes produced the contract's boundary/unavailable states rather than a measured complete ecological loss.

Outer rows had been separated and materialized, but this endpoint did **not** invoke outer-sealed process-transfer evaluation. Therefore the positive-control result is independent literature-backed checking of inner-CV process scores, not demonstrated outer spatial-transfer performance.

## Real positive-control outcome and audit semantics

All **24/24 taxon × M pipelines** completed technically, but only **21/24** contained at least one prediction-adequate candidate and only **17/24** expected-process cells had two-sided adequate comparisons.

Frozen taxon outcomes were:

- plant lane **2/4**: Plantago alpina and Silene acaulis recovered; Quercus robur and Silene ciliata water controls did not;
- nonplant lane **1/4**: Ochotona princeps recovered; Bombus terrestris, Plethodon cinereus and Cepaea nemoralis did not;
- temperature overall **3/4**;
- water overall **0/4**.

Both original lane support gates therefore failed. Combined 3/8 is descriptive only, not a pooled accuracy endpoint.

Quercus had mean expected-process score −0.276692 and Silene ciliata −0.000704 despite all three M values being available. Bombus/150 km, Plethodon/500 km and Cepaea/300 km had no prediction-adequate candidate. These outcomes diagnose the present estimator/representation system; they do not prove the externally supported biological processes are absent.

The external labels are positive only. They cannot estimate specificity, a false-positive rate or complete generating-process accuracy; an always-positive rule would recover every positive control.

## No-refit empirical result audit

`scripts/audit_real_positive_control_results.py` independently reconstructs 96 candidate summaries from 284 stored fold rows, all 48 process × M scores, eight taxon results and both lane decisions. It verifies frozen labels, denominators, archive provenance, numeric outputs and categorical states without fitting models or changing any scientific rule.

Audited source tables include `source_data/real_positive_control_v1_taxon_audit.csv` and `source_data/real_positive_control_v1_cell_audit.csv`.

## Statistical reporting

Discovery (`n=35`), fresh validation (`n=35`) and unchanged replication (`n=70`) are reported separately. Controlled-truth primary outcomes are exact complete process-set recovery and per-process sensitivity/specificity.

For v2.8.4, the primary decision unit remains the frozen seed part (`n=3`); 108 matched cells are reporting units for selector identity.

For real positive controls, the two four-taxon lane decisions retain the prospectively frozen >=3/4 plus process-group rule. Because all labels are positive, no specificity estimate is reported. Missing/empty adequate classes are retained rather than imputed. The combined 3/8 is descriptive only.

## Software and computational environment

The repository package is `sdmr` version `0.3.0.dev0`, Python >=3.10, with NumPy, pandas and scikit-learn; optional geospatial/cloud paths use rasterio, pyarrow and duckdb. The repository is MIT licensed.

Counterfactual scoring is implemented in `src/sdmr/counterfactual_process_recovery.py`; validation/replication in `src/sdmr/counterfactual_process_validation.py` and `src/sdmr/counterfactual_process_replication.py`. Empirical positive-control result auditing is in `scripts/audit_real_positive_control_results.py`.

## Claim boundary and no-rescue rules

The controlled-truth result identifies **process membership under the declared candidate/process representation registry**. It does not establish physiological causation, fundamental-niche necessity or closure over every real-world proxy/composite.

The current real-data system has **not** passed prospective validation for general process identification. The positive-control labels are consumed. Any successor developed in response to their failures must use a new frozen biological validation panel and must prospectively address adequate-alternative availability, water-process representation, complete fold handling and explicit outer-transfer evaluation.

Do not alter old taxa, labels, thresholds, M requirements, missingness rules or terminal decisions to improve the historical result.
