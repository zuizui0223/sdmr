# Nature Portfolio software submission checklist — Product A draft

Status: **submission-production aid; complete against the journal's current form at submission**.

Newly developed software is central to the manuscript. The final submission should include the Nature Portfolio software checklist.

## Software identity

- software name: `sdmr`
- repository: `https://github.com/zuizui0223/sdmr`
- license: MIT
- package version: `0.3.0.dev0`
- language: Python
- supported Python: ≥3.10
- manuscript role: prospective occurrence-only SDM evaluation; process-specific counterfactual ecological-recovery scoring; exclusion-based process-necessity safety certificates; observation-process correction; controlled-truth validation/replication; frozen empirical confirmation; reporting reconstruction

## Final scientific estimator

The principal positive estimator is **counterfactual process recovery**.

For each declared process, prediction-adequate candidates are separated into process-containing and process-excluded classes after frozen process-alias mapping. The estimator measures the normalized loss in best attainable held-out Schoener-D niche overlap when every declared representation of the process is excluded, averaged across five predeclared sampling/background perturbations.

Implementation:

- `src/sdmr/counterfactual_process_recovery.py`
- `src/sdmr/counterfactual_process_validation.py`
- `src/sdmr/counterfactual_process_replication.py`

Frozen process thresholds:

- temperature `0.26539643681319824`;
- water `0.06716709986237807`;
- soil `0.33424158409183774`.

These thresholds were calibrated from discovery seeds `4201`–`4205` and frozen before fresh validation.

## Scientific estimator boundaries

The repository also contains predecessor and complementary estimators. They must not be conflated.

1. **Counterfactual process membership — final headline estimator.** Fresh validation recovered 30/35 complete process sets; an unchanged 70-case replication recovered 65/70.
2. **Consensus-first stable process core — predecessor proof of concept.** It performed strongly in the earlier six-family v2.7.2 suite but fell to 22/35 in the stronger factorial discovery test. Its earlier 55/60 result is not the final headline.
3. **Exclusion-based necessity — separate stronger estimand.** v2.6 controlled false-required claims but remained broad; it is not the source of the counterfactual 92.9% process-membership result.

## Exact scientific implementations and artifacts

### Factorial predecessor falsification / discovery

- frozen contract: `configs/product_a_factorial_process_recovery_contract.json`
- process sets: all seven non-empty combinations of temperature, water and soil
- discovery seeds: `4201`–`4205`
- denominator: 35
- authoritative preserved artifact used for successor discovery: `9983694702`
- predecessor exact stable-process recovery: 22/35

### Fresh counterfactual validation

- contract: `configs/product_a_counterfactual_process_validation_contract.json`
- validation seeds: `4301`–`4305`
- denominator: 35
- workflow: `34015684015`
- artifact: `9983844728`
- digest: `sha256:9a53abc38c45e93eb8696f1de7af5051776881c59ec5079f45b4ecc029068554`
- exact process-set recovery: 30/35

### Independent unchanged counterfactual replication

- contract: `configs/product_a_counterfactual_process_replication_contract.json`
- replication seeds: `4401`–`4410`
- denominator: 70
- workflow: `34015900603`
- artifact: `9983940439`
- digest: `sha256:af72b78f64e5160dbc96a1147769e83a0b21b461d9b7111ca2e663e8f786d3eb`
- exact process-set recovery: 65/70
- AUC comparator: 56/70
- predecessor stable core: 49/70

### Earlier exclusion-based known-truth validation

- v2.6 workflow run: `32251711573`
- terminal artifact: `9364873176`
- digest: `sha256:78cda9c4c1e8a0ddab8371bf324d214cc9b8a76d1ebd65ad562da6de5913e3ba`

### Earlier deterministic v2.7.2 predecessor

- implementation SHA: `9b40393dda3d03943a403d0e7875e2d616b914e7`
- workflow run: `32629842082`
- replicate-A artifact: `9490817718`
- terminal artifact: `9490827277`

### Fresh empirical endpoint — unchanged

- scientific execution ID: `product-a-v2-8-4-fresh-confirmation-v1`
- frozen SHA: `1496a6c63b19bf7711511a864ccb448fc123c963`
- workflow: `33364164527`
- terminal artifact: `9750071472`
- digest: `sha256:a4243eedae221e5ffd289062e27ec949b39f35a4f7a00849a56b047a3ccb8c9f`
- decision: `empirical_confirmation_not_supported`; `not_promoted`

