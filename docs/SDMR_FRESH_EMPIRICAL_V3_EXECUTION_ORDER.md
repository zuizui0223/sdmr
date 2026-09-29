# SDMR fresh v3 execution order

The v3 fresh empirical programme now has two separately frozen selection layers.

## Layer 1 — candidate roster

From the same GBIF 2026-08-01 metadata universe:

- exclude all historical Product-A taxa/candidates;
- exclude all 50 taxa consumed by the first fresh empirical programme;
- require >=500 occurrences and >=20 occupied 1-degree cells;
- retain one species per genus and at most two per family;
- rank with the frozen v3 SHA-256 seed;
- freeze exactly **80 candidates**.

No environmental value or SoilGrids support bit is used to rank these 80.

## Layer 2 — SoilGrids support eligibility

For all 80 candidates:

- freeze the same coordinate-only outer split;
- construct the same model-pool-only 300-km target-group background;
- inspect only finite/missing support for the four frozen SoilGrids topsoil layers;
- never persist raw soil values;
- never inspect answer-check support.

Candidates passing the unchanged v2 complete-case availability thresholds remain eligible.

The first 50 support-eligible taxa in the already frozen candidate rank become the final cohort.

Fewer than 50 eligible taxa closes v3 unavailable.

## Why this is not outcome-adaptive replacement

The candidate denominator, ranking, support mask, thresholds and final-selection rule are all frozen before any v3 candidate support is opened. The support bit is a source-availability criterion, not model performance or ecological response.
