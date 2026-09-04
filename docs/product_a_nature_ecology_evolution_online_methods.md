# Online Methods — Product A Nature Ecology & Evolution submission

Status: **submission-production document only; no new Product-A experiment or endpoint change**.

## Study objective and inferential target

Product A evaluates whether environmental-process claims can be identified from occurrence-only species distribution models (SDMs) without equating predictive success with ecological necessity. The target is **process-information necessity under a declared representation registry**, not proof of a complete causal mechanism or fundamental niche. Prediction is treated as an adequacy layer. A process claim is tested by whether an adequate ecological certificate remains available when the declared information associated with that process is excluded under a prospectively frozen design.

## Prospective information barriers

Within each empirical focal taxon, admitted occurrence records were deterministically processed before tuning and assigned by whole spatial blocks to `model` or `sealed` roles. Sealed rows could not influence predictor/universe selection, regularization, response complexity, stopping, accessible-area/background construction, candidate choice or promotion criteria. A second barrier separated discovery taxa from unseen validation taxa: discovery taxa could select a complete procedure, whereas validation taxa were not used until that procedure was frozen.

The Product-A v1 frozen contract used a minimum of 80 admitted occurrences and 50 unique 0.05° cells per species. The initial sealed fraction was 0.20; repeated stability used 0.15, 0.20 and 0.30. The empirical successor ultimately used the independently calibrated sealed fraction 0.25. Focal taxa could be excluded only by predeclared data-sufficiency/background gates and were not removable because of unfavorable method results.

## Occurrence and environmental evidence

The original Product-A empirical evidence was tied to the GBIF monthly occurrence snapshot dated 1 August 2026, DOI `10.15468/dl.fs3btq`, download key `0020258-260721160103020`, with repository-recorded citation SHA-256 `022a524b59c4c037b28f252c08294e0f22c5eb7b3bce5c52a0a5fc6016f17050`. Product-A tooling independently required the supplied DOI to match the snapshot citation before extraction.

The active environmental manifest contained 43 predictors. Three nested universes were predeclared: `bioclim19`, `chelsa_bioclim` and `active_all`. No larger universe was assumed to be preferable. Predictor/model strategies included all variables, iterative VIF filtering and predictive forward selection; later Product-A v2 candidates added ecological-recovery procedures behind the same information barrier. Model complexity and regularization were tuned only inside the model pool.

## Accessible-area and background sensitivity

Accessible-area/background (`M`) assumptions were not optimized by score. The empirical programme used occurrence buffers of 150, 300 and 500 km as a matched sensitivity set. Each M specification requested up to 2,000 target-group background cells at 0.05° resolution. The target-group reference came from Plantae records in the same GBIF snapshot. The complete predeclared focal-taxon panel was excluded from the target-group source before splitting so that sealed focal positives could not re-enter through background.

Target-group background is treated as an observation/reference frame, not as biological absence or a niche answer key.

## Conventional model-evaluation comparators

Conventional criteria retained for comparison included AUC-equivalent presence–background rank discrimination, Boyce/CBI, OR10, AICc where a valid likelihood/parameter count existed, and local nested spatial cross-validation. These quantities were used as model-evaluation or selection criteria and were not defined as ecological truth.

## Ecological recovery measurements

Candidate procedures were evaluated in a common environmental audit space fitted using model-pool information only. Recovery measurements included environmental centroid error, niche breadth error, environmental quantile-profile error, Schoener-D environmental overlap, response-curve structure and environmental limits where literal generating truth was available, and process recovery under known-truth generators. Prediction and ecological metrics were not collapsed into a weighted super-score.

## Known-truth generators and prospective validation

Known-truth simulation supplied process and response information unavailable from empirical occurrence data. The deterministic v2.7.2 successor prospectively froze six niche families: `gaussian`, `asymmetric`, `soft_threshold`, `interaction`, `omitted_driver` and `observation_confounded`. Ten previously unused seeds (`3101`–`3110`) were evaluated for every family, yielding 60 cases. Each case used 2,400 cells, 230 occurrences, 820 target-group observations, six spatial blocks, three inner folds and a minimum background support of 55. Hidden generating truth was not used during candidate selection.

The v2.7.2 run was repeated in two independent Python processes. The pre-outcome determinism contract required exact equality of discrete scientific outputs and numeric agreement at `rtol=1e-10`, `atol=1e-10`; any discrete difference failed closed. The model `random_state` and selection-process NumPy seed were both fixed to 0. The frozen solver remained scikit-learn `liblinear`; all other model hyperparameters, candidate strategies, predictor universe, prediction-adequacy rules and ecological-recovery metrics were unchanged from the predecessor.

Predeclared v2.7.2 non-regression thresholds required robust-selector coverage ≥0.95, stable-core precision ≥0.90, stable-core recall ≥0.90, stable-core F1 ≥0.90, correction activation of 1.0 in the observation-confounded family and 0.0 in all other families. Failure was allowed as a valid result and thresholds could not be changed after outcome inspection.

## From model-set agreement to falsification-first certificates

