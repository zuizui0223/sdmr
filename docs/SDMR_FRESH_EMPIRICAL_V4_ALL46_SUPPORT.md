# SDMR fresh empirical v4 — all-46 support eligibility

Status: **design frozen before candidate selection**

v3 is not rescued. It remains terminally unavailable at the feature gate: 48/50 taxa passed the frozen complete-case rule, while two taxa failed model-pool retention. No answer-check data were opened and no model was fitted.

v4 therefore starts an independent fresh cohort.

## Frozen order

1. Exclude all 214 previously touched taxa: 84 historical Product-A taxa/candidates, 50 v2 taxa, and all 80 v3 candidate-roster taxa.
2. Select exactly 90 new Tracheophyta candidates from GBIF metadata only, under the same occurrence/QC and taxonomic-breadth rules.
3. Freeze occurrence identities, coordinate-only outer splits, and model-pool-only 300-km backgrounds for all 90 candidates.
4. Before choosing the final 50, evaluate **usable support across all 46 frozen predictors**.
5. Persist only finite/usable support bits and candidate-level support counts. Numeric environmental values are not retained at this stage.
6. A point counts as supported if every predictor is usable. For the six structural CHELSA states, “usable” includes the already-frozen deterministic structural decoding rules.
7. A candidate is eligible only if model-pool joint support is >=0.80 and >=50 rows, and at least 4000/5000 primary background rows have joint support.
8. Freeze the first 50 eligible taxa in the pre-existing candidate order. If fewer than 50 pass, v4 is terminally unavailable.
9. Only after final50 freeze may numeric predictor values be persisted.

The 90-candidate denominator is a planning choice, not a relaxed gate. At a conservative true eligibility probability of 0.65, P(at least 50 eligible of 90) = 0.97518.

No prior taxon is reused, no candidate may be reordered after support is read, and answer-check data remain sealed through cohort construction.
