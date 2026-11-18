# FIA archived growth: basal-area information versus county climate anomaly (v1)

**Status (2026-11-16):** post-outcome, archive-only *exploratory predictive diagnostic*. Not a novel source cohort, independent replication, physiological inference or claim of competition causality. This is a separately named successor that leaves the original VA/WI response endpoint and negative 0/5 practical regional-gain decisions **unchanged**.

## Fixed inputs and why this is meaningful

- Immutable source: [FIA VA/WI first-open run 43886130089](https://github.com/zuizui0223/sdmr/actions/runs/43886130089), [artifact 14234926861](https://github.com/zuizui0223/sdmr/actions/runs/43886130089/artifacts/14234926861), ZIP SHA-256 \`ec8f33c4e179250d6ce4e36d7e4933a48969e0c3e9be6d4b4ae090c0c9c64d24\`.
- Original embedded \`primary_five_conditional_growth_inputs_v1.csv\` SHA-256 \`ee98608ca4e7582144a886d96c9c908a5a5cd25533e1b74ad2e786b20710db4e\` (170,994 linked live→live growth rows), \`new_source_only_taxon_plot_intervals.csv\` SHA-256 \`cd306e559a663c1ddf65259b2fc5298d426f931c272b4cd1ec15ec17da21e402\` (88,145 taxon × source-plot-interval rows), and original \`VA_WI_growth_result_v1.json\` SHA-256 \`a768b17684ee712e00187fdfd24b3e929139bc1fe4b11e96aed475bb3c03d482\`.
- No network access, raw FIA PLOT/COND/TREE archives, new taxon selection, new holdout folds, or new biological outcomes are necessary. Historic model gains are independently recalculated and checked to within \`1e-8\` percentage points before any new interpretation is allowed.

The key new **exploratory** question is: *does local stand basal-area density add out-of-county predictive information where county-level temperature and precipitation anomalies do not?* This matters because the originally frozen comparison found **0/5** taxa achieving the ≥1% practical regional climate-response improvement, but it could not distinguish genuinely weak environmental predictive information from low-resolution environmental exposure.

## Exact one-variable-group incremental contrast

Reproduce the **identical five whole-county folds**, spatially disjoint training/heldout counties, source-only joint T × P × five-year selection, county-equal and state-equal fitting weights and heldout scoring. There are precisely the five prior-primary species \`129/316/802/833/837\`. The three nested fitted designs are:

1. **Without density**: WI intercept, measurement year, remeasurement interval, initial log stem diameter and prior stand age.
2. **Baseline with density**: all foregoing terms + prior forest \`BALIVE\` (basal area, ft²/acre; source scaling /100).
3. **Stationary climate**: baseline + source NOAA county growing-season mean temperature and precipitation anomalies and their interactions with \`BALIVE\` (same as the earlier frozen common-climate model).

No variable combinations or thresholds are retrospectively optimized. The **new drop-BALIVE contrast was specified after opening these growth responses**; it is only a diagnostic, not an independently prespecified promotion result. A positive percent gain means *heldout equal-county/equal-state RMSE decreases* when adding that predictor group.

### First independent recalculation (before CI archival)

| Taxon | Add stand basal area: RMSE gain | Then add county climate: incremental gain | Approx. 95% county-resampling interval for basal-area gain |
|---|---:|---:|---:|
| *Pinus strobus* | **+3.958%** | −0.225% | +2.059–+5.845% |
| *Acer rubrum* | **+2.103%** | −0.084% | +0.957–+3.305% |
| *Quercus alba* | **+0.725%** | −0.013% | +0.371–+1.065% |
| *Quercus rubra* | **+1.115%** | −0.062% | +0.486–+1.759% |
| *Quercus velutina* | **+1.535%** | −0.576% | −0.070–+2.873% |

For every species, the original frozen baseline→stationary climate gain is reproduced to machine precision using the saved numerical input, **not** copied from the original result. The first independent reimplementation's maximum absolute discrepancy was under \`3e-14\` percentage points.

The 95% intervals above are **1,999 postfit**, state-stratified county bootstraps of existing *heldout per-county squared errors*, **not** intervals from refitting a new model in each resample. Four of five exclude a zero predictive gain. One (Q. velutina) crosses zero. All five remain positive when leaving out **one scored county at a time**. Neither procedure establishes independent random landscape sampling, genetic response or causal competition.

## Why a negative climate result does not establish climate irrelevance

The saved input measurements comprise mean intervals of about **five years** between inventories (per-species medians approximately 5.08–5.25 y). Across sampled trees, the **standard deviation of the interval-average county temperature anomaly is only about 0.28–0.31°C**; the corresponding precipitation anomaly standard deviation is about 54–62 mm per six growing months. This narrow, temporally averaged, administratively aggregated signal is not equivalent to plot-level heatwaves, soil drought, summer vapour-pressure deficit or physiological water balance. Weak incremental predictive value of these two averages can therefore reflect **temporal aggregation and measurement error**, not the absence of important climatic controls.

Conversely, \`BALIVE\` is a local stand-structure proxy and can capture site quality, management, stand age/stocking history, species mix and past disturbance as well as inter-tree competition. Larger predictive gains do **not** rank the *causal* importance of competition above moisture or temperature.

This result is biologically more informative than claiming a climate-driver switch on current evidence: **the observation design identifies local structural information more readily than the available coarse temporal-climate indicators**. That is a bounded, post hoc predictor-information statement, not a physiological or niche-evolution claim. Underlying FIA conditional survivor-selection still prevents inference to death and population-wide growth.

## Reproduction and boundaries

\`experiments/fia_density_vs_county_climate_replay_v1.py\` enforces all three embedded input SHA digests, the original five-taxon/13-source taxonomy denominator and exact original climate score reproduction. It emits (i) a five-species summary with all county-bootstrap and leave-one-scored-county-out ranges and (ii) a full county-heldout MSE ledger. These are based only on the already published input artifact, with **no new USDA/NOAA download or response opening**.

The one-shot archive-only GitHub workflow is triggered solely by \`configs/fia_density_vs_climate_archive_once_v1.lock\`. A future causal mechanism study must separately obtain measured plot-scale climate and independent demography/physiology, accounting for survey weights, spatial clusters, survival/attrition and forest conditions. Neither SDMR Product A/M5 nor blocked Product B is reinterpreted.


## Verified archived execution — no scientific endpoint promotion

[GitHub Actions run 43891221129](https://github.com/zuizui0223/sdmr/actions/runs/43891221129) completed **SUCCESS** on the original source-only and derived primary-growth input, with all five previously frozen baseline→stationary-climate scores reproduced. [Artifact 14236158173](https://github.com/zuizui0223/sdmr/actions/runs/43891221129/artifacts/14236158173) ZIP SHA-256: \`02491b3bdd1d42663eae3ada4c2cf1659e20cfa2ac52662bdc12d24c0a1cc542\`. It contains \`density_vs_climate_summary.json\` (SHA-256 \`2107e7d4564442af7b5050c80c757c4d91af76f8b34b820e3ea618898d6e3633\`) and \`density_vs_climate_county_ledger.csv\` (SHA-256 \`6ad37fe47b6787256de351bebe656d7c664c698b7bb93755b4d877203cf1c182\`).

The derived comparison uses 170,994 conditional live→live growth observations, 88,145 source-only taxon/plot-intervals and the **same original five species and county folds**. No new FIA/NOAA retrieval took place. Its new basal-area knockout is **postoutcome**, and even stable positive incremental RMSE gains identify **predictive information**, not independently established causal competition. See machine-readable frozen summary \`results/fia_density_vs_climate_predictor_information_checkpoint_v1.json\` for unrounded measurements and exclusions. Do not claim this as prospective known-truth validation, a region-specific niche result, or a replacement for the original 0/5 regional climate-response criterion.
