# FIA forest basal area: county-context versus within-county prediction (2026-11-17)

**Status:** separate, post-outcome exploratory information audit, **not** causal competition identification, niche adaptation or prospective independent replication. Original v4 and VA/WI shared-versus-region climate model decisions remain frozen (0/5 passing 1% practical regional-response benefit); Product A/M5 unchanged and Product B blocked.

## Source and question

The independently verified archived VA/WI first-open [run 43886130089](https://github.com/zuizui0223/sdmr/actions/runs/43886130089), [artifact 14234926861](https://github.com/zuizui0223/sdmr/actions/runs/43886130089/artifacts/14234926861) (ZIP SHA-256 \`ec8f33c4e179250d6ce4e36d7e4933a48969e0c3e9be6d4b4ae090c0c9c64d24\`) contains **170,994** selected live-to-live growth records and **88,145** taxon × prior-visit PLOT interval source records. Exact derived growth CSV SHA \`ee98608ca4e7582144a886d96c9c908a5a5cd25533e1b74ad2e786b20710db4e\`, source CSV SHA \`cd306e559a663c1ddf65259b2fc5298d426f931c272b4cd1ec15ec17da21e402\`, original response JSON SHA \`a768b17684ee712e00187fdfd24b3e929139bc1fe4b11e96aed475bb3c03d482\`.

The original post-outcome predictor knockout showed that stand basal area (\`BALIVE\`) improves out-of-county growth prediction for all five fixed species while the coarse county-mean climate anomaly does not. The next question is more discriminating: **does its predictive gain depend entirely on county-level differences in stand structure, or does variation among stands *inside the same county* add information?**

## Outcome-blind predictor decomposition (but postresponse-selected cohort)

Within the already selected source/response cohort, take prior BA for every sampled tree, average it over each distinct \`plot_chain_sha256\` (rather than letting every tree in a plot increase its weight), and average these chain means within each **species × state × county**. Denote the resulting predictor \(\bar B_c\). Define \(\Delta B_{ic}=B_{ic}-\bar B_c\).

These **county predictor means are computed from the ultimately surviving and admissible tree cohort**. The calculation reads no growth *values* to choose means, but conditions on future inclusion; it is **transductive, selection-conditioned**, and cannot be directly proposed as a prospective, externally available county covariate. Accordingly, the result is descriptive information decomposition only.

Keep the **exact same 5 county folds** (hash of county FIPS), training-only source-qualified 1°C × 100-mm × five-year climate bins, VA and WI state equal weights, equal county weights within states, and fixed five prior taxa (129/316/802/833/837). Fit five predictor families with the same outcome and nuisance controls (state indicator, survey year, interval, initial diameter, stand age):

1. No BA.
2. Original single BA covariate (the previous frozen baseline; verify identical heldout RMSE to within \(10^{-10}\)).
3. County mean BA alone.
4. Within-county deviation BA alone.
5. Both county mean BA and within-county deviation BA (separate coefficients).

Report the **incremental heldout percent RMSE gain of model 5 versus model 3** as the within-county information estimand. The split models do not causally separate competitive crowding from fertility, management, soil, neighborhood composition or stand age/measurement errors.

## First independent same-artifact result, to be checked by GitHub

The original **five** baseline RMSEs reproduced exactly before any new model comparison. **Every** species has a positive within-county increment conditional on county mean:

| Species | County mean BA alone vs no BA | Add within-county BA | State-stratified 999 county-resample 95% interval |
|---|---:|---:|---:|
| *Pinus strobus* | +0.783% | **+3.098%** | +1.890–+4.223% |
| *Acer rubrum* | +0.425% | **+1.644%** | +0.781–+2.525% |
| *Quercus alba* | −0.063% | **+0.747%** | +0.378–+1.082% |
| *Q. rubra* | −0.012% | **+1.176%** | +0.550–+1.787% |
| *Q. velutina* | +0.850% | **+0.701%** | +0.120–+1.242% |

Calculated on unique plot-chain means, only **11.7–20.4%** of the observed across-plot BALIVE variance is between counties in these species, with the remaining **79.6–88.3% within counties**. The within-county incremental heldout gain is positive **separately in VA and WI for 5/5 taxa**. This checks that the local BA predictive information is not merely re-expressing statewide or county climate means.

**Important:** Those confidence bands resample *already fitted heldout county mean squared errors*, not the full model fit or biological sample design. Their apparently positive lower bounds are not calibrated tests of a causal local density effect. All five species, BA partition widths, 999 resamples and result inspection occur **after** the original model outcome was seen. This is not an independently preregistered support claim; all previously negative regional-climate endpoints remain negative. Repeated tree measurements and stand quality may still confound the relationship.

## Full reproducibility / advancement requirement

\`experiments/fia_county_within_basal_area_audit_v1.py\` must fail closed on changed archived sources or any mismatch between the original first-open BA baseline RMSE and the present county folds. It outputs all five species, all scored counties and postfit uncertainty. A uniquely locked archive-only GitHub workflow verifies with synthetic controls then reopens **only the previously derived file**; there is **no new USDA/NOAA download, fitted survival model or new outcome acquisition**.

If an independent biological test is later attempted, source-frozen raw PLOT/TREE/COND and prior-visit COND predictors must be acquired in a distinct protocol; historical selected-survivor county means may not be used to design or calibrate the new test. To distinguish *competition* from confounding, measure tree neighborhoods, independent microclimate/soil or manipulation, stand management and survival together. Merely improving RMSE or lowering BA with age/site controls remains associational.

**Claim ceiling:** local *measured stand-structure predictive information* remains after county-context separation, in the previously selected survivor cohort. No inference to genetic niche conservation, regional limiting-factor switching or causal density-dependent growth.
