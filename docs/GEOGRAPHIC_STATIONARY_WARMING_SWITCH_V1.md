# Climate exposure can switch the dominant modeled pressure without niche evolution

**Status (2026-10-19):** exploratory theoretical sensitivity under **one fixed illustrative environmental response**, applied to 571 actual CHELSA climate cells from 10 windows. These are *not species-measured fitness coefficients*. No conclusion about real plant growth, survival, local adaptation or physiological niche evolution is licensed.

## Mechanism

For thermal exposure `T` and annual moisture proxy `P`, the *same model in all regions* is:

\[
L(T,P;\delta)=\left((T+\delta-9)/3\right)^2+\left((P-900)/250\right)^2.
\]

`delta` is a **hypothetical additive warming shift in °C**, not a climate projection. The plant is postulated to have identical optima and sensitivities everywhere. For a region of equal-area climate cells, the dominant *modelled* stress contribution is given by the sign of the difference of average thermal and moisture terms. Uniform warming changes only temperature input; no physiology changes.

Because the thermal part is quadratic in `delta`, critical warming for equal-area pressure switching is obtained analytically from

\[
\delta^2+2\overline{(T-9)}\delta +\overline{(T-9)^2}-9\overline{((P-900)/250)^2}=0.
\]

Only positive, sign-changing roots within 0–6 °C are reported. A distinct optional hypothetical occupancy mechanism weights all climate cells by `exp(-L)` at each `delta`, conserving the same fitness curve while allowing location sorting. The sorted-pressure boundaries depend on `delta` through the weights and are found numerically. They are not the same estimand as equal-area means and cannot reuse exact equal-area roots.

## Source-grounded model counterexamples

The inputs are true CHELSA v2.1 BIO1/BIO12 normals at 571 predeclared equal-area cells, archived at `results/geographic_turnover_common_support_v1/all_candidate_climate_cells.csv` with SHA-256 `4b7d5bb9a23e3ef6c4c74448698409be4174d9199765d3ba7bd4eb4f9eddb633`. Zero GBIF occurrences or observation-effort weights enter this theoretical analysis.

| Geography label (not measured population) | Equal-area model switch threshold | Hypothetical habitat-sorted threshold | Interpretation |
|---|---:|---:|---|
| *Quercus* northeast France | **+0.832 °C** | **+0.537 °C** | Modelled moisture pressure becomes thermal as the fixed temperature optimum is exceeded |
| *Quercus* southwest Germany | **+2.083 °C** | **+0.573 °C** | Habitat-sorting assumption changes the timing substantially |
| *Pinus* northeast Germany | **+3.289 °C** | **+3.223 °C** | Same stationary response, later hypothetical switch |
| *Pinus* southern Sweden | **+0.427, +3.889 °C** | **+0.754, +3.681 °C** | **Two** crossings: initially thermal → moisture → thermal, without changing tolerances |
| *Pinus* northeast France | **+2.751 °C** | **none in 0–6 °C** | Habitat sorting can erase an equal-area pressure crossing |

All ten regions are archived, including those with no crossing. These thresholds rely entirely on the **illustrative** optima `(9 °C, 900 mm)` and scales `(3 °C, 250 mm)` inherited from the earlier stationarity counterexample. They are neither species predictions nor evidence of future adaptation.

## Ecological implication as a falsifiable hypothesis

**The environmental factor responsible for the greatest mean fitness penalty can change across sites or over climate forcing even while the species' response function is conserved.** The sequence of dominant pressures can be nonmonotonic: in environments colder than a postulated optimum, warming can *reduce* thermal penalty before later heat exposure increases it, allowing thermal → water → thermal sequences. Spatial habitat choice can shift or suppress a crossing.

This is stronger mechanistically than reporting correlated raster rankings: the prediction concerns independently measurable **fitness-component losses**. To support it in real plants, estimate stress-performance curves from plot-based repeated growth/survival observations and documented sampling area/effort. Test if independently measured performance at equal temperature/moisture states agrees across regions, and whether one stationary response predicts the observed switching pressure under regional environmental availability. Do not use CHELSA annual precipitation as if it were measured plant water stress; an independently justified physiological water-balance representation is required.

## Reproduce

```bash
python experiments/geographic_stationary_warming_switch_v1.py \
  --source results/geographic_turnover_common_support_v1/all_candidate_climate_cells.csv \
  --output results/geographic_stationary_warming_switch_v1.json
python -m pytest -q tests/test_geographic_stationary_warming_switch_v1.py
```

Complete deterministic result and its SHA-locked source are in `results/geographic_stationary_warming_switch_v1.json`. This is a **post-source analysis** and must never be counted as the positive empirical result of the climate-matching or original SDMR/M5 programmes.
