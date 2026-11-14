# FIA × NOAA v4: first opened response, source-pinned audit (2026-10-28)

**Status: exploratory observed growth, not a prospective validation of niche-driver turnover.** This document records the *first observed outcome* of the already frozen one-run v4 protocol, rather than fitting a new model or selecting a better-looking cohort. It does not change SDMR Product A, blocked Product B, or canonical M5.

## Exact evidence and provenance

- [Authoritative GitHub Actions run 40543320267](https://github.com/zuizui0223/sdmr/actions/runs/40543320267) on PR #284 head `3b41f88d8b06b84afb390a6ba7755736e56095cd`, workflow `fia-climate-density-one-snapshot-v4`; successful one-shot response job. [Artifact 12751849450](https://github.com/zuizui0223/sdmr/actions/runs/40543320267/artifacts/12751849450), archived GitHub ZIP SHA-256: `66fe0e81815f99b0112b991f1ee6f766f968889fc858989e4a2f878993cfcaa3`.
- The ZIP contains exactly `source_phase_receipt.json` (18,094 bytes, SHA-256 `5ace92c42a912fdd9d1a720849a458b28821c16764b088defdfc2ce1488c83b5`) and `exploratory_climate_density_growth_v4.json` (62,566 bytes, SHA-256 `a336e0da49588dc81d89ef5e87826285d8d3afeaa80b6bf013c72599abce7512`). These hashes refer to uncompressed exact JSON bytes. Recovered and recomputed the descriptive summaries from the saved result on 2026-11-14, **without refitting**.
- The source-only receipt declares all **3/3** fixed FIA state ZIP families (TREE/PLOT/COND for Rhode Island, Virginia, Wisconsin) ready and records that diameter/status were not opened until after the source check. Same downloaded ZIP bytes are SHA-checked again before biological opening.
- NOAA 2026-10-06 source CSV SHA-256 `623ae07eed2d9a33bf067bf00556338e6e34eb9cc15fc934e0ccf3dfbb6fd6c8`. These are source receipts, **not** a publicly deposited immutable copy of the nine original FIA ZIPs. FIA's mutable online DataMart cannot be treated as equivalent to the frozen historical bytes, and a later download must not replace them.

## What was actually evaluated

- Fixed **13/13** tree species with **295,374** admitted, linked live-to-live tree-growth intervals: RI **5,187**, VA **93,150**, WI **197,037**. These are conditional survivor measurements, not independent taxa, population-weighted forest growth, stand biomass or survival measurements.
- Response: log stem-diameter increment per exact plot measurement-month interval, per year. Five deterministic, outcome-blind **whole-county folds**; not independent geographic external validation. Model families are predeclared: (1) tree size/age/stand basal area, state, time/interval baseline; (2) + county growing-season temperature/precipitation anomalies; (3) + shared climate × basal-area interactions; (4) + state-specific modifications to those interactions.
- Positive `baseline RMSE − comparison RMSE` denotes a *smaller held-out error* under the comparison model. Species are the 13 units of the summary; individual trees and repeated plots must not be treated as independent cross-taxon replications.

| Endpoint, relative to baseline | Species improved | Median within-species relative RMSE reduction | Equal-species mean |
|---|---:|---:|---:|
| Add temperature + precipitation anomalies | **9/13** | **+0.0196%** | **+0.0129%** |
| Add shared climate × basal-area interactions (full vs baseline) | **5/13** | **−0.0159%** | **−0.0404%** |
| Add state-specific climate × basal-area interactions (full vs baseline) | **8/13** | **+0.0127%** | **−0.1028%** |

Incremental improvements, **not** comparisons with baseline: shared-interaction vs climate-only **3/13** species; state-interaction vs shared-interaction **8/13**. The median *relative* gains above are fractions of one percent, not percentage-point gains in explanatory power. The mean state-interaction comparison is unfavorable because larger adverse errors in some species outweigh small benefits in others.

### Species audit (positive values mean lower RMSE)

All values are `100 × (baseline RMSE − candidate RMSE) / baseline RMSE`; the three columns use the *same* baseline denominator.

| Species (FIA SPCD) | Live→live intervals | Climate % | Shared interaction % | State interaction % |
|---|---:|---:|---:|---:|
| *Juniperus virginiana* (68) | 5,927 | −0.0395 | −0.4786 | −0.5635 |
| *Pinus strobus* (129) | 20,566 | +0.0137 | −0.0159 | −0.1337 |
| *Tsuga canadensis* (261) | 9,029 | +0.0571 | −0.0566 | −0.8662 |
| *Acer rubrum* (316) | 93,367 | +0.0019 | −0.0070 | +0.0373 |
| *Acer saccharum* (318) | 54,543 | +0.0376 | +0.0486 | +0.0744 |
| *Betula alleghaniensis* (371) | 8,112 | −0.0199 | −0.0229 | −0.1341 |
| *Fagus grandifolia* (531) | 7,071 | −0.0695 | −0.0705 | +0.0125 |
| *Fraxinus americana* (541) | 9,497 | +0.0196 | −0.0590 | −0.0441 |
| *Populus grandidentata* (743) | 12,665 | +0.0488 | +0.0369 | +0.0213 |
| *Prunus serotina* (762) | 12,969 | +0.0255 | +0.0331 | +0.0637 |
| *Quercus alba* (802) | 26,247 | +0.0236 | +0.0041 | +0.0127 |
| *Quercus rubra* (833) | 24,917 | +0.0708 | +0.1009 | +0.1068 |
| *Quercus velutina* (837) | 10,464 | −0.0017 | −0.0385 | +0.0766 |

Names are from the official FIA taxon crosswalk already archived in this branch. Values are rounded for display only; exact results are in the hashed artifact.

## Scientific interpretation and non-support

**What is positive:** The frozen nine-source acquisition succeeded and produced measurable, auditably screened cross-county comparisons for all 13 predeclared taxa. Some species gain out-of-county predictive information from climatic anomalies; regional changes in fitted interactions sometimes improve this *particular* holdout criterion.

**What is not supported:** The extra climate/interaction gains are negligible compared with overall RMSE, inconsistent among species, and have no calibrated cluster-level uncertainty or predeclared minimum ecological relevance threshold. A region-interaction advantage does not measure a different physiological optimum. Conversely, a negligible interaction advantage does not prove a stationary niche. Do **not** promote this v4 run to a universal climate × competition mechanism, a causal limiting-process switch, a demonstration of local adaptation, or Product B unblocking.

Critical remaining threats: county climate coarseness and public FIA geolocation perturbation; highly uneven state representation and likely limited common environmental support; clustered repeated plots/trees; survivor and management selection; soil/microclimate and year effects; stand basal area as a nonrandom proxy for competition; no held-out independent demographic or physiological process endpoint. The regional sample is three U.S. states, **not** a global species sample or metaanalysis.

The earlier archived size/age/stand-structure gradient (`docs/FIA_HABITAT_ARCHIVED_SYNTHESIS_V1.md`) and stationary-niche climate-switch counterexample (`docs/GEOGRAPHIC_STATIONARY_WARMING_SWITCH_V1.md`) answer **different estimands on different evidence**. Neither supplies missing causal validation to the v4 response.

## Next falsifiable data gate, before any new biological conclusion

1. **Freeze environmental common-support eligibility** by species and region *without viewing further growth responses*: coverage of joint temperature–precipitation anomalies, remeasurement years, adequate counties and plot clusters. Refuse unmatched extrapolation rather than redefining `M` to obtain a favorable result.
2. **Separate sampling from biology**: model plot-level cluster structure, missing/dead/removed trees and FIA design weights. Preserve growth conditional on survival and observed-status endpoints as different outcomes.
3. **Test stationary against region-varying response only within shared environmental support**, using a prospectively reserved external plot/county cohort and a predeclared minimum worthwhile held-out improvement with cluster uncertainty. A physiological/experimental dataset is required before interpreting any statistical winner as niche evolution.

**Reopening prohibited:** none of the M5, original Product-A confirmation, historic FIA source stops, or previously opened v4 source/outcome receipts can be recomputed or reclassified using this retrospective summary.
