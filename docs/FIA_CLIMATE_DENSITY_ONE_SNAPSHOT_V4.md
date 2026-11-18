# One-run, source-frozen FIA × NOAA climate and forest crowding (v4)

**Status:** first exploratory measured-outcome attempt on an independent **contemporaneous source snapshot**. The original FIADB DataMart state CSV ZIPs are mutable: a separately pinned PLOT v2 accession was byte-identical on 2026-10-24 but differed in **all three states** on 2026-10-28. The source-only [v3 gate](https://github.com/zuizui0223/sdmr/actions/runs/40541240798) therefore correctly blocked **3/3** before reading TREE STATUSCD or DIA; no growth conclusion was attempted on the v3 cohort. Do not lower a missing-data threshold or rewrite a historical receipt.

## Why v4 is a new cohort, not an opportunistic repair

v4 uses a **single Actions job**, with **all 9 current TREE/PLOT/COND ZIPs read exactly once** from RI, VA and WI. The two immutable NOAA inputs are the already-archived **2026-10-06** source receipt and 43,890 county×month rows for 209 counties. The study's **fixed** universe, model family, no-outcome source gate and minimum statistical support are predeclared in this Git commit **before running the new job**. No species/state/era is added based on observed tree growth.

Phase A: fetch PLOT, COND and TREE into one temporary immutable working directory. Calculate ZIP SHA-256 and verify each table's schema. Read only PREV_TRE_CN→CN, SPCD, PLT_CN, CONDID, INVYR identities for all 13 frozen species. No DIA or STATUSCD is accessed. Generate NOAA 1991–2025 county-interval climate availability and natural forest condition context (stand age, BALIVE) eligibility; write and preserve a source-only receipt **before** opening outcome columns. If any state fails, stop without modeling any partial subset.

Phase B: open DIA and STATUSCD **only from the locally retained, SHA-reverified ZIP byte sequences acquired in Phase A**. No new remote GET occurs after the source-only gate. Retain only same-species linked prior-live→current-live trees with valid matching diameter-height codes, prior and current natural forest condition, prior BALIVE and STDAGE, and a complete climate interval. Death, removals, nonobserved, missing diameter/date and incompatible measurement height are **not** zero-growth outcomes; keep separate exclusion denominators. Annualized growth is observed `log(DIA_current/DIA_prior) / exact measurement-month interval (years)`; samples are not expanded to population-weighted forest estimates.

## Predeclared first empirical estimand

For each of **13 taxa** separately, use the fixed family of four nested linear growth models:

1. **Baseline**: state intercepts, measured calendar year, interval length, log initial diameter, prior stand age and prior stand BALIVE.
2. **Climate**: baseline + county observed April–September mean temperature and precipitation anomalies relative to the same county's **1991–2020** NOAA baseline.
3. **Shared interaction**: climate model + (T anomaly × BALIVE) + (P anomaly × BALIVE), shared among all states.
4. **Region-dependent interaction**: shared interaction + VA/WI region-specific modifications to each of the two interactions (RI as reference).

The exact scaling is fixed as anomalies/3°C, precipitation anomalies/200 mm per 6 growing months and BALIVE/100 ft² per acre, with log diameter centered at 10 inches. State indicators and end-measurement calendar year are covariates; there is no claim of a linear physiological fitness curve. Model columns are rejected when the matrix is rank deficient. For each model calculate RMSE under **five deterministic, outcome-blind, entire-county holdouts** (not random tree splits). Do not estimate a species' model with fewer than 500 source-eligible live→live intervals, eight distinct NOAA climate counties, 25 unique plot revisits or without all three states. An inestimable taxon remains in the frozen denominator.

Primary diagnostics: RMSE reduction relative to baseline, incremental heldout RMSE gain of climate × BALIVE over climate-only, incremental heldout RMSE gain of region-specific modifications, raw coefficients and per-state climate ranges. None is a calibrated p-value, independent holdout validation or a physiological limiting-factor estimate. **No claim of climate-driven constraint switching, local adaptation or niche evolution is authorized.** This step tests whether the shared climatic-crowding response adds empirically predictive information in a **selected survivor cohort**, and whether a region-specific model improves the declared spatial holdout metric.

## Robustness and limitations

County precipitation/temperature cannot resolve plot microclimate, soil water, or temporally autocorrelated ecological drivers; FIA public coordinates are perturbed/swapped. Stand BALIVE is a competition proxy, not randomized, and may respond to site fertility, prior disturbance and forest management. Repeated trees and plots, state differences, observed-survivor selection, sample-design weights, age/nonlinearity and genetic provenance remain unadjusted. Five county holdouts within the same fixed states are not an independent prospective validation of a generalized ecological law. This is an **exploratory noncausal model comparison** and leaves the frozen Product A, blocked Product B, M5, and all earlier FIADB outcomes unchanged.

The source gate v3 diagnostic should continue to return its genuine zero-of-three SHA mismatch. v4 explicitly starts a **new fully source-pinned 9-ZIP family** instead of relabeling the earlier PLOT successor as identical.

## Reproduce / CI

```bash
python -m pytest -q tests/test_fia_climate_tree_source_gate_v3.py tests/test_fia_climate_density_growth_v1.py tests/test_fia_climate_density_one_snapshot_v4.py
python experiments/fia_climate_density_one_snapshot_v4.py \
 --noaa-csv results/fia_noaa_county_climate_v1/noaa_county_growing_months_1991_2025.csv \
 --noaa-receipt results/fia_noaa_county_climate_v1/source_receipt.json \
 --output-dir artifacts/fia_climate_density_snapshot_v4
```

The CI stores the **source-phase receipt and response separately** even on failure, and explicitly marks whether biological outcomes were opened. Reexecution from live DataMart may yield different ZIP SHA values; reproduce any claimed result only against the originally archived source SHA and first-run outcome receipt. Permanent scientific reproducibility still requires depositing a publicly accessible immutable version of the FIADB source or a suitably permissible derived dataset. The user should not be told that a SHA string itself preserves unavailable original bytes.
