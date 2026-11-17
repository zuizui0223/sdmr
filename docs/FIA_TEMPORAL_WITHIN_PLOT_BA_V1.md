# FIA temporal within-plot stand-density change: archived growth prediction diagnostic v1

**Status (2026-11-17): postresponse exploratory analysis, NOT prospective confirmation, causal competition, identical-individual longitudinal tracking or niche evolution.** This tests a stricter ecological interpretation than the previously robust spatial **within-county plot-level BALIVE predictive signal**.

## Why this is a necessary separation

The fixed five primary FIA taxa (129, 316, 802, 833, 837) had positive out-of-county growth-prediction benefits when accounting for plot-to-plot stand basal-area differences inside counties, including equal-plot weighting. That comparison still conflates **persistent plot-specific forest history, fertility, management and neighborhood structure** with the effect of density.

A different within-plot question is: *after the previous observed growth interval, does the change in stand basal area measured for the next growth interval predict the following plot-level survivor-growth rate, beyond earlier growth and other changing covariates?*

This is a stronger temporal predictive diagnostic, but still **noncausal**: time-varying management, tree cohort replacement, earlier tree growth affecting later BALIVE, drought stress, disturbance, and regression to the mean all remain possible. The archived derived table does not have stable individual TREE CNs for cross-event identity confirmation. Thus a "plot chain" is not a panel of the *same individual trees*.

## Frozen input and no-new-outcome boundary

