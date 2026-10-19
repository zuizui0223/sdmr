# Real-world source/geometry preflight for a new driver-turnover macro programme

**Scientific status:** source and environmental opportunity diagnostics only (new exploratory design). No estimate of niche evolution, physiological limitation, ecological process attribution, or cross-species turnover is authorized. The closed SDMR Product-A v2.8.4 and blocked Product B remain unchanged.

## Fixed pilot before observations

The purpose of this source gate is to determine whether regional observation records and complete environmental *availability* cells can be assembled without choosing the regions or accessible area on the basis of the focal distribution. Two native European species are considered as a structural pilot, not a representative taxon sample:

- *Quercus robur*: Germany (9.0–10.5°E, 50.5–52.0°N) versus southern Sweden (13.0–14.5°E, 56.5–58.0°N). Kew POWO accepted-taxon native range: https://powo.science.kew.org/taxon/urn:lsid:ipni.org:names:304293-2 .
- *Pinus sylvestris*: central Spain (−4.5–−2.5°E, 40.5–42.5°N) versus central Finland (23.0–26.0°E, 61.0–64.0°N). Kew POWO accepted-taxon native range: https://powo.science.kew.org/taxon/urn:lsid:ipni.org:names:263353-1 .

Geographic rectangles are **not** established biologically accessible areas (`M`), nor equivalently sampled ecological regions. The national native-range label does not guarantee that any *individual* occurrence was a self-sustaining wild population; possible plantings remain in the unresolved ledger.

## Actual sources and hard source ceilings

1. Generate 25-km EPSG:6933 equal-area grid cell centres before reading any focal occurrences. Spatial grouping uses four exogenous quadrants of grid indices. Retain every generated cell, irrespective of whether the focal species was recorded. These rectangles still require an independently justified `M` before process inference.
2. Request CHELSA v2.1 1981–2010 BIO1 (temperature) and BIO12 (precipitation) for every grid centre through the current SDMR COG-resolution/extraction functions. Archive raw sampled values and raster metadata with every source result. Values are not silently converted into degrees or precipitation units: transformation/scales must be verified from source metadata before ecological comparisons.
3. Use GBIF CoL-XR v2 taxon matching and the GBIF v1 occurrence-search API **only for this bounded diagnostic**, with independently fixed rectangle WKT, country, years 2010–2025, presence and geospatial flags. A 1-row query obtains the indexed source count; no ecological model is fitted from a counted-record total. Only when the total is ≤4,000 are *all* results fetched. Search truncation is a non-availability state, never a random sample or a valid source receipt. An actual final macro analysis requires a pinned GBIF bulk download DOI and independent sources.
4. Focal occurrence QC explicitly rejects duplicate/missing `gbifID`, disallowed basis, nonmatching taxon, missing/nonfinite coordinate uncertainty, uncertainty >1,000 m, and out-of-range coordinates. Do **not** treat missing uncertainty as zero. Counts are aggregated to exogenously generated climate cells; no centroid or clipping is learned from focal points.
5. Independently query *Betula pendula*, *Salix caprea*, and *Sorbus aucuparia* as a fixed **target-group source coverage diagnostic**. If every sentinel source was fully retrieved, count sentinel GBIF records by climate cell and report the fraction of cells with any sentinel evidence. Zero sentinel counts are not replaced by an arbitrary pseudo-count. This proxy is neither a validated sampling-effort intensity nor demonstrably taxon-neutral. It is explicitly blocked from ecological model inference.

Failures of remote COG access, search completeness, taxonomic mapping, or source support are preserved in the same output ledger as successful windows. No window is substituted, dropped from its denominator, or expanded after inspecting occurrences.

## Recorded and unresolved outputs

- `source_receipt.json`: complete four-window denominator, source counts, complete-versus-truncated status, row QC ledger, CHELSA resolution metadata, cell-source coverage and `macro_inference_blocked=true`.
- `available_climate_cells.csv`: *all* finite CHELSA grid-cell centres and their preassigned geometry; where an entire focal source is complete, a diagnostic focal cell count; where all target-group sources are complete, independent sentinel record counts. There is **no** fitted suitability, occurrence probability, causal limiting process, or niche turnover score in this output.
- GitHub Actions: `.github/workflows/geographic-turnover-native-source-v1.yml`. The workflow explicitly installs optional geo dependencies, runs offline tests first, reads public sources once, and archives all success and failure evidence.

The finalized macro model requires a **separate prospectively frozen study** with defensible `M` for all native populations, independently calibrated observation effort, meaningful shared climatic support, whole-space holdout, location- and detection-aware inference, cross-species taxon eligibility, model class/effort sensitivity, and a strong stationarity null. In particular **a changing statistical importance of BIO1/BIO12 cannot by itself demonstrate a switch in biological limiting factors.**

## Execute

```sh
python -m pip install -e '.[test,geo]' pyproj scipy
pytest -q tests/test_geographic_turnover_native_windows_v1.py
python experiments/geographic_turnover_native_windows_v1.py \
  --config configs/geographic_turnover_native_windows_v1.json \
  --output-dir artifacts/geographic_turnover_native_windows_v1
```

This study's output cannot be added to the completed Product-A/M5 denominators or used to re-promote Product B.
