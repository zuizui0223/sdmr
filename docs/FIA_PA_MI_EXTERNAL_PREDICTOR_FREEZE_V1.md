# Freeze VA/WI climate-response model parameters before PA/MI biological outcomes (v1)

**Research stage (2026-11-18): development-model freeze only, no external biological outcome opening, NO causal SDM niche mechanism proof.** This is a pre-PA/MI-response commitment made *after* earlier VA/WI and RI biological outcomes and their postdevelopment model comparisons were opened. Do not relabel it as a pristine preregistration of the entire research program. Keep Product A/M5 and blocked Product B unchanged.

## Last verified source requirement

The source-only [NOAA 20261105 event-identity first-open #44296141877](https://github.com/zuizui0223/sdmr/actions/runs/44296141877) retained the exact original 89,616 RI/VA/WI source-selected plot intervals after verifying old 20261006 climate anomalies to the reconstructed visit dates, and compared 83,046 PA/MI source records on the **same** NOAA 20261105 climate edition. **All 13 prior taxa, and all five priority taxa**, are source-eligible in PA and MI. This establishes environmental source comparability only; original source ZIP full SHA values **differ**, so don't claim raw-release equivalence.

The v5 derived training CSV is \`RI_VA_WI_original_IDs_rebased_NOAA_20261105_v5.csv\` SHA \`e3c872f5b0f4fce7e97bef5f172a631d0f09f28ced663d8bb6580a5ab894c11c\`. The immutable v5 receipt and full 13×2 support result must also be validated byte-for-byte before any model fit. The development growth file is the previously opened [FIA VA/WI first-open #43886130089](https://github.com/zuizui0223/sdmr/actions/runs/43886130089), artifact #14234926861, exact 170,994 conditional live→live growth observations and the original 88,145 VA/WI taxon×source-plot intervals, including complete raw-source linkage/derived checksums.

## Fixed training-side model design

For all five priority codes in their immutable order \`129,316,802,833,837\` (including any model failure as *unavailable*, never effect zero), verify every first-open VA/WI taxon×plot×interval joins exactly one v5-rebased source interval; check geographic county, plot-chain SHA, original old T/P climate and full 88,145-row old source identity before changing climate predictors. Replace **only** per-interval county growing-season T/P anomalies by the same-edition NOAA 20261105 values. Preserve growth, prior stand basal area, prior tree diameter, age, year, remeasurement duration, and species as previously opened. Refit on **VA/WI only**, subject to the same source-only VA∩WI joint T (1°C) × P (100mm) × five-year qualifying bins (at least 2 training counties and 5 distinct physical plot chains in EACH region/cell; ≥2 shared cells); require ≥500 live→live training growth pairs and ≥20 training counties **per region**. Do not use RI, PA or MI biological outcomes to fit or select any parameter.

Freeze three already-developed, nested, linear response representations:
- **Baseline**: VA reference intercept, WI indicator, year, interval length, initial log diameter, age, stand BA.
- **Shared climate**: baseline + temperature anomaly /3, precipitation anomaly /200, each × prior BA (BA in 100ft²/acre).
- **Region-dependent climate**: shared + WI × each climate anomaly and WI × each density–climate interaction.

Each state has total weight 1/2; within each state every physical county has equal fitted weight, then previously selected surviving tree records share county weight. If a design is rank deficient or a source denominator changes, **refuse**, not search for new variables or choose a favorable subset.

## External transfer is not PA/MI model calibration

Training VA and WI intercepts and slopes **cannot estimate independent PA and MI intercepts or slopes**. The only v1 regional surrogate mapping is **Pennsylvania → VA branch, Michigan → WI branch**. The **same surrogate intercept** is used by both stationary and regional models so the difference in their out-of-region predictions isolates an **additional regional-climate slope term**, not an illegally fitted local baseline. This is a geography-defined surrogate, not proof that PA resembles VA physiologically or MI resembles WI genetically.

Freeze all model coefficients, numerical predictor names/order, eligible climate-time cell lists, original source hashes, species denominators and missingness before any new PA/MI TREE STATUSCD/DIA read. Output no biological PA/MI predictions, truth, RMSE, inferred survival or winner label at this stage.

Later external evaluation (a *different, separately approved source/outcome opening*) must enforce full PA/MI raw FIA PLOT/TREE/COND source integrity and matching prior live tree denominators; include missing/removals as distinct from deaths and keep **conditional survivor growth separate from survival**. Quantify source-outside-environment fraction, extrapolation, equal-county/equal-state heldout RMSE, outcome missingness and survey weights. Compare shared-vs-baseline and surrogate-regional-vs-shared, retaining unfavorable effects. The existing 1% practical-gain threshold is **postdevelopment** from old FIA analyses, not prospectively chosen at the start of SDMR; do not upgrade ecological inference merely because an interval excludes zero.

## Machine-enforced abstentions

\`experiments/fia_PA_MI_transfer_model_freeze_v1.py\` verifies v5 and first-response input SHA, original 88,145-row VA/WI source identities and climate correspondence; creates one JSON of training-only coefficients per species. \`surrogate_design\` is tested on synthetic PA/MI feature rows, but no real new PA/MI biology is accessed. The GitHub one-shot workflow downloads **only archived prior derived response and source rows**, runs tests, computes full five-source-taxon models with no PA/MI calibration, and stores exact SHA and enough coefficients for later replay.

**Claim ceiling:** model coefficients from previously opened FIA survivor-growth observations, frozen *prior to* external PA/MI biological outcome analysis; no independent replication, causal competition, niche conservation or environmental driver-turnover proof yet.
