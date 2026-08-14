# Citable Product-A evidence pipeline

SDMR separates pipeline debugging from scientific method evidence. A run should
move through the stages below without weakening the sealed-occurrence or
unseen-taxon information barriers.

## Stage 0 — diagnostic real-data smoke

`.github/workflows/real-api-smoke.yml` demonstrates that real GBIF occurrences,
real CHELSA COGs, target-group background construction, and the sealed Product-A
engine can execute end to end.

This stage is **not admissible for method promotion** because it deliberately uses:

- GBIF occurrence search rather than a DOI-backed download/snapshot;
- a small diagnostic CHELSA subset;
- focal-pilot taxa themselves as the target-group sampling frame.

Its only claim is pipeline operability.

## Stage 1 — DOI-backed citable Product-A pilot

`.github/workflows/citable-product-a-pilot.yml` is a manual `workflow_dispatch`
run. The caller must supply the exact GBIF monthly snapshot date and DOI.
SDMR does not guess or silently substitute a current DOI.

The pilot freezes:

- `configs/product_a_pilot_taxa_v1.csv` — predeclared 12-species method panel;
- `configs/product_a_buffer_specs_v1.csv` — 150, 300, and 500 km accessible-area
  buffer sensitivity grid;
- `configs/chelsa_v2_1_plant_candidates.csv` — active environmental candidate
  universe;
- the requested occurrence/taxon holdout fractions and random seed.

### 1. CHELSA preflight

Every active raster is metadata-opened before expensive data work begins. One
failed URI fails the pilot. The probe ledger is retained in the artifact.

### 2. Focal occurrence snapshot

The 12 focal species are materialized from the declared GBIF monthly cloud
snapshot. Snapshot date, DOI, query hash, local subset hash, and row count are
retained.

### 3. Broader target-group sampling frame

The same monthly snapshot is queried for `Plantae`, not just the focal species.
For widespread focal taxa, the cloud prefilter uses only occupied 5-degree tiles
plus a conservative 500 km buffer rather than one species-wide bounding box.
The km buffer expands longitude more strongly toward the poles so a downstream
500 km haversine M is not clipped by the rectangular cloud prefilter.

The target-group subset is compressed in DuckDB to one deterministic GBIF row
per 0.05-degree cell. This is an I/O optimization consistent with the downstream
background rule, which also gives at most one target-group candidate per climate
cell before sampling. It is not focal-occurrence thinning.

### 4. Matched Product-A protocol grid

`sdmr-pilot-grid` holds occurrence admission fixed and compares:

- M/background specification: 150 / 300 / 500 km buffer;
- candidate universe: BIOCLIM19 / broader CHELSA-bioclim / active-all;
- predictor strategy: all / VIF baseline / predictive selection;
- model regularization and response complexity inside the model pool.

All M specifications share the same admitted occurrence evidence. CHELSA values
for occurrences and all background specifications are extracted jointly, so each
remote raster is opened once; the tables are split back afterward without
changing values or row order.

The selected protocol is chosen using discovery taxa only and then evaluated on
unseen validation taxa. `product_a_protocol_choice.txt` records the selected
components and evidence fingerprints.

### 5. Citable contract

The artifact contains `citable_snapshot_contract.json`, the original focal and
target-group snapshot provenance, the CHELSA probe ledger, the frozen grid and
analysis outputs, and `CITABLE_PILOT_BOUNDARY.txt`.

A successful Stage-1 run is eligible Product-A pilot evidence, but a single seed
and holdout fraction are not enough for method promotion.

## Stage 2 — stability on exactly the same feature evidence

`.github/workflows/citable-product-a-stability.yml` takes the GitHub Actions run
ID of a successful Stage-1 pilot. It downloads that artifact and refuses sources
without the DOI-backed snapshot contract or a successful CHELSA preflight.

It then runs `sdmr-protocol-stability` over predeclared repeated seeds and sealed
fractions. No new GBIF or CHELSA data are fetched. Therefore any change in the
winner is attributable to validation partition sensitivity, not to a changed
data snapshot or environmental extraction.

Default stability grid:

- seeds: 11, 22, 33, 44, 55;
- sealed fractions: 0.15, 0.20, 0.30;
- unseen-taxon fraction: 0.25.

These defaults are operational starting points, not universal scientific
thresholds; the exact submitted values are stored in the stability artifact.

## Stage 3 — explicit promotion assessment

`sdmr-promote-protocol` is intentionally separate. It has no hidden scientific
cutoffs. The caller must declare all requirements, including protocol-selection
stability, minimum repeated runs, mean paired validation improvement, positive
pair fraction, pair count, and required comparators.

If the criteria are not met, `promotion_not_met.txt` is the correct result. The
method should not be promoted by relaxing criteria after seeing the result.

Only a protocol that passes a predeclared Stage-3 assessment should become the
frozen Product-A input to broad Product-B universal-driver analysis.
