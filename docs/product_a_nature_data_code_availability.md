# Data and Code Availability — Nature Ecology & Evolution draft

Status: **submission-production text / no scientific endpoint change**.

## Data availability

All manuscript claims are tied to prospectively frozen or reporting-only-audited evidence recorded in the public `zuizui0223/sdmr` repository. Empirical occurrence evidence originated from the GBIF monthly snapshot dated 1 August 2026, DOI `10.15468/dl.fs3btq`, download key `0020258-260721160103020`. The repository records the corresponding snapshot citation hash and the frozen taxon, environmental-manifest and accessible-area contracts used by Product A.

Controlled-truth and fresh empirical scientific endpoints are identified by immutable GitHub Actions artifact IDs and SHA-256 digests in repository contracts and result documents. The principal frozen artifacts are:

- v2.6 known-truth validation: workflow `32251711573`, terminal artifact `9364873176`, digest `sha256:78cda9c4c1e8a0ddab8371bf324d214cc9b8a76d1ebd65ad562da6de5913e3ba`;
- v2.7.2 deterministic known-truth validation: workflow `32629842082`, replicate-A artifact `9490817718`, digest `sha256:78b261f95c31d6c1df1f29aa02988abba2398bfca2765e7afdfe83d0acf74d4e`, and terminal artifact `9490827277`, digest `sha256:033b5393444f0d7365d6823d068e08778454496213f0f438188680740f846a17`;
- v2.8.4 fresh empirical endpoint: workflow `33364164527`, terminal artifact `9750071472`, digest `sha256:a4243eedae221e5ffd289062e27ec949b39f35a4f7a00849a56b047a3ccb8c9f`, with finalized seed artifacts `9750048481`, `9749405054` and `9749815263`.

The manuscript reporting audits do not create new scientific outcomes. They derive family-level v2.7.2 summaries and exact ecological-versus-AUC selector identity from these already frozen artifacts. Reporting scripts contain hard assertions against the frozen pooled values and empirical cell identities.

**Before submission:** create a release/archive with a permanent DOI for the exact manuscript branch and manuscript source-data files. The final Data Availability statement should replace branch-only references with the archived DOI while retaining the original GBIF DOI and frozen workflow/artifact provenance.

## Code availability

Source code is publicly available in `zuizui0223/sdmr` under the MIT License. The Python package is `sdmr` version `0.3.0.dev0` and requires Python ≥3.10. Core dependencies are NumPy, pandas and scikit-learn; optional geospatial/cloud dependencies include rasterio, pyarrow and duckdb. The repository contains automated tests, scientific contract files, GitHub Actions workflow definitions, provenance receipts and the reporting script `scripts/build_nature_product_a_figures.py`.

The deterministic v2.7.2 scientific implementation is pinned to commit `9b40393dda3d03943a403d0e7875e2d616b914e7` on frozen ref `frozen/product-a-v2-7-2-known-truth-9b40393d`. The authoritative v2.8.4 fresh empirical execution used frozen SHA `1496a6c63b19bf7711511a864ccb448fc123c963`.

**Before submission:** archive the exact Nature-submission code state with a permanent DOI and add a `CITATION.cff`/release tag if not already present. The archived package should include the manuscript reporting scripts and small source-data tables; large third-party/source artifacts may remain referenced by immutable workflow artifact IDs and external provider DOIs where redistribution is inappropriate.

## Reproducibility statement

The scientific evidence sequence was governed by fail-closed prospective contracts. Sealed evidence could not tune candidate choice or thresholds. Known-truth validation seeds were unused until the relevant design was frozen. A computational parity failure that changed one discrete selected-predictor result was retained as a failed predecessor; the deterministic successor fixed estimator and selection RNG state before new known-truth evidence was opened. The final empirical endpoint was retained unchanged after its preregistered ecological-support rule failed.

No additional Product-A scientific experiment, favorable-data search or empirical retuning is required or permitted for the submission package.