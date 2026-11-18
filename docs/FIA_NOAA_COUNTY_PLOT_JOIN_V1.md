# Source-only join of NOAA county climate to FIA exact PLOT revisit intervals

**State:** experimental source-geometry audit; no tree-response or climate-by-competition estimate.

This separately source-coherent stage uses the NOAA 2026-10-06 county archive frozen in `results/fia_noaa_county_climate_v1/` (43,890 paired growing-season county-months, 209 counties in RI, VA, WI), and only the **previous/current exact FIA PLOT identifiers**, publicly recorded county and field-measurement month/year, without reading the TREE or COND tables.

## Rules

- Every re-read FIA source ZIP must be byte-identical to `evidence/fia_plot_condition_source_v1.json` (source gate from the original FIA stand-context programme). No fallback to a newer ZIP or retuned study cohort.
- FIA `STATECD`, `COUNTYCD` form the actual FIPS state and 3-digit county suffix (44/51/55). NOAA source keys have **different state ordinals** (37/44/47) and have already been converted to FIA county FIPS at source opening. No coarse plot coordinates are used or reconstructed.
- The later `PLOT.PREV_PLT_CN` must resolve to the exact previous plot row. Retain only valid forward dates and the same declared county across the two dates. An unexplained county change, missing source row, absent climate month, truncated record or source SHA drift stays a counted exclusion. This is a study of source alignment, **not species abundance**, growth or detection.
- Climate during an interval is from **complete intervening April–September months only**, excluding both months of field measurement. A minimum six-month support is required; partial years are not extrapolated. Temperature is in °C and 6-month-equivalent precipitation is in mm. No measurement-year leakage is permitted.
- The output reports full PLOT-level denominators and eligible exposure **metadata counts**, not individual plot location/coordinate lists or linked tree responses. Study remains pre-response and descriptive.

## Limits and continuation

A successful source join provides climate-exposure coverage, but it does not supply the actual causal response. At least three limitations remain for any subsequent growth model: (i) **county** climate is not an exact microhabitat measurement; (ii) remeasured trees within a plot and state-year are not independent (cluster and survey weights required); (iii) only surviving trees have live→live growth and management/sampling may bias records. Climate×stand-density slopes require a separately fixed independent new TREE/PLOT/COND source with plot information available. Neither earlier SDMR Product A nor the primary M5 evidence is reclassified by this extension.

```bash
python -m pytest -q tests/test_fia_noaa_county_plot_source_v1.py
python experiments/fia_noaa_county_plot_source_v1.py \
  --fia-plot evidence/fia_plot_condition_source_v1.json \
  --climate-csv results/fia_noaa_county_climate_v1/noaa_county_growing_months_1991_2025.csv \
  --climate-receipt results/fia_noaa_county_climate_v1/source_receipt.json \
  --output artifacts/fia_noaa_county_plot_join_v1.json
```
