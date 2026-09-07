# Product-A main figure evidence specification

Status: **figure-production contract / frozen evidence only / integrated real-data non-support / no scientific tuning**.

Purpose: keep every quantitative panel traceable to frozen evidence and visually separate controlled-truth capability from empirical external-validity limits.

## Figure 1 — From model selection to ecological identification

Show conventional `candidate models → predictive score → winner` against the protected Product-A flow. Distinguish predictive adequacy, process membership and the stronger exclusion-based necessity claim. Selected rasters are representations, not automatically causal drivers.

## Figure 2 — Ecological sharpening can create false necessity

Use the v2.3 result to show that pruning to ecologically better models can narrow apparent uncertainty while losing truth/boundary coverage and creating false necessary-process claims. Pair this with the v2.6 exclusion certificate:

- false-required = 0;
- possible-process recall = 1.0;
- possible-process precision ≈0.467;
- `required_processes` empty in 9/9 validation taxa.

Required interpretation: safe false-necessity control but a broad identified set. This is not the final process-membership classifier.

## Figure 3 — Counterfactual niche recovery identifies process membership under controlled truth

The stronger factorial truth system varied temperature, water and soil over all seven non-empty combinations.

Predecessor discovery/falsification (`4201`–`4205`, n=35):

- stable core exact **22/35 = 62.9%**;
- AUC exact **25/35 = 71.4%**.

Product A then measured process-specific ecological recovery lost when every declared representation of process `p` was excluded from the prediction-adequate class. Discovery-only thresholds were frozen at:

- T `0.26539643681319824`;
- W `0.06716709986237807`;
- S `0.33424158409183774`.

### Panel a — fresh validation and unchanged replication

Fresh validation (`4301`–`4305`, n=35): counterfactual **30/35**, AUC **25/35**, predecessor **23/35**.

Unchanged replication (`4401`–`4410`, n=70): counterfactual **65/70**, AUC **56/70**, predecessor **49/70**.

### Panel b — process-specific operating characteristics

Replication:

- T: TP/FN/TN/FP **40/0/28/2**, sens/spec **1.000/0.933**;
- W: **40/0/28/2**, **1.000/0.933**;
- S: **39/1/30/0**, **0.975/1.000**.

### Panel c — exact recovery across process sets

`T` 8/10, `W` 8/10, `S` 10/10, `T+W` 10/10, `T+S` 10/10, `W+S` 10/10, `T+W+S` 9/10.

Ecological fitted models disagreed in 30/70 replication cases; process sets remained exact in **27/30 = 90.0%**.

Authoritative replication: workflow `34015900603`, artifact `9983940439`, digest `sha256:af72b78f64e5160dbc96a1147769e83a0b21b461d9b7111ca2e663e8f786d3eb`.

Required interpretation: controlled-truth process membership under the frozen registry, not causal/fundamental-niche necessity.

## Figure 4 — Frozen real-data tests delimit empirical process identification

Figure 4 combines two distinct frozen empirical endpoints; neither is reinterpreted after outcome.

### Panel a — v2.8.4 selector collapse

Plot sealed presence-rank values for ecological and AUC roles across 108 matched taxon × M × seed cells and show:

- same candidate **108/108**;
- same selected predictors **108/108**;
- strict ecological improvement **0/3**;
- terminal state `empirical_confirmation_not_supported` / `not_promoted`.

The 108 cells are reporting units, not independent replacement primary replicates.

### Panel b — real positive-control taxon scores

Eight prospectively frozen positive controls:

- plants: Quercus robur [W], Silene ciliata [W], Plantago alpina [T], Silene acaulis [T];
- nonplants: Bombus terrestris [T], Ochotona princeps [T], Plethodon cinereus [W], Cepaea nemoralis [W].

Plot all-three-M expected-process means only when all three M values are available. Taxa with one missing M are labelled as mean NA; **do not plot them at zero**, because zero would falsely look measured.

Recovered taxon totals:

- plant **2/4**;
- nonplant **1/4**;
- temperature **3/4**;
- water **0/4**.

### Panel c — frozen lane gate and evidence availability

Show the predeclared >=3/4 lane gate and annotate:

- 24/24 taxon × M pipelines completed;
- 21/24 contained at least one prediction-adequate candidate;
- 17/24 expected-process cells had two-sided adequate comparisons;
- positive-only controls → specificity not estimable;
- process scores → inner spatial CV, outer transfer not evaluated.

Required interpretation: **empirical non-support / identification boundary**, not evidence that externally supported biological processes are absent.

### Reporting implementation and provenance

Renderer: `scripts/render_nature_fig4_empirical.py`.

Inputs:

- `source_data/nature_fig4_full.csv`;
- `source_data/real_positive_control_v1_taxon_audit.csv`;
- `source_data/real_positive_control_v1_cell_audit.csv`.

The renderer fails closed on 108/108 identity, plant 2/4, nonplant 1/4, temperature 3/4, water 0/4, exact Quercus/Silene ciliata means, 24/24 technical completion, 21/24 adequacy and 17/24 two-sided comparisons.

Last verified reporting payload: run `34097696742`, artifact `10009246095`, digest `sha256:76c4b7b6d41f0d35ff6c823b65145b7fe354850a2956842f2e283a1aeb471a92`.

## Extended Data priorities

Retain separately:

- v2.6 exclusion-based necessity breadth;
- v2.7.2 predecessor proof of concept and observation-confounding correction;
- factorial predecessor failure 22/35;
- discovery-only threshold separation;
- fresh 30/35 validation;
- unchanged 65/70 replication and five-error envelope;
- v2.8.4 selector-collapse audit;
- detailed real positive-control M-specific diagnostics, including water failures and empty adequate classes;
- immutable scientific outcome/provenance states.

## Figure QA rules

1. Every quantitative value maps to frozen/audited source data.
2. Controlled truth is visibly labelled.
3. v2.6 necessity, v2.7.2 stability and final counterfactual membership are not presented as one estimand.
4. Predecessor **22/35** remains visible before successor validation.
5. Fig. 3 asserts **30/35, 65/70, 56/70, 49/70, 27/30** and T/W/S confusion counts before rendering.
6. Thresholds are discovery-calibrated and frozen before validation.
7. Technical/unavailable empirical states are not plotted as measured ecological effects.
8. Fig. 4 retains **108/108, 2/4, 1/4, water 0/4, 21/24 and 17/24**.
9. Positive-only controls never imply specificity.
10. Inner-CV empirical scores never imply outer spatial transfer.
11. No empirical panel implies literal generating truth, causal raster identification or complete real-world proxy closure.
