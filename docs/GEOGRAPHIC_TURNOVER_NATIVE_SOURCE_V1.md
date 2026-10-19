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

## Executed 19 October 2026 — first public-data source receipts

GitHub Actions run `39217679310` completed source extraction; archive artifact `12171000234`. The raw (unmodified) source receipt and 25-km sampled environmental-cell file are preserved under `evidence/geographic_turnover_native_source_v1/` so the exact biological *non-claim* is auditable. CHELSA returned **187/187** finite BIO1+BIO12 raster cells across all four fixed rectangles. GBIF source query statuses (source window counts, not populations):

| Source rectangle | climate cells | GBIF focal indexed | full focal Search archive | accepted focal QC | matched 25-km cells | fixed sentinel archive status |
|---|---:|---:|---|---:|---:|---|
| *Quercus robur* DE | 30 | 329 | complete | 292 | 264 records | complete for all 3; sentinel cell coverage 30/30 |
| *Quercus robur* SE | 24 | 3,660 | complete | 3,650 | 3,310 records | complete for all 3; coverage 24/24 |
| *Pinus sylvestris* ES | 56 | 1,496 | complete | 537 | 529 records | complete for all 3; coverage 29/56 |
| *Pinus sylvestris* FI | 77 | 11,340 | **not fetched; exceeds prereported 4,000 cap** | unavailable | unavailable | *Sorbus* 5,582 exceeds cap; other 2 archives complete |

The 3/4 record archives are the **entire Search API result for that finite WKT×country×taxon×year query**, not a full GBIF global bulk download. GBIF record-level native versus planted origin is not known. `n_occ` zero was never inferred for *Pinus* Finland. The donor/source phenology mismatch (2010–2025 occurrences versus 1981–2010 long-term CHELSA climate) further bounds inference.

The reproducible rectangular opportunity audit (`experiments/geographic_turnover_opportunity_receipt_v1.py`) shows:

- *Quercus robur* source windows: Germany median BIO1 **8.45 °C** vs Sweden **6.55 °C**; raw temperature-range overlap **0.40 °C**; 6×6 pooled quantile climate-bin intersection **0.10**.
- *Pinus sylvestris* source windows: Spain median BIO1 **11.75 °C** vs Finland **3.65 °C**; **no overlap** in observed window BIO1 ranges (Spain 8.55–14.95 °C, Finland 2.75–4.55 °C). Bin overlap is coarse and should *not* be interpreted as literal axis intersection.

All values describe environmental **availability within arbitrarily fixed survey rectangles**, not sampled thermal niches or biological tolerances. The result proves that a strict cross-region common-thermal-support requirement would exclude the fixed *Pinus* ES/FI pair, even though both regions are in the species' native range. This is a concrete **source-geometry eligibility** result, not a test of evolution.

A **post-source diagnostic** was also run on the fully retrieved *Quercus* windows using the fixed three-sentinel plant record density as a candidate effort proxy. It returned **no observed direction reversal** of temperature-versus-moisture held-out information gain; raw contrast spread `0.10156 nats/record`, null median `0.44626`, uncalibrated bootstrap tail `1.0` (99 replicates). Because process ablations had negative held-out gains, the joint climate-bin overlap was only 0.10, and effort/wild-origin/M assumptions are not validated, this cannot support biological process constancy or reject a niche change. The result is **post-source, not confirmatory**, with all caveats in `results/geographic_turnover_quercus_real_postsource_v1.json`.

The single Finnish source capacity issue is pursued in a separately recorded, source-only `v1b` retrieval contract, **not** by changing the original v1 evidence or any ecological model after observing an effect. The v1b contract retains the exact original *Pinus* Finland rectangle and only raises the API finite-diagnostic retrieval cap to 15,000; the first v1 scientific conclusion remains `macro_inference_blocked=true`.

### Post-source observation-effort sensitivity (NOT a species driver finding)

The two fully retrieved *Quercus robur* rectangles were re-evaluated under **two post-outcome** observation assumptions, without changing occurrence records or climate cells: uniform recording offset (`q=1`) versus raw target-group counts (three sentinel plant species). Code and source-bound JSON: `experiments/geographic_turnover_quercus_effort_sensitivity_v1.py` and `results/geographic_turnover_quercus_effort_sensitivity_v1.json`.

| Rectangular source window | T minus moisture (uniform effort) | T minus moisture (sentinel-count offset) |
|---|---:|---:|
| Germany | −0.479 nats/record | +0.663 nats/record |
| Sweden | −0.223 nats/record | +0.561 nats/record |

The sign of the inferred relative process *information contrast* **flips in both source regions**, using identical focal data. Uniform-effort exploratory turnover tail `(B=99)` was `0.04`, versus `1.00` with sentinel-count offsets; both are post-source, uncalibrated, and **must not be interpreted as significant/no effect in a confirmatory study**. These two recording models are neither independent nor known to be correct, so this illustrates **observation-model dependence**, *not* a biological process switch. The result strengthens the priority of independently measuring collection effort and verifying non-focal control taxa before asking whether drivers genuinely turn over among native populations.

### Independently weighted climate-source comparison (descriptive, not habitat selection)

`experiments/geographic_turnover_source_weighted_climate_v1.py` compares three distributions with **unchanged CHELSA 25-km cells**: all predeclared available rectangles, admitted focal GBIF record counts, and independently retrieved three-plant target-group record counts. The completed 3/4 source windows retain their results; the incomplete Finnish window remains explicitly unavailable rather than being reclassified as zero. Frozen result: `results/geographic_turnover_source_weighted_climate_v1.json`.

The *Pinus sylvestris* Spanish source records were **1.337 °C colder and 210.4 mm/year wetter** than equal-area rectangle cells when weighted by focal observation counts. Compared with the *other three plant species' own source-record-weighted distribution*, the difference was only **0.215 °C colder and 66.6 mm/year wetter**. This attenuation is a concrete property of the two independent public-data assemblages; it cannot be attributed uniquely to observer bias because the sentinel species also have their own biological niche selection and possibly different detectability. Calling the remaining 66.6 mm an ecological water limitation would require a more defensible observation/availability model and independent ecological response data. This result is not evidence for warm-edge adaptation.
