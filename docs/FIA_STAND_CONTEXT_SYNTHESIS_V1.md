# FIA growth after actual measurement dates and stand-age matching — independent source-version audit

**2026-10-21 / exploratory demographic result, not climate causality or niche evolution.** This is a new, explicitly distinguishable source lineage from the previously frozen first-response TREES in PR #284. The previous archived 308,181-pair result is preserved, not overwritten or 'corrected' by importing newer USDA source bytes.

## Source proof and full denominator

1. An independent [GitHub Actions PLOT/COND source gate](https://github.com/zuizui0223/sdmr/actions/runs/39454801553) retrieved PLOT and COND for the same predeclared RI, VA, WI states, with **3/3 complete** sources and byte SHA receipts. It found 133,582 PLOT rows, 56,849 with `INVYR != MEASYEAR`, and 84,700 forest conditions with valid `STDAGE`. Inventory year and actual measurement year are different objects.
2. The [new-source TREE × PLOT × COND execution](https://github.com/zuizui0223/sdmr/actions/runs/39456209416) first verified all six PLOT/COND ZIP hashes against `evidence/fia_plot_condition_source_v1.json`, then opened *current* TREE ZIPs for the unchanged **13 species × three states**. The new TREE ZIP hashes are all declared; they differ from original first-response source hashes and **the datasets must not be pooled as one sample**.
3. The exact source-derived, aggregate-only result is preserved at `evidence/fia_new_source_stand_context_v1/aggregate.json` (SHA-256 `60de80f5b41a8eed94d13032a8176b857bc509017ace99ffa3ba4815cc2c8016`). It is a new exploratory outcome, not an independent confirmation, and its original raw TREE/PLOT/COND ZIP files are not bundled in the repository. The same historical source bytes may become unavailable if upstream releases mutate; preserve the limitation.

## Actual observations

Among same-tree links with valid measured dates and live→live diameter measurements on a newly source-coherent dataset:

| State | Confirmed diameter pairs | Subset with forest condition natural at both times and valid prior stand age |
|---|---:|---:|
| RI | 5,190 | 5,187 |
| VA | 100,105 | 93,166 |
| WI | 202,802 | 197,038 |
| **Total** | **308,097** | **295,391** |

Measured intervals are from `PLOT.MEASYEAR+(PLOT.MEASMON-0.5)/12` (mid-month approximation), following two independent chains (`TREE.PREV_TRE_CN` and `PLOT.PREV_PLT_CN`); **not** tree-only `INVYR` differences. The earlier-source total 308,181 is not a matched paired denominator for the new measurements.

### Size + prior stand age direct standardization

The new source predefines four prior-DIA bands (1–<5, 5–<10, 10–<20, ≥20 inches) and three prior stand age bands (0–<40, 40–<80, ≥80 years). Natural forest conditions at both visits are required. A cell qualifies only with at least 10 observed live→live pairs in **every state**. A single species' common cell weights are proportional to its pooled available survivor pair counts. This is **not FIA design-weighted forest demography**, not estimated growth of all stems, and cannot remove survivor selection or plot clustering.

| Species | Shared size×age cells | RI mean log DBH/y | VA | WI | WI > RI |
|---|---:|---:|---:|---:|---|
| *Juniperus virginiana* | 1 | 0.00346 | 0.00952 | 0.00975 | Yes |
| *Pinus strobus* | 10 | 0.01797 | 0.01871 | 0.02321 | Yes |
| *Tsuga canadensis* | 4 | 0.00984 | 0.00863 | 0.01086 | Yes |
| *Acer rubrum* | 9 | 0.00959 | 0.01163 | 0.01611 | Yes |
| *Acer saccharum* | 2 | 0.00896 | 0.01419 | 0.01280 | Yes |
| *Betula alleghaniensis* | 7 | 0.00945 | 0.00972 | 0.01210 | Yes |
| *Fagus grandifolia* | 3 | 0.02970 | 0.01856 | 0.01877 | **No** |
| *Fraxinus americana* | 3 | 0.00662 | 0.01220 | 0.01550 | Yes |
| *Populus grandidentata* | 1 | 0.00898 | 0.01027 | 0.01175 | Yes |
| *Prunus serotina* | 1 | 0.00695 | 0.01052 | 0.01065 | Yes |
| *Quercus alba* | 7 | 0.00740 | 0.01013 | 0.01002 | Yes |
| *Quercus rubra* | 8 | 0.01264 | 0.01339 | 0.01596 | Yes |
| *Quercus velutina* | 5 | 0.00924 | 0.01049 | 0.01319 | Yes |

**Primary descriptive counts:** 12/13 species show WI > RI on this survivor-cohort standardization, with 53/61 shared size×age cells in that direction. Nine of 13 have strict RI < VA < WI. All 13 species retained the same WI-vs-RI direction when inventory-year versus actual measurement-month denominators were contrasted **on the same new-source pairs**. This is a useful exclusion of one simplistic time-normalization explanation, **not** proof of a bioclimatic or physiological cause.

### Threshold sensitivity (post-outcome diagnostics)

| Minimum observed survivor pairs **per stratum in each state** | Estimable species | WI > RI | Positive size×age cells |
|---|---:|---:|---:|
| 10 (primary predeclared) | 13 | 12 | 53/61 |
| 20 | 10 | 8 | 37/42 |
| 30 | 7 | 6 | 24/27 |
| 50 | 6 | 6 | 19/21 |
| 100 | 5 | 5 | 14/15 |

These sensitivity counts are **not independent inferential replications**. Increasing the minimum changes which species and cells are estimable; it does not prove the biological result becomes stronger as the threshold increases.

## What this adds to ecology, and what it does not

The nontrivial *observed* finding is that geographically structured variation in growth of the **same species** can remain among repeat-surviving trees even after restricting to natural-forest stand conditions, correcting elapsed measurement year, and matching available size × stand-age categories. This reduces two classes of purely compositional explanation in this cohort.

It does **not** identify the limiting ecological process. Remaining confounders include differential sampling inclusion and detection, conditioning on survival, stand-density and competition, site quality, disturbances and management within nominally natural stands, phylogenetic dependence, regional climate and weather history, inaccurate public FIA geographic coordinates, different tree sampling ages and non-independent tree/plot replicates. The difference is conditional on *observed surviving, remeasured trees*, not an FIA population estimate. Uncertainty is not estimated at the plot level and no population confidence interval or hypothesis p-value is claimed.

**Next test:** within-plot structural/competition covariates (basal area / density) and independent temporal moisture/heat anomalies on a single source-consistent remeasurement panel, then held-out plots with matched climatic support and site-specific observation/effort diagnostics. Only independently anchored growth/survival curves can test the proposed invariant-niche versus local environmental-response-change alternatives. Product A/M5 remain closed; Product B remains blocked.

## Reproduce from original source-derived archive (no network)

```bash
python -m pytest -q tests/test_fia_stand_context_synthesis_v1.py
python experiments/fia_stand_context_synthesis_v1.py \
  --input evidence/fia_new_source_stand_context_v1/aggregate.json \
  --output results/fia_new_source_stand_context_synthesis_v1.json
```

A source-nonreacquisition CI checks the JSON source hash, 13 taxon × state denominators, common strata, and output identity. The previous external TREE × PLOT × COND acquisition is retained as a **manual-only historical replay** because USDA DataMart state ZIPs may change.
