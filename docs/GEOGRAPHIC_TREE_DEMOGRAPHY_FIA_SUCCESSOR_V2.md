# FIA tree identity source: audit and versioned capacity successor

This **independent source-only** work follows the first public FIA source check, and is not a positive plant-demography outcome. Product A and M5 remain untouched.

## First observed source result (2026-10-19)

The raw, unmodified source metadata counts are in `evidence/geographic_tree_demography_source_gate_v1/fia_ri_va_wi_identity_linkages.json`, from GitHub Actions. The source identity profile requires matching `TREE.CN` to `PREV_TRE_CN`, same original `SPCD` string and increased `INVYR`. The source ZIPs are not committed.

| State | Data rows in downloaded tree table | Same-species, forward-year identity links | State download |
| --- | ---: | ---: | --- |
| RI | 23,307 | 10,112 | Complete, SHA-256 recorded |
| VA | 1,203,753 | 441,063 | Complete, SHA-256 recorded |
| WI | not fully read | unavailable | ZIP archive exceeded original declared 135-MB transfer cap |

Twenty-two distinct **raw FIA species codes** reach at least 30 identity links in both RI and VA. This says nothing about death, live growth, or the original environmental mechanisms. A `PREV_TRE_CN` link may include dead trees; it is not a growth success count.

## Exact next independent source checks

1. The USDA-hosted `FIADB_REFERENCE.zip` source is independently downloaded, SHA-256 preserved, and `REF_SPECIES.csv` used to map raw FIADB `SPCD` values to officially published scientific names. FIA numeric identifiers may be textual decimals (`'316.0'`): normalize with exact decimal arithmetic before matching, never hand-map the missing species. Unmatched names remain visibly unmatched.
2. The **unchanged Wisconsin source cohort** is read in a separately labelled runtime-size-cap successor with maximum ZIP bytes raised from 135 MB to **310 MB** (uncompressed table cap 3.5 GB). Neither the state panel, code-linkage definition, taxon threshold, nor response-data boundary changes. The original unavailable result remains authoritative for v1 and is not overwritten. The successor is not a fresh independent ecological replication.
3. Report status for each attempt, including errors and complete count denominators, not only eligible taxa. No growth, death, DBH or species performance is opened by either check.

## After data support is confirmed

A new response-eligibility contract must pin *named* species, regions, source ZIP SHA-256 and all requested tree/plot tables; then it should validate longitudinal `DIA` measurement compatibility, `STATUSCD`/tree observations, `PLOT`/`COND` survey design and geographic uncertainty. The primary estimand would be a within-species temperature–water effect on measured annual diameter increment and directly observed survival, with region, plot, tree size, taxon and sampling-date effects. A strict common-response versus region-varying-response comparison must happen **after** environmental common-support checks, using blocked site/plot validation. Presence-only driver rankings must not be substituted for demographic effects.

Official source: https://apps.fs.usda.gov/fia/datamart/CSV/FIADB_REFERENCE.zip , source pattern verified in https://rdrr.io/cran/FIESTA/src/R/DBgetCSV.R .
