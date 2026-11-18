# NOAA county climate × FIA PLOT successor v2 — source-version-aware audit

**Status:** new PLOT-source-only eligibility audit, not a biological effect estimate. The old archival PLOT source is **not** reopened, relabeled or retroactively altered. This successor uses a separately observed set of 2026-10-24 DataMart ZIP hashes, without changing the 2026-10-06 NOAA county climate vintage.

## Motivation and source break

The original pre-response PLOT-to-NOAA county-climate join on GitHub Actions run [40074802488](https://github.com/zuizui0223/sdmr/actions/runs/40074802488) returned a **hard source identity stop in all three predeclared states**, because current USDA FIA PLOT archive bytes no longer match the ZIP hashes frozen during the earlier independent PLOT/COND gate. `results/fia_noaa_county_climate_v1/original_plot_source_stop.json` retains every expected/observed SHA-256 and `n_states_join_complete=0`. The corresponding completed NOAA source has 209 counties × 35 years × six growing-season months = 43,890 county-month records, in RI (5), VA (132), and WI (72), and is independently pinned by `source_receipt.json` and `noaa_county_growing_months_1991_2025.csv`.

The original source failure is **not** an absence of FIA trees or NOAA climate. It prohibits combining archived 2026-10-20 tree-growth results with mismatched 2026-10-24 PLOT entries. This procedure does not attempt to obtain a favorable biological signal through source replacement.

## Successor rule

1. Read the **unaltered** original source-stop receipt; require all three RI/VA/WI rows to report `source_unavailable_or_changed`, different valid original and newly observed ZIP SHA-256 values, and zero admitted source joins and zero opened tree-growth responses.
2. Verify the already pinned NOAA county-climate bytes through `climate_csv_sha256`, full 43,890-row grain and original source receipt fingerprint. No climate axes, dates, geographies or taxa are selected on the basis of FIA growth outcomes.
3. Retrieve each currently distributed `RI_PLOT.zip`, `VA_PLOT.zip`, `WI_PLOT.zip` exactly once, **require the ZIP SHA-256 to equal the first newly observed hash** in the old stop receipt, and otherwise report `new_plot_source_changed_again_stop`. No retry with replacement states or loosened tests.
4. For each verified PLOT ZIP, enumerate repeated **plot IDs** via `CN` and `PREV_PLT_CN`, enforce matching FIA state+county FIPS and valid `MEASYEAR`/`MEASMON`, and require a complete April–September NOAA climate exposure strictly between the two measurement months, with >=6 observed months. No `TREE`, `DIA`, status, stand basal area or species responses may be read.
5. Archive a source-only output with full state-specific denominators and explicit failure reasons. All-three success establishes **metadata linkage feasibility only**; it does not license a climate × crowding growth model.

## Scientific boundary and required next data

The previous measured growth results are still based on a separate historical or subsequent source cohort. Before any empirical climate model is fit, independently freeze a **coherent, same-version TREE + PLOT + COND cohort** with `PLOT.STATECD/COUNTYCD`, `MEASYEAR/MEASMON`, `COND.BALIVE`, physiology site codes, plot identity, same-tree remeasurements, observation/design weights and plot-block holdout. County climate is area-averaged and does not measure local water stress or microclimate; public FIA plot positions are spatially perturbed, so county aggregation reduces but does not eliminate spatial uncertainty. The primary null should remain one shared species growth response and a declared region-varying competitor, with a positive-heldout-adequacy gate and balanced climate support. Only after confirming this eligibility can ecological effects be estimated.

Existing closed SDMR Product A/M5, blocked Product B, all prior FIA response aggregates and their hashes are unchanged.

## Run

```bash
python -m pytest -q tests/test_fia_noaa_county_plot_successor_v2.py
python experiments/fia_noaa_county_plot_successor_v2.py \
  --original-stop results/fia_noaa_county_climate_v1/original_plot_source_stop.json \
  --climate-csv results/fia_noaa_county_climate_v1/noaa_county_growing_months_1991_2025.csv \
  --climate-receipt results/fia_noaa_county_climate_v1/source_receipt.json \
  --output artifacts/fia_noaa_county_plot_successor_v2.json
```

The manual/prospective GitHub workflow will create a read-only source audit. Its result is a new version; never rewrite `original_plot_source_stop.json` in response to ZIP updates.
