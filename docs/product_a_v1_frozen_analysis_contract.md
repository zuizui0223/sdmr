# Product-A v1 frozen analysis contract

**Status at commit time:** the DOI-backed `citable-product-a-v1` workflow had
started, but no focal-snapshot extraction result, protocol winner, stability
result, or promotion result had been observed. The choices below are therefore
recorded before the citable Product-A result is available.

## Source evidence

GBIF monthly occurrence snapshot:

- snapshot date: `2026-08-01`
- snapshot DOI: `10.15468/dl.fs3btq`
- GBIF download key: `0020258-260721160103020`
- snapshot `citation.txt` SHA-256:
  `022a524b59c4c037b28f252c08294e0f22c5eb7b3bce5c52a0a5fc6016f17050`
- frozen machine-readable contract: `configs/gbif_snapshot_v1.csv`

The DOI was parsed from the `citation.txt` stored beside the exact GBIF AWS
snapshot and cross-checked against DataCite. `sdmr-gbif-snapshot` independently
requires the supplied DOI to match that snapshot's `citation.txt` before a
Parquet scan begins.

## Product-A v1 taxon panel

Frozen file: `configs/product_a_pilot_taxa_v1.csv`.

Twelve predeclared plants span annual herb, deciduous tree, conifer,
wetland monocot, shrub, fern, arid shrub, mangrove, southern-temperate tree,
montane tree, boreal conifer, and wetland emergent strata.

Taxa are not to be dropped because they give inconvenient method results. A taxon
may be excluded only by the predeclared objective data-sufficiency/background
gates, with the exclusion retained in the ledger.

## Occurrence admission gate

Product-A v1 uses:

- minimum admitted occurrences/species: `80`
- minimum unique 0.05-degree cells/species: `50`
- grid size used for the sufficiency gate: `0.05` degrees
- no hidden 50/50 train/test requirement

Within each admitted species, `20%` of spatial blocks are sealed as the
answer-check set. Those blocks cannot influence any fitting, predictor/universe
selection, regularization, stopping, M/background selection, or protocol choice.

## Unseen-taxon barrier

- taxon validation fraction: `0.25`
- Product-A v1 split seed: `20260814`

Discovery taxa choose the complete protocol. Validation taxa do not participate
in that choice and test only the already-frozen winner.

## Accessible-area / background grid

Frozen file: `configs/product_a_buffer_specs_v1.csv`.

Competing M/background specifications:

1. occurrence buffer 150 km;
2. occurrence buffer 300 km;
3. occurrence buffer 500 km.

Each requests up to 2,000 target-group background cells at 0.05-degree cell
resolution. All M specifications must use the exact same admitted occurrence
evidence.

The target-group sampling frame comes from `Plantae` records in the **same GBIF
monthly snapshot**. For cloud I/O only, the query is prefiltered to occupied
5-degree focal tiles plus a conservative distance-aware 500 km buffer and is
compressed to one deterministic target-group record per 0.05-degree cell. The
biological M is still applied downstream by haversine occurrence buffers.

## Environmental candidate universe

Frozen file: `configs/chelsa_v2_1_plant_candidates.csv`.

The active manifest currently contains 43 predictors. Every active remote COG
must pass metadata-open preflight before Product-A evidence is admitted.

Three nested candidate universes compete:

1. `bioclim19`;
2. `chelsa_bioclim`;
3. `active_all`.

No larger universe is assumed to be superior.

## Predictor/model strategies

Within every data specification and candidate universe, three predeclared
predictor strategies compete:

- `all`;
- iterative `vif` baseline;
- `predictive` forward selection using inner spatial CV.

Model complexity and regularization are tuned only inside the model pool. The
sealed occurrence set is opened only after candidate protocols are frozen.

## Product-A v1 output

Discovery taxa choose exactly one full protocol:

`M/background specification × candidate universe × predictor strategy × model-complexity rule`.

The selected full protocol is then evaluated on unseen validation taxa.
`product_a_protocol_choice.txt` and the citable contract retain the selected
components and evidence fingerprints.

A single Product-A v1 winner is **not** method promotion.

## Frozen-evidence stability plan

After one successful citable Product-A v1 artifact, stability reuses its exact
occurrence/background/CHELSA feature tables and the exact Product-A source code
commit. No GBIF or CHELSA data are re-fetched.

Predeclared stability grid:

- seeds: `11,22,33,44,55`
- sealed fractions: `0.15,0.20,0.30`
- unseen-taxon fraction: `0.25`
- total repeated protocol-selection runs: `15`
- random predictor null repeats during stability: `0` because those nulls do not
  enter protocol selection or promotion criteria.

## Product-A promotion criteria v1

Frozen machine-readable file:
`configs/product_a_promotion_criteria_v1.csv`.

Promotion requires all of the following:

- identical full protocol selection fraction >= `2/3`;
- identical full protocol selected in at least `10` of the 15 runs;
- mean unseen-taxon paired presence-rank advantage >= `0.01` against each
  non-self strategy comparator;
- positive unseen-taxon paired fraction >= `2/3` against each non-self strategy
  comparator;
- at least `15` paired observations per required comparator;
- comparator set declared as `all,vif,predictive` (the selected strategy's self
  comparison is not applicable).

These are operational method-promotion thresholds, not ecological effect-size
claims. If they are not met, `promotion_not_met` is the intended scientific
result. Thresholds must not be relaxed after stability results are inspected.

## Product B boundary

Product B must not choose a method or candidate universe from its own driver
results. Only a Product-A protocol that passes the separate predeclared promotion
gate may become the frozen method input to the broad universal-driver analysis.