Use exactly the [first opened FIA VA/WI growth source run 43886130089](https://github.com/zuizui0223/sdmr/actions/runs/43886130089), [artifact 14234926861](https://github.com/zuizui0223/sdmr/actions/runs/43886130089/artifacts/14234926861) (ZIP SHA256 \`ec8f33c4e179250d6ce4e36d7e4933a48969e0c3e9be6d4b4ae090c0c9c64d24\`). Require exact derived growth CSV SHA256 \`ee98608ca4e7582144a886d96c9c908a5a5cd25533e1b74ad2e786b20710db4e\`, source-only taxon/plot CSV SHA256 \`cd306e559a663c1ddf65259b2fc5298d426f931c272b4cd1ec15ec17da21e402\` and original response JSON SHA256 \`a768b17684ee712e00187fdfd24b3e929139bc1fe4b11e96aed475bb3c03d482\`. Original numerical records are 170,994 selected live-to-live tree-growth rows and 88,145 prior-taxon source intervals. No new FIA/NOAA GET or biological outcome read takes place.

Verify source plot-chain identity via hash, exact species × state × current PLOT interval, matching county, calendar end-year and NOAA anomaly values. Preserve the **13-taxon original source frame**, with eight secondary taxa explicitly listed as *not modelled* rather than silently dropped.

## Postresponse-defined plot-event pairing

1. Collapse selected tree-growth rows to **species × state × county × plot-chain × PLOT current-event** means. Each source event requires **at least 3 admitted live-to-live tree growth rows**, a single consistent previous \`BALIVE\` value across those tree rows, an unambiguous source-only interval match and measured year. No tree row is treated as a separate replicated plot.
2. For each plot chain, select the **first two chronologically observed eligible** growth intervals. These are not guaranteed to be consecutive underlying FIA censuses. Require 4–15 years between the end dates and refuse invalid or identical source identities. Keep only one first-pair contrast per plot-chain for spatially independent plot grouping.
3. The first-open derived data contain exactly **4,744 such plot pairs**: *Pinus strobus* 519, *Acer rubrum* 2,448, *Quercus alba* 767, *Q. rubra* 741 and *Q. velutina* 269. This was counted *after* the earlier empirical outcomes were opened; sample eligibility is therefore exploratory. A first-pair table contains earlier/later mean annual log-diameter growth, earlier/later prior BALIVE and the changes in prior size, stand age, remeasurement interval, county temperature and precipitation, measurement year and gap. Do not treat differing observations at the same plot as verified same-tree response changes.
4. Retain the original **five out-of-county folds** (first 4 bytes of SHA256(FIPS county) modulo 5). For each species/fold, select allowed joint temperature×precipitation×five-year source cells using **VA/WI source-only TRAINING counties only**, requiring at least two counties and five plot chains in *each* training region per cell. Both the earlier and later plot events must fall within the intersection of those qualified training source cells. A test county is never used to define the environment bins.
5. After joint-source filtering, require per state ≥10 training counties and ≥40 training plot pairs, ≥3 heldout counties and ≥5 heldout plot pairs; otherwise keep the fold in the fixed denominator as unavailable. All five folds are needed for any full-taxon score.

The exact source cell restrictions were not applied in the initial unconstrained local diagnostic. Do not relabel that first diagnostic as a source-matched result.

## Two nested predictors, temporal order, scoring

For each retained plot pair let \`g0\` be the mean survivor growth during its earlier window and \`g1\` during the later window. Let \`B0\` and \`B1\` be prior BALIVE for those intervals.

The *fixed baseline* predicts \`g1\` using earlier \`g0\`, initial \`B0\`, earlier year, elapsed years, state indicator and the differences in sample-mean initial stem diameter, stand age, measurement interval, temperature and precipitation between the two growth windows. The only added covariate in the second model is **\`ΔBALIVE = B1 − B0\`** (in 100 ft² per acre).

Both variants use linear least squares weighted equally over VA and WI and over counties within states. Every plot pair appears at most once. County-heldout mean squared errors are averaged with equal county weights inside each state and then equal state weights before square-root RMSE. Positive \`100 × (RMSE_baseline − RMSE_ΔBA) / RMSE_baseline\` means an improvement. The 999-draw state-stratified county bootstrap resamples **postfit county errors**, not full model refits, and is not a calibrated ecological selection test. A zero-crossing interval is explicitly inconclusive.

## Preliminary calculations (superseded by fixed GitHub archived replay)

A simpler earlier difference-of-growth model produced positive point gains for 5/5 taxa, but **all five postfit 95% intervals included zero**. It is a different estimand and cannot be used as a success criterion.

A stronger model with preceding growth as predictor, but **without** the shared-source climate-time filter, yielded gains +3.377%, +1.953%, −0.268%, −0.043%, +0.170% (taxa 129/316/802/833/837 respectively). With the fixed **both-event source-climate restriction** described above, the independent preliminary point gains are approximately +2.125%, +2.491%, −0.316%, −0.155%, −0.449%. Under preliminary 499-draw postfit uncertainty, only *Acer rubrum* had a zero-excluding interval. The canonical source-hash-checked workflow uses the fixed 999-draw setting and will produce the authoritative audit, not these preliminary values.

This materially limits the original positive stand-density **spatial** association: persistent local BA differences can remain predictive, while a **time-varying within-plot predictive mechanism is not established across the five taxa**. No new positive outcome was selected from model tuning; the full five-taxon denominator is retained, including the negative or inconclusive taxa.

## How to reproduce and claim ceiling

\`experiments/fia_temporal_within_plot_density_audit_v1.py\` enforces the original exact CSV/receipt checks and counts, source-anomaly identity, unique plot event, first-two-event and fixed county-fold rules. It saves an aggregate result and **all heldout county MSE rows**, plus an auditably derived plot-pair numerical table with SHA-hashed plot-chain IDs (not raw tree identities). The archive-only one-shot GitHub workflow uses no FIA DataMart GET.

A future mechanism study must independently freeze tree identity, mortality/harvest/attrition, true site climate and soil, disturbance/management and forest condition before looking at later growth outcomes. Within-plot fixed-effects or first-difference associations alone still do not prove that density **causes** growth suppression; the present derived data cannot establish that repeated records represent identical surviving stems.

**No changes authorized:** prior FIA v4, Product A not promoted, Product B blocked, M5 endpoints or the original 0/5 practical region-specific climate winner count.


## Completed immutable-source GitHub validation (2026-11-17)

The synthetic test gate [run #44005063857](https://github.com/zuizui0223/sdmr/actions/runs/44005063857) **passed** before the first archived replay was dispatched. The SHA-frozen **no-network/no-new-outcome** [GitHub Actions run #44005163621](https://github.com/zuizui0223/sdmr/actions/runs/44005163621) then **completed successfully**. Artifact [#14293388090](https://github.com/zuizui0223/sdmr/actions/runs/44005163621/artifacts/14293388090) has ZIP SHA-256 \`6feaf9595b8b42f28958bfb0a18307f877a650bfa37f0a330955cfc8f2165379\`. Within the ZIP: full JSON SHA-256 \`68bdcacfd859870c0e131f93ffb40571101d32487d23ed9d021c6a1a07d5b164\`, complete species×heldout-county error ledger SHA-256 \`c6a003a36bec4883cc87f1fc34a821f8ea5b9ad6e5f567e32601d167a470b1b5\`, and derived, SHA-hashed plot-chain numeric input CSV SHA-256 \`32df354dd13214861c1bfffc943ee26c780249091da388883f48a5e819b8474a\`.

The original 170,994 selected survivor-growth records and 88,145 prior-taxonomy source records yielded **39,659** source-matched plot-events, **18,759** with at least three selected growth records and one unambiguous prior BA, **4,744 first-two eligible plot-chain pairs** (exact five-taxon denominator), and **4,501 source-supported out-of-county test plot pairs** across the five heldout county folds. These create **568 species×heldout-county score records**, not 568 independent globally unique counties.

| Taxon | Candidate pairs | Evaluated heldout pairs | Incremental RMSE benefit of ΔBALIVE after earlier plot growth | 95% *postfit* county-resample interval |
|---|---:|---:|---:|---:|
| *Pinus strobus* (129) | 519 | 473 | +2.125% | −0.254 to +4.596% |
| *Acer rubrum* (316) | 2,448 | 2,364 | +2.491% | +0.466 to +4.305% |
| *Quercus alba* (802) | 767 | 719 | −0.316% | −1.362 to +0.501% |
| *Quercus rubra* (833) | 741 | 719 | −0.155% | −0.621 to +0.230% |
| *Quercus velutina* (837) | 269 | 226 | −0.449% | −2.772 to +2.233% |

The **999-draw** official county score intervals above replace the earlier *preliminary 499-draw* values; point estimates are unchanged. Independent re-aggregation of the artifact's country/state-averaged county MSE reproduced every point gain within 4×10⁻¹² percentage points. All five species passed all five source-restricted county folds, so non-positive results are not being hidden as non-estimable taxa.

**Falsification result:** *Across-plot within-county stand structure* had positive prediction increments in all five taxa in the earlier same-cohort spatial audit. But *within-plot temporal BA changes* in this more controlled lagged-growth and common-source-support comparison have only **2/5 positive point increments** and **1/5 nominally zero-excluding postfit intervals**. The *Acer rubrum* interval is exploratory, unadjusted for multiple testing, and not a calibrated whole-model/whole-county causal inference interval. It cannot be promoted as a repeatable physiologic mechanism. Stronger claims that competition generally causes lower growth across all five taxa are not supported by this longitudinal diagnostic.

These results are compatible with a strong, persistent local **site/stand context predictor** that does not reliably translate into a universal short-to-midterm density-change effect. They do not distinguish soil/site fertility, stand structure, repeated tree survival selection, growth feedback into subsequent BA, forest operations or actual inter-tree competition.

The compact, hash-pinned checkpoint \`results/fia_temporal_within_plot_BA_checkpoint_v1.json\` preserves this complete positive-and-negative result. **Original regional climate model practical promotion remains 0/5 and Product B blocked.** The research PR remains draft.
