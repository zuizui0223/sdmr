# Geographic environmental-information turnover: independent macroecology lane (v0)

**Status: new exploratory analysis; no real-plant ecological outcome opened.**  This is **not** SDMR Product A / Product B re-promotion, and it does not amend the closed v2.8.4 or M5 decisions. It is also distinct from `turnover`'s trait/interaction memory project.

## Main biological question

> Can the environment that most strongly constrains a species' *realized* geographic occurrence switch between regions even when its underlying niche response is unchanged? How often do observed regional contrasts exceed the turnover expected from available environments and recording effort alone?

The important distinction is between (i) a **regional difference in evidence about environmental drivers**, (ii) a truly **active binding biological limit** under a fixed physiological response, and (iii) a **change in the response function**. Presence-only data directly identify at most (i) under an observation model. (ii) requires fitness, survival, reproduction or physiological performance information, and (iii) is not automatically evidence for *evolution* rather than plasticity, interactions or source bias.

## Hypotheses (do not equate them)

* **H0 — availability shadow:** one taxon-wide environmental response, but different region-specific accessible climates and recording efforts, produces apparent temperature–moisture driver-rank reversals. This is a genuine mathematical and ecological null, **not** evidence of local niche evolution.
* **H1 — extra nonstationarity:** the observed region-to-region contrast is larger than the distribution produced by H0 with the same accessible cells, effort and number of records. This can reject the *specified* invariant occurrence-intensity model, not establish physiological evolution.
* **H2 — interpretation bridge:** H1 excess co-occurs with within-environment overlap, independent native-range status, independently evaluated demographic responses and robust observation-process corrections. Only such independent evidence could support changed active limits or evolved/plastic niche shifts.

### Why "rank reversal" alone is not a discovery

Let region `r` contain available environmental cells `M_r`, temperature `T`, moisture `W` and detection/recording effort `q_rc`. Under the invariant response null,

`P_0(c | r, observed record) = q_rc exp[f(T_c,W_c)] / sum_{j in M_r} q_rj exp[f(T_j,W_j)]`.

The *same* `f` can yield different regional temperature/moisture knockout gains because `M_r` and `q_rc` differ. A rank reversal is only compelling if it **exceeds this conditional null** and remains estimable over *overlapping* environmental support. If the two regions occupy almost disjoint environments, different local functions may agree with a single global function on their observed support; non-rejection then says little about niche conservatism.

## Implemented v0 test (new code under `experiments/`)

Input is a **preconstructed, complete accessible-cell table**, with one row per taxon × region × environmental grid cell and columns:

| Column | Meaning |
|---|---|
| `taxon` | accepted, provenance-tracked species identifier |
| `region` | *a priori* independent ecoregion/geographic partition |
| `cell_id` | equal-area grid-cell identifier unique within taxon/region |
| `spatial_block` | geographically contiguous block fixed *before* inspecting response values |
| `temperature` | predeclared environmental axis, e.g. CHELSA BIO5 or BIO1 |
| `moisture` | predeclared water-balance axis, e.g. CMI or BIO12 |
| `effort` | positive **relative recording-effort density**, from independent target-group data within the declared accessibility frame; not an invented constant |
| `n_occ` | count of admitted, deduplicated presence records for that cell, may equal zero |

The analysis **does not** create `M`, ecological predictors, missing effort weights or climate regions. All three must be prepared and source-audited *before* running. In particular, a target-group point cloud must not be silently treated as all potentially available environment; no absence or detection probability is inferred from a missing GBIF record.

1. **Observed evidence:** for each taxon and region, fit a five-term quadratic temperature/moisture response using conditional multinomial occurrence intensity, controlling for `log(effort)`. The five terms are `T`, `T²`, `W`, `W²` and `T×W`. Estimate *spatially held-out* log-score gain per observed record when removing **the whole declared temperature or moisture closure** (both remove the shared interaction).
2. **Turnover statistic:** for each region, `C_r = gain_T,r − gain_W,r`. Report whether any regions have opposite signs exceeding a declared `minimum_contrast`, and the observed `spread = max_r C_r − min_r C_r` in nats/record. The gains can be negative under spatial transport; neither gain is a physiological limiting-strength estimate.
3. **Invariant-response null:** fit one shared species-specific response coefficient vector with region-specific conditional normalization, retaining all original available cells and effort. Generate exactly the original record total per region under that shared response. For every simulated world, refit **all** spatially held-out regional full/knockout models, with the same region and spatial-block partition. An observed rank reversal that is frequent under this null **is not a niche-shift result**.
4. **Inference:** use the prereported one-sided plug-in parametric-bootstrap tail `(1 + #null spreads >= observed spread)/(B+1)`. Report null median, 95th percentile and null reversal frequency. Coarse pairwise equal-cell binned overlap (`1 − total-variation distance`) is included as an **estimability diagnostic**, not a magically sufficient identifiability test.
5. **Integrity:** no input missingness, nonpositive effort or duplicate cell rows accepted. At least four blocks and adequate observed/test records are needed in each region. Simulated empty spatial folds abort the entire taxon instead of selectively discarding null replicates. Every excluded taxon is retained with an explicit reason. Taxon RNG streams are stable under species or row reordering. Raw input SHA256 is written to the CLI result receipt.

