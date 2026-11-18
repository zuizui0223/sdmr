# SDMR × Structural: reference-conditioned ecological structure information (development v1)

**Status:** Method development / synthetic contracts only (2026-11-18). No new biological effect, no reopening of the frozen Product-A v2.8.4, M5 known-truth, fresh-plant v5, or Structural manuscripts. Original SDMR Product B remains **blocked**. The implementation is in `src/sdmr/contextual_structure_evidence.py` and is not part of an M5 submission result.

## Question and independently observed motivation

Can a structural representation contribute **held-out endpoint information beyond a declared ecological reference**, and is that information portable across spatial blocks, time and biological operators?

Two non-exchangeable exploratory empirical lines motivate this problem:

| Source, response | Archived within-source result | What it does NOT establish |
| --- | --- | --- |
| SDMR draft PR #284, FIA VA/WI survivor-diameter growth | Source-frozen, plot-chain-equal *within-county* stand basal-area deviation improved county-heldout prediction in 5/5 fixed species: Pinus strobus +2.503%, Acer rubrum +1.095%, Quercus alba +0.823%, Q. rubra +1.521%, Q. velutina +0.825%. | Causal competition or new field replication; cohort selection on live-to-live survivors and transductive county means are substantial issues. |
| SDMR draft PR #284, **same** FIA survivor cohort, same-plot lagged analysis | Adding within-plot `ΔBALIVE` gave positive point gains in only 2/5 species, with one nominal postfit interval excluding zero. | A portable temporal growth mechanism. This is **not** a second independent cohort. |
| Structural draft PR #469, Finland deadwood × saproxylic beetle guild-composition Hellinger² | 142 original physical sites, nine heldout geographic cells, 7/9 positive; site-level resource `VD10` gives block-equal +0.00024237 Hellinger² (conditional signed-block p=0.0150). | Causal resource limitation or multi-country universality. |
| Structural draft PR #469, Steigerwald beetle composition | Six parent plots within **one** German forest; source-conditioned shade baseline + host-tree identity gives +0.019699892 heldout Hellinger², 6/6 positive (conditional p=0.03125). | Six independent forests, future occupancy or a novel field host-sorting effect. |
| Structural draft PR #469, Slovak Carpathian source | 116 original beetle-community plot IDs aligned to forest environment; 18 source stand groups; eight predictors complete. | **No guild biological scores** yet: organism-response/guild-ontology stage is on HOLD. |

