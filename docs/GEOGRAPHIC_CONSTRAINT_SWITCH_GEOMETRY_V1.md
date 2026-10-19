# Geographic turnover of the *limiting* environmental axis need not involve niche evolution

**New theoretical & real-climate opportunity result, 19 October 2026.** This is a mechanistic *counterexample*, not an inferred wild-plant niche response. The separately closed Product-A and M5 studies are untouched. The four source rectangles and CHELSA raster cells are those from the existing PR #284 pre-outcome source archive; this hypothesis stress test and its illustrative physiological settings were specified **after source acquisition** and must not be called prospective confirmation.

## The ecological statement to test next

> Regional environmental constraints can switch from moisture-dominated to temperature-dominated **while every parameter of the organism's environmental response remains identical**. The switch can arise because the available environmental exposures differ, without local adaptation or a change in physiological tolerances.

This is a hypothesis about *regionally realized pressures*, not the statistical importance of a BIOCLIM raster. It differs from asserting that a coefficient or SDM variable rank changes. It identifies a concrete mechanism by which adaptation could be wrongly inferred from regional maps.

### Derivation, not an SDM estimator

For a stationary separable, hypothetical negative log-fitness penalty at climate cell `i`, write

\[
L_i = w_T\left|\frac{T_i-T_*}{s_T}\right|^p + w_W\left|\frac{P_i-P_*}{s_W}\right|^p,\quad p\in\{1,2\}.
\]

The parameters `T*`, `P*`, `sT`, `sW`, `wT`, and `wW` are *identical between regions*. They are **not estimated** from GBIF data. Define equal-area available-climate means:

\[
A_{T,r}=E_{M_r}|(T-T_*)/s_T|^p,\qquad A_{W,r}=E_{M_r}|(P-P_*)/s_W|^p.
\]

The larger expected loss component in region `r` is thermal precisely when the **fixed** physiological weight ratio `k=wT/wW` exceeds `h_r=A_{W,r}/A_{T,r}`. If two regions have different thresholds, any `k` strictly between the thresholds produces **different dominant components under one unchanged fitness function**. This is exact conditional algebra; it is not a p-value, an estimate of field fitness or proof of adaptation.

### First calculation on independently retrieved CHELSA raster values

We used the already archived equal-area CHELSA BIO1/BIO12 centres: Germany 30 and Sweden 24 for *Quercus robur*; Spain 56 and Finland 77 for *Pinus sylvestris* (187 total). Both pairs were chosen **before** original occurrence outcomes were acquired. For a purely illustrative shared `T*=9 °C`, `P*=900 mm/year`, `sT=3 °C`, `sW=250 mm/year`, and `k=1`, the same response yields:

| Source pair | Loss shape | Regional penalty ranking at k=1 | Exact k interval giving a switch |
|---|---|---|---|
| Quercus DE → SE | quadratic | moisture → temperature | (0.373, 4.120) |
| Quercus DE → SE | absolute | moisture → temperature | (0.479, 2.133) |
| Pinus ES → FI | quadratic | moisture → temperature | (0.198, 1.569) |
| Pinus ES → FI | absolute | moisture → temperature | (0.438, 1.289) |

The *temperature* availability range overlaps only **0.40 °C** between the Quercus rectangles and **0.00 °C** between the Pinus rectangles. This is a descriptive geographic feature, not a demonstrated climate-tolerance overlap.

To expose sensitivity rather than select one favorable optimum, a **post-source** Cartesian grid covers 17 temperature optima from 5 to 13 °C and nine precipitation optima from 700 to 1,100 mm in 50-mm steps, at the same fixed scales and `k=1`:

| Source pair | Quadratic hypothetical switch | Absolute hypothetical switch |
|---|---:|---:|
| Quercus DE–SE | 61/153 parameter combinations | 63/153 |
| Pinus ES–FI | 100/153 | 101/153 |