## Installation

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e '.[test]'
```

Core dependencies:

- `numpy>=1.24`
- `pandas>=2.0`
- `scikit-learn>=1.3`

Optional groups include rasterio, pyarrow and duckdb. Nature reporting additionally installs Matplotlib.

## Automated tests

Repository tests are under `tests/` and configured through `pyproject.toml`.

```bash
pytest
```

Counterfactual unit tests check frozen process aliases, candidate/process exclusion semantics, validation contracts and threshold identity. Scientific contracts fail closed when seeds, denominators, thresholds, candidate/process sets or required states differ from the pre-outcome declarations.

## Nature reporting reproduction

The reporting workflow is `.github/workflows/nature-product-a-reporting.yml`.

Reporting scripts include:

```text
scripts/build_nature_product_a_concept_figures.py
scripts/build_nature_product_a_figures.py
scripts/render_nature_fig3_counterfactual.py
scripts/check_nature_manuscript_format.py
```

Figure 3 is now rendered from frozen counterfactual source-data tables:

```text
source_data/nature_fig3_counterfactual_methods.csv
source_data/nature_fig3_counterfactual_process_summary.csv
source_data/nature_fig3_counterfactual_process_sets.csv
```

The workflow fails unless it reconstructs/asserts:

- fresh validation exact counts: counterfactual 30/35, AUC 25/35, predecessor 23/35;
- independent replication exact counts: counterfactual 65/70, AUC 56/70, predecessor 49/70;
- model-disagreement replication: 30 cases, counterfactual exact 27/30;
- temperature replication TP/FN/TN/FP = 40/0/28/2;
- water = 40/0/28/2;
- soil = 39/1/30/0;
- process-set exact counts: T 8, W 8, S 10, T+W 10, T+S 10, W+S 10, T+W+S 9.

The empirical reporting gate independently retains:

- 108 matched taxon × M × seed cells;
- ecological/AUC candidate and selected-predictor identity in all 108;
- common candidate `all|logit_l2_C0.1_degree1_rs0`;
- nondomination 3/3, strict improvement 0/3, mean presence-rank delta 0.0.

## Determinism and reproducibility

The earlier v2.7.2 successor fixed scikit-learn model `random_state=0`, selection NumPy seed `0`, and exact discrete parity; successful independent process replication had observed maximum numeric difference 0.0.

For the final counterfactual estimator, reproducibility is primarily protected through immutable process sets, seed partitions, candidate library, perturbations and process thresholds. Validation and replication are disjoint. The replication contract explicitly records `method_changes_after_validation=false`.

## Hardware / computational resources

No GPU is required for the reported logistic-regression scientific core or reporting reconstruction. Scientific workflows used standard hosted CPU runners. Final hardware/runtime details should be copied only from workflow metadata.

## User interaction / non-default settings

Scientific results are driven by machine-readable contracts/workflow inputs rather than interactive choices. Process combinations, discovery/validation/replication seeds, candidate library, perturbations, thresholds and empirical endpoints are frozen in repository contracts.

## Primary submission documentation

- `docs/product_a_nature_ecology_evolution_article_draft.md`
- `docs/product_a_nature_ecology_evolution_online_methods.md`
- `docs/product_a_final_claim_spine.md`
- `docs/product_a_counterfactual_process_recovery_result_2026-09-06.md`
- `docs/product_a_nature_data_code_availability.md`
- `docs/product_a_nature_reporting_summary_draft.md`
- `docs/product_a_nature_reference_boundary.md`

## Permanent archival requirement

Before submission, create a permanent DOI archive of the exact submission state including source code, contracts, reporting scripts, source-data tables, `CITATION.cff`, dependency metadata and reproduction instructions. Insert the resulting DOI into Code Availability. Do not invent a DOI before the archive exists.

## Claim-safety boundary

No further retuning of the consumed counterfactual validation/replication is authorized. Thresholds, seeds, process sets, candidate library and perturbations may not be changed after outcome. The new controlled-truth result identifies process membership under the declared registry; it does not establish physiological causation or complete proxy closure. The frozen v2.8.4 empirical result remains `empirical_confirmation_not_supported` / `not_promoted` and is not rescued by the new simulation result.