Source documents:
- [FIA spatial plot-equal audit](https://github.com/zuizui0223/sdmr/blob/research/geographic-driver-turnover-macro-v0-20261019/docs/FIA_WITHIN_COUNTY_BA_PLOT_EQUAL_SENSITIVITY_V1.md)
- [FIA same-plot temporal audit](https://github.com/zuizui0223/sdmr/blob/research/geographic-driver-turnover-macro-v0-20261019/docs/FIA_TEMPORAL_WITHIN_PLOT_BA_V1.md)
- [Finland spatial host-guild result](https://github.com/zuizui0223/Structural/blob/analysis/forest-macro-plot-environment/docs/FOREST_BEETLE_FINLAND_142SITE_DEADWOOD_HOSTGUILD_SPATIAL_HOLDOUT_ACTUAL_RESULT_20261115.md)
- [Steigerwald host-tree result](https://github.com/zuizui0223/Structural/blob/analysis/forest-macro-plot-environment/docs/FOREST_BEETLE_CHIU2023_STEIGERWALD_SIXPLOT_HOST_SHADE_SITE_HELDOUT_ACTUAL_RESULT_20261117.md)
- [Carpathian source readiness (not biology)](https://github.com/zuizui0223/Structural/blob/analysis/forest-macro-plot-environment/docs/FOREST_MACRO_CARPATHIAN116_ORIGINAL_SOURCE_ADMISSION_ACTUAL_RESULT_20261118.md)

**Do not pool the effect sizes:** FIA uses tree growth (RMSE) and survivor selection; Structural uses beetle community composition (Hellinger²), different sampling levels and operators. These are two applications of an inference principle, not replications of a shared effect.

## Method objective, rather than 'a better AUC'

For a declared process `P`, endpoint `Y`, structural operator `O` and reference `R`, ask two separate questions.

**Stage I: reference-conditioned incremental prediction.** Compare heldout losses of `R` and `R+C`, where `C` is a typed structural candidate (e.g. basal area, deadwood amount, host wood identity, canopy structure). For geographic block `b`:

```
d_b = mean_{unit i in b}[ L(Y_i, R_i) - L(Y_i, (R+C)_i) ]
Delta = mean_{independent blocks b} d_b .
```

Positive `Delta` indicates conditional predictive information **only for that endpoint, representation and validation axis**. Larger numbers of trees/traps in one plot do not turn it into more independent blocks. `L` must be an additive per-unit loss (squared error, Hellinger-squared, log loss or Brier), **not a pooled RMSE**. Block-exact or seeded block sign-flips are *conditional diagnostics* requiring exchangeable block differences, never a causal or population-level uncertainty certificate.

**Stage II: process-information necessity, separately.** Only after establishing a complete and adequate system, predeclare a many-to-many mapping from representations to processes. Refit the same models after excluding **every carrier** of `P`, including composites and proxies. Reuse `sdmr.process_information_closure` and its statuses. A positive Stage-I gain for one measured variable does **not** prove `P` necessary or uniquely identified. A null/negative increment is not an equivalence test and does **not** prove the process absent.

The procedure must distinguish:
- **Predictive increment:** `R -> R+C`, endpoint- and reference-conditional.
- **Process closure:** full information availability, complete knockout of process carriers, potential replacement and explicit unresolved/unavailable states.
- **Space/time transfer:** separate heldout spatial or future endpoint for a frozen process claim; absence of temporal transfer cannot be hidden by spatial association.
- **Observation/selection process:** sampled live-to-live trees, detection, effort, site management and missing species are not assumed to be random.

## A testable ecological distinction

The most interesting mechanistic fork is **stable site/stand differences versus within-site changes**.

- Spatial BA differences can summarize persistent site quality, stand age/history, species composition, management, soil or competition. Out-of-county transfer of their *predictive association* does not discriminate these.
- Lagged `ΔBA` after earlier growth/structure is a stricter, but still potentially endogenous, temporal contrast. The observed 5/5 spatial versus 2/5 temporal signs from the **same** FIA cohort bar promotion of a universal competition mechanism.
- Beetle host/resource identity is an *operator-specific* channel, not the same candidate as stand crowding. An observed beetle Hellinger² gain cannot validate a tree growth driver. A putative shared principle is conditional **residual information**, not shared coefficients.
- Structural's connectivity and forest-resource operators must stay typed: geometry, measured vegetation/resource, detection/realized link and future demographic transition are different evidence levels.

## Executable v1 interface

`StructuralContextContract` requires:
- one named endpoint, biological operator, process, structural candidate and **reference specification**;
- explicit **spatial / temporal / region / taxon** validation axis and evidence family ID;
- source SHA-256, response-blind (unit, block)-identity SHA-256, and exactly predeclared independent block IDs;
- additive loss metric, minimum block count, margin, test rule/seed and synthetic/retrospective/prospective evidence class;
- training-only preprocessing and temporal direction guards (future targets cannot use contemporaneous predictors);
- prospectively designated source/outcome-blind design before any `conditional_predictive_gain` decision.

`audit_contextual_structure` rejects duplicate units, wrong block/identity denominators, nonfinite losses and non-additive RMSE inputs; it uses **block-equal**, not tree-count-equal aggregation. For 2–16 eligible blocks its two-sided signed-block test is exact; for 17+ blocks it uses seeded Monte Carlo (with +1 correction). Missing blocks are a **STOP**, insufficient predeclared blocks are **not_estimable**, and retrospective cases stay **retrospective_diagnostic_only** irrespective of attractive p-values.

`integration_scope` explicitly refuses pooled-effect inference for differing ecological endpoints/operators, differing process candidates, shared source families, unequal metric scales, different transfer axes or nonconfirmatory cohorts. Returning `candidate_for_external_harmonization_not_automatic_pooling` is not permission for immediate meta-analysis.

**Critical implementation boundary:** Code validates supplied receipts, identities and losses. It cannot independently prove that supplied losses are truly out-of-fold or that field effort, survivor selection and ecological process closure are adequate. Adapters must enforce those upstream.

## v2 next-stage frozen hypotheses and estimability requirements

1. **Known-truth falsification panel (new, unused seeds only):** generate (a) genuine structural effect, (b) correlated site-quality proxy without structural effect, (c) shared carriers for biotic/abiotic processes, (d) observation/survivor selection, (e) purely spatial stand association with no lagged predictive increment, (f) temporal structural response transferable across regions, (g) operator mismatch and (h) missing environmental process. Freeze all world parameters, source/response stage barriers, learner pair, minimum blocks, falsification thresholds and equality/abstention penalties before new openings.
2. **Source adapter interface:** preserve physical stand/plot/tree hierarchy; train-only covariate transformations; frozen source version; strictly earlier measurement for future response; independent effort/zero-sampling frame; geographic and temporal shared-support gates; independent guild-ontology audit. Each adapter emits only paired out-of-fold **additive** losses and an exact response-blind unit ledger.
3. **Independent biological transfer:** do not re-open/relabel the consumed FIA/Finland/Steigerwald evidence. A new fit must use a distinct, source-frozen outcome cohort with region- or stand-heldout tests and relevant controls. Carpathian 116-plot structure readiness does not yet authorize beetle guild outcome or cross-country promotion. NEON in SDMR has a token/individual-identity source barrier, not an independent demographic result.
4. **Distinct paper paths:** keep the original M5 *Methods in Ecology and Evolution* article and its 71/80 vs 0/700 result intact. This new typed-reference/context/transport framework may warrant an independent methodology manuscript only after external tests; forest case studies may later become a separate ecology study. Product B cannot be unblocked by this exploratory module.

## Evidence non-retroactivity

Source-family and time-overlap bookkeeping matters more than apparently consistent signs. The same FIA cohort contributes **one** selected-survivor evidence family; spatial and temporal audits are two estimands, not independent replications. Finland, Steigerwald, and Carpathian each retain their own original field grouping and publication provenance. Nothing in this file recalculates their effect sizes, treats a historical post-outcome analysis as prospective, assumes available foliage resources are local deadwood, or turns 'unavailable' into an ecological zero.
