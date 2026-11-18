# FIA VA/WI two-phase growth response study: fixed development protocol (2026-11-16)

**Status:** post-previous-outcome, *exploratory* within-VA/WI conditional survivor-growth comparison; not an independent biological confirmation. Source acquisition, thresholds, heldout splits and model list are frozen in this code/config *before opening the new DataMart version's TREE.DIA/STATUSCD*. Historical FIA v4, SDMR Product A, M5 and blocked Product B remain unchanged.

## Estimand

Does one **common temperature–precipitation–stand-density response** predict tree diameter growth under county-block transfer as well as a response containing separate WI climate slopes? For the previously selected five source-robust taxa (*Pinus strobus, Acer rubrum, Quercus alba, Q. rubra, Q. velutina*) the fixed two-region, five-fold design has passed the **source-only** support and 20-train / 3-test counties, 20 test plot-chain minimum for all 25 cells in archived source run 43883371062. This does **not** guarantee new paired live→live outcomes, and is not a reason to relax subsequent response-stage gates.

Only **VA and WI** are acquired/opened in this new study; RI is neither a model-training region nor a growth/survival response endpoint. RI may later serve as an external test of the shared response, but an RI-specific response cannot be estimated without RI training observations.

### New source, two-stage information barrier

1. In one GitHub Actions job, download the **current** USDA FIA PLOT, COND, TREE ZIP for each of VA and WI, exactly once, preserving each real ZIP SHA-256, member, byte length, errors and no-outcome source denominators. The stable independently archived NOAA October 6, 2026 county-month climate file (SHA-256 \`623ae07eed2d9a33bf067bf00556338e6e34eb9cc15fc934e0ccf3dfbb6fd6c8\`) is reused. Read **only prior-visit TREE.SPCD/PLT_CN** for the taxon sampling frame, PLOT measurement dates/counties and source forest condition metadata. Do not open TREE.DIA/STATUSCD yet.
2. Apply the **whole plot-chain county consistency** rule before outcomes (exclude all records of a chain with multiple county FIPS codes). For each fixed species/fold, use only VA/WI **training** source plot chains to define qualified T × P × five-year environmental cells and then project test counties. Strictly require **all 25 primary species × county folds** to pass the same response-readiness source geometry. Preserve all 13 taxonomy entries and every failure reason. Record source SHA and the complete outcome-blind 65-fold source ledger to the artifact before opening responses. If source incomplete/insufficient: **STOP; no biological column is read**.
3. Only then, and only from the **same local SHA-matched ZIP bytes**, read linked prior/current TREE.DIA and STATUSCD via the existing frozen DIA-height and natural-forest-context rule. Primary response is \`log(DIA_current / DIA_prior) / exact PLOT measurement-month interval in years\`, **conditional on both previous/current trees observed alive and intact compatible diameter measurement**. Death, removed and unobserved are counted in the source QC but never set to zero growth. This is **not a survival model**. No species or environmental criterion may be modified in light of growth outputs.
4. Retain only growth rows whose taxon and current PLOT interval have a valid **prior-visit species source**. Exclude full county-unstable plot chains by the pre-response rule. Keep exclusion counts. Archive an exact **derived primary five-taxon numerical growth input** and SHA so a statistical refit can proceed without redownloading mutable raw FIA ZIPs. It contains public county identifiers, plot measurement identifiers, a plot-chain hash, covariates and growth—not raw geographic coordinates or exact TREE IDs.

### Model families and out-of-county evaluation

Fixed five-fold county split: \`first4bytes(SHA256(FIPS))/mod 5\`. Each test county is absent from fit; all available response rows for the selected county fall in the same test fold. Within each fold, climate source bins are selected using **only source observations from training counties**; both training and test biological observations are restricted to the resulting common VA/WI training-source cells.

Fit with training weights that give total weight **0.5 per state** and equal total weight per county within each state:

- **Baseline**: state intercept + measured year, interval, initial log diameter, prior stand age and prior stand basal area.
- **Stationary**: baseline + shared temperature, precipitation and their two interactions with stand basal area.
- **Region-specific**: stationary + WI × temperature, WI × precipitation and both WI × climate × basal-area terms.

No highly correlated raster importance coefficient is taken as proof of a causal stress. Rank-deficient models are unavailable, not re-fitted with selected variables. Required for *each fold and state after source matching*: ≥500 training live→live records, ≥20 training counties, ≥100 heldout live→live records, ≥3 heldout counties and ≥20 distinct plot chains. Full species-level comparison requires **all five folds**; a partial run is not a favorable result.

Score each heldout **county** by mean squared prediction error for all three predeclared models, then average counties equally within each state and states equally; report square roots as RMSE. Measure shared-vs-baseline and regional-vs-shared percent RMSE improvements. Reuse each heldout county exactly once across five folds. A 399-draw within-state county bootstrap quantifies **postfit score uncertainty only**, not retrained model uncertainty or spatially independent mechanism inference.

Development-only **practical threshold** (chosen after v4 was opened, not an independent preregistered ecological test): both the stationary-over-baseline and state-varying-over-stationary gains must be ≥**1%** relative heldout RMSE and the region-varying minus stationary lower percentile bootstrap bound must be **positive** to flag a potentially meaningful *predictive* increment. All other outcomes, including inadequate climate signal, inconclusive intervals, negative gains and model failure remain explicitly reported. No thresholds are relaxed in response to results.

### Interpretation ceilings and reproducibility

The two statuses this study does **not** identify are (1) all-prior-live tree survival/mortality risk and (2) physiological or genetic thermal/moisture tolerances. Survivor conditioning can create apparent growth differences; site productivity, soil, management, forest composition, canopy, source availability, repeated-tree correlation, FIA sample-design weights and true water stress remain partially or wholly uncontrolled. County aggregates and climate normals are not plot microclimate.

**New ZIP bytes are a new source accession, not independent individual observations.** The earlier v4 study may have opened growth of the *same trees*. Therefore even a positive modeled difference is only a post-prior-outcome exploratory association, not external biological replication or niche evolution. Before publication of any biological result, the derived response data/receipts must be archived durably and the independence of biological tree cohorts assessed. Raw original FIA ZIP bytes are not contained in their SHA strings.

Source and synthetic tests:

\`\`\`bash
python -m pytest -q tests/test_fia_shared_vs_regional_growth_core_v1.py tests/test_fia_VA_WI_new_source_growth_v1.py
\`\`\`

The one-shot \`fia-VA-WI-new-source-conditional-growth-v1.yml\` pipeline activates only from a uniquely named lock; it is **not** re-run automatically after an unavailable source or an unfavorable scientific endpoint.
