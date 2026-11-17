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


## 2026-11-17 verified public catalog snapshot

The offline synthetic metadata contract [GitHub Actions #44034278473](https://github.com/zuizui0223/sdmr/actions/runs/44034278473) passed. The **one-shot public catalog acquisition**, [run #44034394812](https://github.com/zuizui0223/sdmr/actions/runs/44034394812), then completed **SUCCESS** and stored artifact [#14306711443](https://github.com/zuizui0223/sdmr/actions/runs/44034394812/artifacts/14306711443), ZIP SHA-256 \`178009f2f30a4d64a27b71549524e275780873febde747deb697503bde123238\`. It contains the complete PUBLIC product metadata (161,173 bytes, member SHA-256 \`0ba89ff5835ea54071e7a8f12f05b5ca928cec05a1dd424660727de4f94d9bcf\`) and derived source receipt (35,711 bytes, SHA-256 \`29699a799b5fc09411b952548f371b7f27545d4b0f73d479590576f63937021f\`). The raw product metadata's **canonical JSON** digest excluding a saved-file newline is \`22334f2b9c6bc42563a74996e6e540636cd2183857e37768bd1f1e0c4109b5ee\`.

**Actual response-blind, source-only result:** the \`RELEASE-2026\` product catalog reports **42** sites with at least one released month, **928** reported site-months, **39** sites with releases in ≥2 distinct years and **37** with a span ≥4 calendar years between the earliest and latest released years. The five below-four-year-span sites are \`CPER\` (2014–2017), \`DCFS\` (2015 only), \`LAJA\` (2016–2019), \`NOGP\` (2015 only) and \`WOOD\` (2014 only). **33/42** sites have 2024 as their latest released data year; the release label **2026 does not mean the most recent observation was taken in 2026**.

This is an **inventory of source-file availability, not an ecological or independent-individual result**. The metadata reveal **no** taxon crosswalk, stable tree remeasurement, plot survey design, mortality or growth values. Every repeated-individual tally remains \`unknown\` (JSON \`null\`), **not zero**. The independent NEON response test is **not run**, and no ecological effect claim is promoted.

A complete, source-identifiable [42-site checkpoint](../results/fia_independent_neon_public_catalog_checkpoint_v1.json) pins the site-year spans and the source/run/metadata SHA-256 values, while the Actions artifact retains the public source payload with every monthly record. A future file-access phase must verify the identity of repeated trees at each specific site and candidate year after a user-authorized API-token connection, not select sites by looking at growth outcomes.