### Computational boundary

This is a **sensitivity design, not a validated significance-test family**. In particular, the fixed quadratic function class may not represent the biological suitability response; the fitted null does not propagate all model-selection or effort-estimation uncertainty; spatial blocks may have residual autocorrelation; two folds are insufficient for precise small-sample inference; coarse support overlap is sample-geometry dependent; choosing M using held-out presence would leak information. Any formal macroecological test needs pre-outcome simulation-based error calibration and independent environmental/effort source receipts. Never report v0 `p` as a valid causal or evolutionary test.

## Actual source acquisition and preregistration gates (not yet passed)

**Data to acquire:** versioned GBIF bulk plant occurrences (not 300-record Search API pilots), target-group records *not containing sealed focal answers*, 1981–2010 CHELSA v2.1 BIO1/BIO5 and a moisture axis, and published native/introduced regional range status. Existing `sdmr.data.gbif`, `sdmr.data.chelsa`, raster provenance and `island` GBIF occurrence inventory can assist; **none is by itself a complete accessible-cell/effort table**. Use GBIF record IDs, download DOI, checklist key, dataset keys, coordinate uncertainty, observation years and exclusion reasons as source receipts.

**Geometry before outcome:** define biogeographic regions independent of focal response (terrestrial ecoregions/biomes or established native regional units), an explicitly justified taxon-specific accessible area `M` with sensitivity M alternatives, equal-area cells and disjoint spatial blocks. Drop coastal/raster nodata cells by a documented rule. Keep introduced populations in a *separate predeclared stratum*, not mixed with native comparisons. Report native-range status uncertainty.

**Species eligibility:** at least two qualifying regions; ideally ≥3 for wider comparisons; each region has ≥4 nonempty environmental blocks, ≥50 independent spatially thinned occurrence records, and a sufficiently complete target-group effort surface. **These numbers are design candidates, not empirically promoted thresholds**; freeze them *before* final opening and retain all failures. Require demonstrable temperature/moisture variation and record measurement consistency. Environment distributions with negligible overlap cannot identify response change outside shared support.

**Negative controls:** (a) globally invariant surface simulated over actual observed regional environmental availability; (b) effort-only intensity; (c) shuffled region labels only within geographical/effort-matched strata; (d) known region-specific response under sufficiently overlapping availability. Calibrate type I error and positive recovery across M, effort misspecification, spatial autocorrelation, sampling intensity and learner capacity.

**Primary eventual macro estimands (new prereg needed):** proportion of eligible native taxa with *excess* driver-information turnover above matched invariant-response null, probability of a genuine sign reversal conditional on common support, and its relation to climatic opportunity and island/mainland accessibility contrasts. Species is the independent replication unit; account for phylogeny/family and geographic pseudoreplication. Maintain a full eligible + excluded denominator and control multiple testing before claiming any global rate.

**External confirmation:** if turnover excess is robust, compare matched region/site demographic records (growth/survival/recruitment, common gardens, transplant experiments). Without those records, call it *occurrence-information nonstationarity*, not niche evolution or a changed causal biological constraint.

## Reproducible use

```bash
python experiments/geographic_turnover_toy_v0.py \
    --replicates 99 --seed 52 --output /tmp/geographic_turnover_toy.json

python experiments/geographic_driver_turnover_v0.py \
    --input /path/to/versioned_available_cells.csv \
    --replicates 199 --seed 20261019 \
    --output /tmp/geographic_driver_turnover.json

python -m pytest -q tests/test_geographic_driver_turnover_v0.py
```

### Claim ledger

- **Supported by executed synthetic examples only:** regional process-importance ranking can reverse without altering a globally fixed quadratic environmental response; a separately simulated region-dependent response can produce observed contrasts above the matched null.
- **Not established:** a cross-species macroecological frequency, native-versus-introduced effect, regionally switching *physiological* limiting factor, niche evolution, or empirical advantage over existing SDM approaches.
- **Product A/B:** unchanged. Product A remains `not_promoted` on its completed fresh plant endpoint and Product B remains blocked. This exploratory lane does not alter any previously frozen denominator, gate or manuscript conclusion.
