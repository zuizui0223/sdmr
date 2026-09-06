# Product-A main figure evidence specification

Status: **figure-production contract / frozen evidence only / no further scientific tuning**.

Purpose: keep every quantitative panel traceable to frozen evidence and make the final counterfactual process-identification result, its predecessor falsification and the empirical boundary visually distinct.

## Figure 1 — From model selection to ecological identification

Show conventional `candidate models → score → winner` against the protected Product-A flow. Distinguish:

- predictive adequacy;
- exclusion-based process necessity;
- process stability across ecological selectors;
- final counterfactual process membership.

Selected rasters are representations, not automatically causal drivers.

## Figure 2 — Ecological sharpening can create false necessity

### Evidence

v2.3:

- all three controlled-truth panels evaluable;
- Pareto certificate sharper in 3/3;
- truth/boundary coverage not preserved;
- false necessary-process claims can be created.

### Replacement for necessity

`intersection of retained good models` → **reject as a necessity rule**.

Use explicit process-information exclusion with calibrated boundaries and `unresolved/unavailable` states.

Quantitative v2.6 support belongs in Figure 2/Extended Data:

- 9/9 process certificates complete;
- 9/9 boundary certificates complete;
- false-required=0;
- possible-process recall=1.0;
- possible-process precision≈0.467;
- `required_processes` empty in 9/9 validation taxa;
- wider calibrated intervals retained.

Required interpretation: **safe false-necessity control, but broad identified set**. This is a different estimand from the final process-membership classifier.

## Figure 3 — Counterfactual niche recovery identifies process membership

This is the principal positive quantitative figure.

### Scientific sequence represented by the figure

A stronger factorial truth system varied temperature, water and soil across all seven non-empty combinations. The predecessor consensus-first stable intersection failed this test on discovery/falsification seeds 4201–4205:

- predecessor stable core exact: **22/35 = 62.9%**;
- AUC winner exact: **25/35 = 71.4%**.

Product A then defined, for each process `p`, a truth-free counterfactual score: among prediction-adequate candidates, compare the best held-out Schoener-D ecological niche overlap available with `p` to the best overlap available when every declared representation of `p` is excluded, normalize by the adequate-candidate overlap range, and average across five frozen sampling/background perturbations.

Thresholds were frozen from discovery seeds 4201–4205 only:

- temperature `0.26539643681319824`;
- water `0.06716709986237807`;
- soil `0.33424158409183774`.

### Panel A — fresh validation and unchanged replication

Fresh validation, unused seeds 4301–4305, n=35:

- counterfactual exact: **30/35 = 85.7%**;
- AUC winner exact: **25/35 = 71.4%**;
- predecessor stable core exact: **23/35 = 65.7%**.

Unchanged independent replication, unused seeds 4401–4410, n=70:

- counterfactual exact: **65/70 = 92.9%**;
- AUC winner exact: **56/70 = 80.0%**;
- predecessor stable core exact: **49/70 = 70.0%**.

### Panel B — process-specific operating characteristics in replication

Counterfactual estimator, 70 cases:

- temperature: TP/FN/TN/FP = **40/0/28/2**, sensitivity **1.000**, specificity **0.933**;
- water: **40/0/28/2**, sensitivity **1.000**, specificity **0.933**;
- soil: **39/1/30/0**, sensitivity **0.975**, specificity **1.000**.

### Panel C — exact recovery across all seven process sets

Counterfactual exact recovery in the 70-case replication:

- `{T}`: **8/10**;
- `{W}`: **8/10**;
- `{S}`: **10/10**;
- `{T,W}`: **10/10**;
- `{T,S}`: **10/10**;
- `{W,S}`: **10/10**;
- `{T,W,S}`: **9/10**.

AUC comparator rates are plotted beside the counterfactual values from the same frozen source table.

### Model-disagreement annotation

Ecological fitted models disagreed in 30/70 replication cases; counterfactual process truth remained exact in **27/30 = 90.0%**.

### Provenance

Authoritative replication:

- workflow `34015900603`;
- artifact `9983940439`;
- digest `sha256:af72b78f64e5160dbc96a1147769e83a0b21b461d9b7111ca2e663e8f786d3eb`.

Committed reporting inputs:

- `source_data/nature_fig3_counterfactual_methods.csv`;
- `source_data/nature_fig3_counterfactual_process_summary.csv`;
- `source_data/nature_fig3_counterfactual_process_sets.csv`.

Reporting renderer: `scripts/render_nature_fig3_counterfactual.py`.

Required interpretation: **process membership can be recovered under the declared representation/candidate registry even when exact fitted models disagree**. Do not label this as causal or fundamental-niche necessity.

## Figure 4 — Fresh empirical external-validity boundary

Show:

- 3 complete seed parts;
- 12 taxa × M=150/300/500 km per part;
- prediction guardrail passed;
- ecological nondomination 3/3;
- strict ecological improvement 0/3;
- mean presence-rank delta vs AUC=0.0;
- `empirical_confirmation_not_supported`;
- `not_promoted`;
- ecological/AUC candidate identity 108/108;
- selected-predictor identity 108/108.

The 108 cells are reporting units for realized identity, not replacement primary replicates. Figure 4 must not imply literal empirical process truth or rescue the frozen non-promotion decision.

## Supporting / Extended Data evidence

Retain separately:

- v2.6 exclusion-based necessity safety/breadth;
- v2.7.1 process nondeterminism failure;
- v2.7.2 predecessor deterministic proof of concept and observation-confounding correction;
- v2.7.3 structural/presealed unavailability;
- v2.8.3 technical terminal before sealed ecological evidence;
- v2.8.4 complete scientific non-support and 108/108 selector collapse.

## Figure QA rules

1. Every quantitative value maps to a frozen or prospectively completed artifact/source-data table.
2. Controlled truth is labelled visibly.
3. v2.6 exclusion-based necessity, v2.7.2 consensus stability and final counterfactual process membership are never presented as one estimator trajectory.
4. The predecessor factorial failure **22/35** remains visible in text/Extended Data even though Figure 3 emphasizes fresh validation and replication.
5. Figure 3 must assert **30/35**, **65/70**, **56/70**, **49/70**, **27/30** and the T/W/S confusion counts before rendering.
6. The counterfactual thresholds are reported as frozen before validation, not tuned on validation/replication.
7. No technical/unavailable state is plotted as ecological evidence.
8. No empirical panel implies AUC universal optimality or direct real-data process truth.
9. No complete real-world proxy closure or causal-raster claim is made.
