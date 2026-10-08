# Supporting Information — Real-plant applicability sequence and disclosure

**Scope.** This chronology accompanies the M5 prospective known-truth Methods manuscript. It is an audit of separately frozen real-plant applicability programmes, **not** extra successful validation evidence or a pooled confirmatory replication.

## Relationship to the primary result

The M5 prospective known-truth test opened a predeclared denominator of seeds 74001–74020 and passed KT-A–F: positive process-state recovery **71/80**, favorable false attributions **0/700**, unresolved over-resolutions **0/60**, and structural-refusal violations **0/60**. Those controlled-world endpoints remain unchanged.

Subsequent real-plant attempts reused the general inferential framework but evaluated its practical eligibility and generalization on GBIF occurrence data and a six-process, 46-environmental-representation system. **The later designs were informed by earlier failures**, even though each version had a separately frozen cohort and execution contract. They must not be represented as four independent confirmatory replications or combined to select a favorable result.

## Chronological accounting of real-plant attempts

| Programme | Cohort and prespecified gate | Terminal result | Outcome exposure and legitimate interpretation |
|---|---|---|---|
| **fresh v2** | 50 selected taxa; full 46-predictor complete-case feature requirement | **37/50** passed after six source-encoding corrections; 13 failed primarily from the shared SoilGrids topsoil support mask | Closed at feature availability; no model fitting or sealed answer-check |
| **fresh v3** | Independently selected 80 candidates, four-SoilGrids support prequalification, then first 50 eligible taxa; full-46 feature gate | **48/50** passed; *Luzula arcuata* and *Micranthes foliolosa* failed model-pool completeness, chiefly because CHELSA gdd10/ngd10/gdgfgd10 were missing in approximately 64% of their model-pool records | Closed before fitting or sealed answer-check; diagnostic missingness could not rescue it |
| **fresh v4** | 90 new metadata-selected candidates; 300-km model-pool-only accessible area and **exactly 5,000** background cells for every candidate before 46-layer preeligibility | **89/90** passed geometry; *Eryngium glomeratum* had only **4,699** available background cells, 301 short | Closed before support-bit opening, model fitting or sealed answer-check |
| **fresh v5** | 120 new candidates; geometry and **all 46 predictor** availability prequalification before first 50 were fixed | **79/120** jointly eligible; final 50 frozen; **50/50** passed numerical feature completeness. However only **10/50** primary process-first routes were available and just **16/300** process cells were stable and sharp (5.33% versus frozen EMP-D minimum 80%) | Irreversible failure declared **before** sealed answer-check. Later sealed scoring is post-terminal characterization, not promotion evidence |

Cohort exclusion was cumulative: v3 excluded its predecessors, v4 excluded **214** previously considered taxa, and v5 used another fresh metadata-defined roster. This does **not** remove the adaptive history of programme design or make the sequence a randomized experiment.

## v5 model-pool diagnosis before answer-check opening

Numerical completeness did **not** translate into a learner-invariant process-information decision. The archived, model-pool-only diagnostic records:

- The shallow-depth histogram-gradient-boosting (HGB) route passed full-system authorization for **32/50** taxa; the penalized logistic route passed for **10/50**. Both authorized **10/50** of the same taxa, leaving 22 taxa authorized by HGB only.
- Among the 10 jointly authorized taxa, only **16/60** process-by-taxon cells (26.7%) agreed on a sharp process state across both learners. On the complete fixed denominator this is **16/300** (5.33%), not 26.7%.
- The final two-learner state accounting was **240 unavailable + 44 unresolved + 15 replaceable + 1 contributory + 0 required = 300** cells. Here *unavailable* means not authorized under the declared model system, **not** that the biological process is absent.
- A post-hoc single-learner rescue would also be misleading: HGB alone produced **125/300** sharp states (41.7%), still below the prespecified 80% EMP-D threshold.

These are descriptive **pre-answer-check model-pool** observations. They reveal two distinct operational bottlenecks—full-system authorization and cross-learner state agreement—but cannot distinguish true biological process ambiguity from representation, learner-capacity, sampling or observation biases. Learners, taxa and thresholds were not changed in response.

The archived decision, model-pool diagnostic and later sealed result are preserved **byte-for-byte** as immutable repository evidence snapshots in `evidence/mee_real_v5_receipts/`, with their original source-file blob hashes recorded in `README_EVIDENCE.md`. **For double-anonymous review, the distributed ZIP removes Git heads, run IDs and artifact identifiers from copies of these JSONs while preserving the scientific values and decisions.** These compact receipts support a numerical audit; they do not replace the underlying occurrence data or fitted models.

## v5 sealed post-terminal characterization

After EMP-D was irreversibly false, the frozen v5 sealed evaluation completed without model refit or post-opening reselection. On the declared 50-taxon denominator:

- SDMR versus matched-learner flat selector: mean paired balanced log-score difference **−0.00385763**, taxon-bootstrap 95% interval **[−0.01116851, +0.00288823]**.
- Primary route evaluable in **10/50** taxa; remaining 40 were unavailable rather than biologically negative and contributed zero gain under the frozen scoring convention.
- Frozen promotion vector: **EMP-A/B/C/D failed; EMP-E/F passed**. The overall empirical promotion failed.
- The full-46 capacity comparison was not a positive rescue: mean paired gain **+0.00406973** with 95% interval **[−0.00056440, +0.00995594]**, including zero, and only 10 evaluable taxa.

The terminal decision predates sealed opening. Sealed scores cannot alter earlier thresholds, taxa, predictor identities, learner requirements, or the failure decision.

## Reproducibility and interpretive boundaries

Frozen development results, receipts, script definitions, and audit documents are preserved separately from the primary known-truth promotion. For version-level reconstruction, relevant receipts include:

- v2: `results/sdmr_fresh_empirical_feature_stage_terminal_v2.json`;
- v3: `results/sdmr_fresh_empirical_v3_feature_gate_result.json`;
- v4: `results/sdmr_fresh_empirical_v4_background_terminal_result.json` and its geometry audit;
- v5: `results/sdmr_fresh_empirical_v5_model_pool_terminal_decision.json`, `results/sdmr_fresh_empirical_v5_sealed_promotion_result.json`, and the post-terminal receipt.

No failed real-plant programme can be relabelled a success by retrospectively removing taxa, variables or learners. Nor does failure imply absence of the named thermal, water, seasonality, radiation, soil or productivity processes. **The controlled known-truth recovery demonstrates validity within its frozen generating worlds, not real-plant transportability or biological causal identification.**