An earlier set-valued certificate retained complete prediction-adequate candidates and then pruned to an ecological Pareto set. Necessary processes were initially defined from the intersection of retained fitted process sets and response uncertainty from their min–max spread. Known-truth validation showed that this operation could lose true process/boundary coverage and create a false necessary-process core.

The successor logic therefore became falsification-first. Process status distinguished claims that were refuted as necessary, required by the frozen evidence contract, or unresolved. Lack of evidence remained unresolved rather than being converted into absence. Boundary claims were calibrated separately using discovery-only evidence; validation truth could not create missing calibration support or relax a frozen support threshold.

In v2.6, after prospective calibration redundancy, all three validation panels and all nine validation taxa had complete process and boundary certificates. False-required processes were zero and minimum possible-process recall was 1.0. Possible-process precision was 0.467 in all three panels, and calibrated boundary intervals were wider than complete-adequate intervals, preserving the safety–sharpness limitation as part of the result rather than pruning it away.

## Observation-process separation

Product A separates ecological suitability from occurrence-record observation. Declared observation nuisance variables can be marginalized from predictions. In addition, held-out occurrence environments can themselves be observation-biased, so a candidate-independent nuisance model transports the held-out occurrence target toward a common target-group observation reference when reproducible nuisance-only evidence is present. When correction is inactive, held-out weights remain exactly 1 to avoid introducing finite-sample nuisance weighting.

In the frozen v2.7.2 controlled-truth test, observation correction activated in 10/10 observation-confounded cases and 0/50 cases from the other five families.

## Fresh empirical confirmation endpoint

The final empirical scientific execution was `product-a-v2-8-4-fresh-confirmation-v1`. Its scientific semantics were inherited unchanged from the predecessor; v2.8.4 changed execution/runtime structure only. The frozen invariants were:

- sealed fraction: 0.25;
- split seeds: `2026082201`, `2026082202`, `2026082203`;
- M sensitivity: 150, 300 and 500 km;
- all 12 taxa required in every seed part;
- all three M specifications required in every part;
- model random state: 0;
- selection-process NumPy seed: 0;
- primary denominator: three seed parts;
- prediction guardrail: mean presence-rank delta versus AUC ≥ −0.01;
- ecological nondomination required in at least two parts;
- strict ecological improvement required in at least two parts;
- process modal-status fraction ≥2/3.

Candidate universe, candidate library, thresholds, taxa, M, seeds, sealed fraction, denominator and decision rule were fixed before sealed outcomes were opened. Sealed outcomes could not select candidates or alter scientific thresholds.

The authoritative execution was workflow run `33364164527`, attempt 1, frozen SHA `1496a6c63b19bf7711511a864ccb448fc123c963`. The terminal artifact was `9750071472`, digest `sha256:a4243eedae221e5ffd289062e27ec949b39f35a4f7a00849a56b047a3ccb8c9f`.

## Reporting-only selector-contrast audit

After the terminal scientific decision was already frozen, a reporting-only audit inspected the three finalized seed artifacts without changing any endpoint. Each seed contained 12 taxa × 3 M specifications × 2 roles, giving 108 matched ecological-versus-AUC taxon × M × seed cells across the full endpoint.

Candidate ID and selected-predictor strings were exactly identical between ecological and AUC roles in 108/108 matched cells. All cells used `all|logit_l2_C0.1_degree1_rs0`. Audited sealed presence-rank, continuous Boyce, OR10, Schoener-D overlap, centroid distance, breadth error and quantile-profile error were also identical between roles. This audit explains the realized absence of selector contrast but does not change the formal endpoint from `empirical_confirmation_not_supported` to `not_tested`.

## Statistical reporting and replication units

Known-truth family-level summaries use 10 independently seeded cases per preregistered niche family (60 total). Precision, recall and F1 are reported for the stable process core against hidden generating processes. Process-set consensus and exact-model consensus are case-level binary outcomes and are summarized as fractions within family and across all 60 cases.

The fresh empirical primary decision unit is the preregistered seed part (n=3), each of which contains the full 12-taxon × 3-M denominator. Taxon × M × seed rows (108 matched cells) are used only for reporting the realized selector identity and metric identity; they do not replace the frozen three-part decision rule or create post hoc inferential replication.

## Software and computational environment

The repository package is `sdmr` version `0.3.0.dev0`, requires Python ≥3.10 and depends on NumPy, pandas and scikit-learn; optional geospatial/cloud paths use rasterio, pyarrow and duckdb. The repository is MIT licensed and includes automated tests, frozen scientific contracts, workflow definitions, evidence receipts and reporting scripts. The Nature reporting figures are generated by `scripts/build_nature_product_a_figures.py`, which contains hard assertions for the frozen v2.7.2 pooled recovery values, 38/60 exact-model consensus, 50/60 process-set consensus, the three empirical seeds, 108 matched empirical cells and exact ecological/AUC candidate identity.

## Reproducibility and no-rescue boundary

No Product-A v2.9 experiment is authorized. The consumed v2.8.4 endpoint must not be rerun, retuned, rescued or replaced. No taxon, seed, M, sealed fraction, threshold, candidate library, predictor universe, denominator, source or provider may be changed to seek a favorable result. A future hierarchy/proxy-closure experiment would require a genuinely new prospective contract and independent evidence.