# Geographic driver turnover: independent tree-demography source eligibility v1

**Stage:** source-only, no empirical driver-switch or physiological niche-evolution inference. A new optional empirical programme, not Product A or Product B; original sealed terminal decisions and M5 manuscripts are not reopened.

## Core question

> Can *within-species* differences in tree growth and survival across regions be accounted for by a common environment–demography response, with dominant temperature-vs-water penalties changing because environmental opportunities differ? Or are distinct regional response functions required?

This is a *future* response-data question. The data source gate below intentionally opens no diameter, death, growth, or temperature-effect outcomes and cannot support the biological hypothesis on its own.

## Public primary candidates

1. **NEON Vegetation Structure** (`DP1.10098.001`, `RELEASE-2026`, DOI `10.48443/pypa-qf12`). NEON's `vst_apparentindividual` table includes per-event woody-plant status and diameter and `vst_mappingandtagging` carries taxon/individual identity; `vst_perplotperyear` supplies actual surveyed plot area. Within-event uniqueness is `eventID × individualID × tempStemID`; `tempStemID` is **not** a stable longitudinal stem ID for multi-stem individuals. NEON's product metadata (`/api/v0/products/...`) publicly lists sites and release months but is **not** proof of repeatedly measured individuals. As of June 2026, NEON requires a user account/API token for raw download. The gate makes one **anonymous data-access probe only**; neither a token nor credentials are requested/printed/stored, and an HTTP 401/403 is a clean `api_token_required` state.
2. **USDA Forest Inventory and Analysis (FIA)** publicly distributed raw FIADB DataMart archive tables, frozen initial states **RI, VA, WI**. The published `TREE` table carries `CN`, `PREV_TRE_CN`, `SPCD`, `INVYR`, `PLT_CN`; a same-species prior identity link with increasing inventory year is a *structurally linkable* tree pair. This is **not** a verified surviving individual or a growth/death event. The gate uses three independently downloaded state `*_TREE.zip` archives and never reads the `DIA`, `STATUSCD` or plot-level response columns. Actual FIA survey samples and measurement geometry require further audits before analysis. Coordinates in public FIA files are perturbed for landowner confidentiality; never interpret them as exact sites or disclose private plot locations.

## Exact eligibility rules fixed before opening tree response values

- Source region panel: `RI`, `VA`, `WI` (not selected by growth, mortality, or species-specific effects).
- Archive URLs and SHA-256, member name, byte counts and source errors are emitted for **every** state, without replacing unavailable archives with zeros.
- Join the current `TREE.CN` to older `TREE.PREV_TRE_CN` within state. Count only links where species code agrees and the `INVYR` increases; do not infer deaths from missing reobservations.
- Candidate taxon code: at least **30** strict linked-tree rows in each of at least **2** frozen states. This is a discovery eligibility count, **not** a claim of independent populations, demographic signal, confirmed species identity, or adequate climate overlap.
- Species codes must be crosswalked to source-versioned `REF_SPECIES` and source-checklist nomenclature in the next distinct step. `PLOT`, `COND`, actual sampled plot area and plot design strata must be joined and audited before fitting a demographic response.
- Avoid using public lat/lon at microhabitat precision. Pairing climate requires area-scale uncertainty and sensitivity to randomized FIA coordinates, and observed site/range environment overlap must be checked *before* any trait effect is opened.
- Missing prior links can reflect sampling/identifier limits and may **not** be classified as mortality. Even when linked, dead trees are valid response outcomes only if source `STATUSCD` and revisit design support the classification.

## Execution

```bash
python experiments/geographic_tree_demography_source_gate_v1.py --neon-only --cache artifacts --output artifacts/tree_neon_metadata_v1.json
python experiments/geographic_tree_demography_source_gate_v1.py --fia-only --cache artifacts --output artifacts/tree_fia_linkage_v1.json
python -m pytest -q tests/test_geographic_tree_demography_source_gate_v1.py
```

The GitHub Actions workflow stores **only count/metadata receipts**. It never commits raw tree specimen records or user tokens. The three source ZIP files remain ephemeral on the runner and are not uploaded. The FIA results are **new live DataMart snapshots** (not a DOI-frozen occurrence release); a later demographic programme must pin source SHA-256 and collection date and use the exact same archives.

## Required response study (separate, future freeze)

1. Crosswalk validated species and region/site geometry, fixed plot sampled area, tree DBH and status QC, revisit intervals and comparable growth stage, and adequate climate overlap; record every ineligible cohort.
2. Fix a causal **interpretation boundary**: measured growth and survival are demographic associations; they are not automatically individual fitness or fundamental physiological tolerance. Tree diameter change is not growth when measurement methods differ, and missing follow-up is not death.
3. Link site/year climate using independently collected meteorology and lagged moisture/temperature anomalies, and maintain plot, species, region and year effects. Use spatial groups and site-level resampling rather than treating individual trees as independent regional replicates.
4. Compare a **single common** temperature-water response to region-varying responses. Report full-model predictive adequacy, environmental common support, spatial/temporal transfer, and cluster-level uncertainty. Only then compare region-specific relative penalties conditional on the observed exposure distribution and measured response.
5. Use independent demographic/physiology experiments before interpreting residual region differences as evolutionary niche change.

Fail closed on access errors, insufficient repeated same-species observations or insufficient climate support. New taxon/covariate choices based on observed growth outcomes require a new preregistered independent confirmation sample.

## Authoritative sources

- NEON data product: https://data.neonscience.org/data-products/DP1.10098.001/RELEASE-2026
- NEON API product catalog: https://data.neonscience.org/data-api/endpoints/products/
- NEON API authenticated data access: https://data.neonscience.org/data-api/endpoints/data/
- USDA FIA DataMart: https://research.fs.usda.gov/products/dataandtools/fia-datamart
- FIESTA source demonstrates the public `state_TABLE.zip` DataMart pattern: https://rdrr.io/cran/FIESTA/src/R/DBgetCSV.R
- FIADB table identity definitions: https://research.fs.usda.gov/understory/forest-inventory-and-analysis-database-user-guide-nfi
