# Data and Code Availability — Nature Ecology & Evolution draft

Status: **submission-production text; counterfactual controlled-truth successor integrated; empirical endpoint unchanged**.

## Data availability

All manuscript claims are tied to prospectively frozen or reporting-only-audited evidence recorded in the public `zuizui0223/sdmr` repository. Empirical occurrence evidence originated from the GBIF monthly snapshot dated 1 August 2026, DOI `10.15468/dl.fs3btq`, download key `0020258-260721160103020`. The repository records the snapshot citation hash and frozen empirical taxon, environmental-manifest and accessible-area contracts.

Principal scientific artifacts are:

- v2.6 exclusion-based known-truth validation: workflow `32251711573`, artifact `9364873176`, digest `sha256:78cda9c4c1e8a0ddab8371bf324d214cc9b8a76d1ebd65ad562da6de5913e3ba`;
- v2.7.2 predecessor deterministic known-truth suite: workflow `32629842082`, artifact `9490817718`, terminal artifact `9490827277`;
- factorial process-membership discovery/falsification: frozen contract `configs/product_a_factorial_process_recovery_contract.json`, seeds `4201`–`4205`, 35 cases; preserved discovery artifact `9983694702`;
- fresh counterfactual process validation: workflow `34015684015`, artifact `9983844728`, digest `sha256:9a53abc38c45e93eb8696f1de7af5051776881c59ec5079f45b4ecc029068554`;
- unchanged independent counterfactual replication: workflow `34015900603`, artifact `9983940439`, digest `sha256:af72b78f64e5160dbc96a1147769e83a0b21b461d9b7111ca2e663e8f786d3eb`;
- frozen v2.8.4 fresh empirical endpoint: workflow `33364164527`, terminal artifact `9750071472`, digest `sha256:a4243eedae221e5ffd289062e27ec949b39f35a4f7a00849a56b047a3ccb8c9f`, with finalized seed artifacts `9750048481`, `9749405054` and `9749815263`.

Small source-data tables underlying the main counterfactual reporting figure are committed under `source_data/`, including fresh-validation/replication method counts, per-process TP/FN/TN/FP and per-process-set recovery. Reporting transformations do not alter scientific thresholds or endpoints.

**Before submission:** create a release/archive with a permanent DOI for the exact manuscript branch, contracts, code and source-data state. The final Data Availability statement should replace branch-only references with this archived DOI while retaining the GBIF DOI and immutable workflow/artifact provenance.

## Code availability

Source code is publicly available in `zuizui0223/sdmr` under the MIT License. The Python package is `sdmr` version `0.3.0.dev0` and requires Python ≥3.10. Core dependencies are NumPy, pandas and scikit-learn; optional geospatial/cloud dependencies include rasterio, pyarrow and duckdb.

Counterfactual process membership is implemented in:

- `src/sdmr/counterfactual_process_recovery.py`;
- `src/sdmr/counterfactual_process_validation.py`;
- `src/sdmr/counterfactual_process_replication.py`.

The relevant frozen contracts are:

- `configs/product_a_factorial_process_recovery_contract.json`;
- `configs/product_a_counterfactual_process_validation_contract.json`;
- `configs/product_a_counterfactual_process_replication_contract.json`.

The repository also contains automated tests, scientific contracts, GitHub Actions workflows, provenance receipts and Nature reporting scripts. Figure 3 is reconstructed from committed frozen source-data tables by `scripts/render_nature_fig3_counterfactual.py` with hard assertions for the 35-case validation and 70-case replication values.

The earlier deterministic v2.7.2 implementation is pinned to commit `9b40393dda3d03943a403d0e7875e2d616b914e7`. The authoritative v2.8.4 fresh empirical execution used frozen SHA `1496a6c63b19bf7711511a864ccb448fc123c963`.

**Before submission:** archive the exact Nature-submission code state with a permanent DOI. Include manuscript/reporting scripts, machine-readable contracts, source-data tables, `CITATION.cff` and dependency metadata. Large third-party/source artifacts may remain referenced by immutable workflow artifact IDs and provider DOIs where redistribution is inappropriate.

## Reproducibility statement

The scientific sequence was governed by fail-closed prospective contracts. The stronger 35-case factorial truth test first falsified the predecessor stable-process estimator. Those discovery cases were then used only to freeze counterfactual process thresholds before unused validation seeds were opened. Fresh validation used seeds `4301`–`4305`; the estimator and thresholds were then left unchanged for independent replication on `4401`–`4410`. No seed, process combination, threshold, candidate library or perturbation was changed after the corresponding outcome.

The v2.8.4 empirical endpoint remains separately consumed and unchanged after its preregistered ecological-support rule failed. The new controlled-truth result does not retroactively convert it into empirical confirmation.
