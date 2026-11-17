# Independent NEON cohort: source-only availability and identity boundary (v1)

**Status (2026-11-17):** candidate data-source verification, NOT an independent tree-growth, survival or niche validation. This work is an isolated successor to the already consumed FIA VA/WI growth analyses on PR #284; it does not modify their end points. Original FIA v4, Product A, M5 and the blocked Product B remain unchanged.

## What we can identify without opening any biological response

The NSF National Ecological Observatory Network (NEON) **Vegetation structure** product is \`DP1.10098.001\`, release \`RELEASE-2026\`, DOI \`10.48443/pypa-qf12\`. NEON is a different network from FIA and has event-based woody plant observations. According to the [2026 product documentation](https://data.neonscience.org/data-products/DP1.10098.001/RELEASE-2026), **\`eventID × individualID × tempStemID\`** should be unique within the \`vst_apparentindividual\` table, but \`tempStemID\` for multi-stem trees is **not** a persistent between-year stem identifier. Taxonomic identity and plot survey coverage require other tables, such as \`vst_mappingandtagging\` and \`vst_perplotperyear\`.

The public product catalog at \`https://data.neonscience.org/api/v0/products/DP1.10098.001\` includes site codes and release/month availability. It can be accessed without a token. NEON's [published API documentation](https://data.neonscience.org/data-api/endpoints/data/) explicitly requires **an API token for the \`/data\` file endpoints**, while its [product catalog endpoint](https://data.neonscience.org/data-api/endpoints/products/) supports public metadata access. This project must **never** request, log, save or commit an NEON token or attempt to use a user's credentials without authorization.

### Fixed, response-blind site enumeration

\`experiments/fia_independent_neon_catalog_v1.py\` reads exactly one **public metadata** JSON response for the predeclared 2026 release and audits *all sites* in the catalog, not handpicked sites that look favorable. The gate validates product ID, unique four-letter site codes, release identity and unambiguous ISO release months. A missing or malformed catalog is recorded as **metadata unavailable**, never a population count of zero.

Per site it records the years covered by released **file availability**, and designates a **candidate time span of at least four calendar years** (a development-only criterion informed by the earlier FIA remeasurement windows). It pins a canonical JSON SHA-256 of the complete public product catalog, stores only this public catalog and the derived source receipt, and exposes all zero/one/year candidates.

Importantly: a site with many available release months may have **zero verified remeasured trees**, may include different vegetation plots at different dates, or may lack any of the five preselected FIA taxa. Consequently all these quantities are explicitly **unknown** at this stage: repeated individual trees, stem identity, source-survey inclusion/detection effort, condition/management, five-taxon species overlap, soil/microclimate, independent tree demographic response coverage. Site-month publication is not individual-level longitudinal data.

### Necessary response-stage checks, not yet allowed to run

1. Obtain legally/technically authorized NEON data access and **fix release, site panel and acquisition fingerprints** before biological outcomes. Archive exact source response bytes securely according to NEON data terms; a SHA string without original raw bytes is insufficient to reproduce measurements.
2. Read actual \`vst_perplotperyear\`, \`vst_mappingandtagging\` and \`vst_apparentindividual\` event records; verify **the same individualID within an explicitly remeasured, comparable plot**, with stable single-stem identity or an approved multi-stem linkage rule. Exclude unknown identities and heterogeneous stem measurement procedures **before** growth outcomes. Do not treat absence at followup as death without observing the design and statuses.
3. Crosswalk the predeclared five species \`129,316,802,833,837\` to *source-versioned scientific names*, not matching codes with NEON's taxonomy blindly. Preserve species absent from NEON as *unavailable*, not effect zero; do not choose favorable species after observing growth.
4. Compute source plot-level basal area per sampled area using effort, eligible stems and appropriate diameter methods. Align plot-survey years, forest conditions/management and actual local climate; avoid using the eventually surviving response cohort to define transductive density covariates.
5. Before estimating effects, freeze independent site/plot-group folds, minimum actual linked tree observations, source support, accuracy and practical-effect bounds; report *source unavailable* if insufficient. Distinct institution does not automatically guarantee that the ecological mechanism is identified.
6. Fit the previously developed stationary-versus-regional and within-site temporal BA hypotheses *only after the prospective data gate* and keep any unfavorable effects. **Observational replication still cannot show causal competition or physiological niche evolution.**

This metadata scan is a **one-shot source opportunity query**. It is not a routine source-monitoring task, does not require a token, and does not download raw tree tables. If the product API is blocked or its schema drifts, keep the error receipt and stop. Previous FIA exploratory negative and positive results are not reinterpreted.

## Alternative and its constraints

The Smithsonian ForestGEO SCBI forest-dynamics plot has repeated full censuses and publicly described disturbance histories, offering a different identity/management perspective. However, the official [ForestGEO data portal](https://ctfs.si.edu/datarequest/) requires project-specific data-use requests; the [SCBI terms](https://forestgeo.si.edu/explore-data/scbi-termsconditionsrequest-forms) prohibit unauthorized redistribution and can require PI collaboration. The presence of files on a public repository must not be assumed to waive those terms. SCBI is **one forest**, so it cannot alone confirm broad region-level driver turnover.

## Reproduce source-only catalog checks

\`\`\`bash
python -m pytest -q tests/test_fia_independent_neon_catalog_v1.py
python experiments/fia_independent_neon_catalog_v1.py --out-dir artifacts/neon_source_metadata_v1
\`\`\`

The one-shot GitHub workflow is triggered only by a uniquely named metadata-only lock. The artifact contains \`neon_release_2026_public_product_metadata.json\` (public metadata, not plant data) and \`neon_release_2026_source_gate.json\`; any authentication or upstream failure produces a STOP receipt, **never fabricated site counts**.

**Scientific target:** independently test whether local stand-density prediction information and within-site temporal density changes recur beyond the already-consumed FIA survivor cohort. **Current result:** feasibility of a separately sourced test is unproven until actual repeated individual and species/site overlap are verified. Do not claim otherwise.