These counts are **not ecological frequencies or probabilities**: their fractions depend on the arbitrary illustrative grid. They demonstrate that the counterexample is not confined to a numerically unique choice of optima or response curvature. The exact threshold intervals, not these fractions, are the identifiable theoretical result under declared fitness-response parameters.

### Why actual plant data still do not identify this mechanism

No field-derived physiological optima, fitness curves, biomass, survival, demographic rates or true plant accessible area `M` are available for these taxa in this analysis. Country-native status does not establish each specimen's wild status. The GBIF occurrence and sentinel-effort columns are intentionally *never read by this calculation*. Thus the computed switches describe **environmental opportunity under a hypothetical fitness function**, not measured constraints faced by real trees.

The two Pinus rectangles have disjoint BIO1 intervals. Without independent physiological or demographic anchors, comparing responses in two disjoint thermal environments cannot identify whether an apparently changing response is due to regional niche evolution or interpolation/extrapolation of one stationary response. A global SDM may *assume* a shared smooth response, but its extrapolation does not verify that assumption.

### Falsification path for a genuine biological macro study

The biological version requires prospectively selected native, non-planted populations with both meaningful environmental contrast and genuine shared environmental support, independently measured survey effort/detection, and at least some measured demographic or physiological response. Measure species-level `T*`/`P*` or usable response constraints independently of the occurrence-only dataset. Then test whether the measured regional pressure ordering and spatial variation in growth/survival can be predicted by **one fixed response function** and each region's predeclared available exposure distribution. The informative alternative is a necessary change in the response function beyond what environment-only opportunity predicts.

The current real *Quercus* rank-contrast result in `docs/GEOGRAPHIC_TURNOVER_POSTSOURCE_AUDIT_V1.md` remains negative/nonconfirmatory: changing assumed collection effort can reverse predictor rankings, while full models fail adequacy under the declared primary spatial folds. It cannot be used as validation for these hypothetical pressure rankings.

## Reproduce

```bash
python experiments/geographic_constraint_switch_geometry_v1.py \
  --source evidence/geographic_turnover_native_source_v1/available_climate_cells.csv \
  --output results/geographic_constraint_switch_geometry_v1.json
python -m pytest -q tests/test_geographic_constraint_switch_geometry_v1.py
```

The input SHA-256 is frozen: `42747f07c030a09134a08703bf20e60a73fe661468c2047ccc1c1fd7628b85aa`. The script requires all 187 climate cells, verifies this SHA, and discards all `n_occ`, focal GBIF, and target-group source columns before calculation. The sensitivity and exact algebra are accompanied by seven tests. No new Product-A/B promotion, M5 gate, causal claim, or confirmatory biological conclusion follows.

### Does habitat selection itself erase the predicted switch?

An additional mechanistic check goes beyond averaging all available cells. Assume hypothetical organisms distribute among the predeclared equal-area cells proportionally to `exp(-L_i)` using **the identical fixed fitness function in both regions**. This changes the *model-implied* realized exposure while leaving physiology unaltered, with no focal occurrences or sentinel records used for weighting.

At the same illustrative `T*=9 °C`, `P*=900 mm`, `sT=3 °C`, `sW=250 mm`, and `k=1`, both the quadratic and absolute penalty models still give **moisture-dominated → temperature-dominated** expected exposure for the Quercus DE→SE and Pinus ES→FI source rectangles. Under the exploratory 153-optimum grid, this habitat-sorted switch occurs in **69/153 (quadratic), 70/153 (absolute)** choices for Quercus, and **104/153, 103/153** for Pinus. These are shape/parameter-grid sensitivity counts, not probabilities of biological transitions.

The exact critical-ratio intervals above apply to the **equal-area availability means**. When habitat sorting depends on `k`, the relative exposure distribution itself changes with `k`; those intervals **must not** be reused as exact thresholds for sorted-occupancy predictions. This check only verifies the sign of the model-implied pressure difference at the declared `k=1` and across the listed scenarios. A field test would need independently measured abundance, demographic performance and sampling effort to determine whether any tree populations actually sort this way.
