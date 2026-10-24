# NOAA county climate source for FIA tree growth: independent pre-response opening

**Status:** source acquisition only. Climate exposure has not been linked to trees, plots, growth, mortality or density; no climate-by-competition parameter has been estimated. The closed SDMR Product A/M5 and blocked Product B are unchanged.

## Purpose

Prior source-frozen FIA evidence reported a pervasive **within-tree-species / state / initial-diameter / stand-age / source-physiography** negative association between prior forest basal area and survivor increment. The xeric/mesic moderation was variable, including across states. To investigate whether actual temporal warmth and precipitation anomalies modify the density-growth gradient, climate must be externally retrieved *before* biological effect modelling. Do not confuse `COND.PHYSCLCD` with actual measured drought.

### Source and identity boundary

- NOAA NCEI **nClimDiv county monthly** snapshot dated **October 6, 2026**, two fixed products: `climdiv-tmpccy-v1.0.0-20261006` (mean air temp, degrees Fahrenheit) and `climdiv-pcpncy-v1.0.0-20261006` (monthly rain, inches), via official NOAA current monthly archive URLs. No future or alternative file can be substituted after opening.
- **RI FIPS 44, VA 51, WI 55**. A `ccy` line's 11-digit identifier is **county FIPS5 + element2 + year4**, unlike `cst` state files that use NOAA's **distinct ordinal** state codes (RI 37, VA 44, WI 47). A code mismatch is a hard rejection.
- April–September climate months, 1991–2025; 1991–2020 climate baseline for later anomaly calculations. USDA `PLOT.STATECD` and `PLOT.COUNTYCD` are present in the source schema already archived in PR #284. County level avoids drawing fine-grid predictions from FIA's displaced and sometimes swapped public plot coordinates.
- Every NOAA source file is fully read and SHA-256 fingerprinted, parsed with duplicate/missing-value failure, and the full county-month denominator archived. Only years/counties with adequate source coverage are admitted. The frozen eligible universe is preserved, not optimized for observed tree growth.

## Planned estimand (not yet authorized)

For each exact previous/current FIA PLOT chain, join **county/month exposure from full intervening growing-season months only**, excluding both endpoint measurement months and rejecting unavailable months. We will not treat annual averages as exact plot microclimate. This time-varying, county-level variable may be correlated within plots/state-year, and is not a local temperature/water-stress measurement.

Then, on an **independently frozen, source-coherent version of FIA TREE/PLOT/COND**, test a *species-specific* growth–density slope whose coefficient may change with county-climate anomaly. Candidate terms include `density × growing_temperature_anomaly` and `density × growing_precipitation_anomaly`; a properly qualified model must use plot/tree cluster uncertainty, years/cycles and live-survivor selection checks. Statewide or county-climate sourcing without population sampling/cluster controls is insufficient for a causal competition/climate conclusion.

Do not refit the 2026-10-19 tree snapshot by replacing drifting USDA DataMart ZIPs. The new NOAA source does **not** supersede the original 2026-10-20 source-coherent observed 13-species response, and a numeric climate × competition result is **not** claimed here.

## Reproducibility

```bash
python -m pytest -q tests/test_fia_noaa_county_climate_source_v1.py
python experiments/fia_noaa_county_climate_source_v1.py \
  --config configs/fia_noaa_county_climate_source_v1.json \
  --out artifacts/fia_noaa_county_climate_v1
```

**Underlying source:** [NOAA nClimDiv archive](https://www.ncei.noaa.gov/monitoring-content/data/us/climdiv/monthly/current/) and [USDA FIA Spatial Data Services](https://research.fs.usda.gov/programs/fia/sds). The source record, not a physiological response, is the deliverable at this stage.
