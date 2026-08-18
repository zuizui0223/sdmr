# Product-A v2.4: falsification-first exclusion certificate

## Status

This is a predeclared known-truth development line. It starts after Product-A v2.3 ended in `identified_set_not_supported` and before any v2.4 validation truth is opened.

Product-A v2.3 established a useful negative result: pruning a complete adequate model set to its mean ecological-recovery Pareto front narrowed response intervals in all three panels, but it also created a false necessary-process core and lost boundary coverage. Agreement among retained fitted models was therefore not evidence of biological necessity, and between-model spread was not a complete uncertainty interval.

v2.4 changes both claims.

## Scientific target

The output is not one winning SDM and not an intersection of selected variable sets. It is a falsification-oriented certificate that asks:

1. can the observed niche evidence remain adequate when a whole ecological process and every declared proxy for it are forbidden;
2. which process-necessity claims are refuted, required only by the frozen evidence contract, or unresolved;
3. what niche-boundary range remains after procedure, accessible-area and spatial-refit uncertainty are represented;
4. how much that raw range must be expanded, using discovery evidence only, to avoid systematic undercoverage.

The empirical interpretation remains the realized/accessible environmental niche under the declared occurrence, observation and M contracts. `required_by_frozen_evidence_contract` is not a claim of fundamental physiological necessity or causation.

## Frozen information order

For each panel:

1. simulate discovery taxa without exposing their generating truth to fitting or selection;
2. build the base and process-knockout procedure library from the frozen alias registry;
3. require complete taxon × M × outer-fold evidence;
4. apply the absolute AUC-equivalent adequacy gate;
5. freeze admitted knockout routes and process statuses that can be determined from discovery evidence;
6. fit every frozen validation member under every required M and spatial refit without reading validation truth;
7. freeze raw response envelopes and apply interval-expansion radii calibrated on discovery taxa only;
8. open validation truth once for process and boundary audits;
9. apply the predeclared decision rule.

No validation outcome may choose a process alias, knockout, procedure, M, spatial refit, calibration radius or fallback.

## Frozen process registry

The candidate ecological predictors are:

- temperature process: `temperature`, `temp_proxy`, `sparse_temp_proxy`;
- water process: `water`;
- soil process: `soil`;
- seasonality process: `seasonality`;
- noise process: `noise`, `sparse_noise`.

`recording_bias` is an observation-process nuisance term. It remains available to procedures that declare it and is marginalized before ecological interpretation. It is never a candidate ecological process and is not removed by ecological knockouts.

Each predictor has exactly one frozen role. An unknown or multiply assigned predictor is a configuration error, not an invitation to infer an alias from validation behavior.

## Explicit knockout library

For every base procedure and every ecological process, v2.4 creates one candidate labeled:

```text
<base procedure>::exclude::<process>
```

The candidate reruns the full base selection/tuning procedure with every predictor assigned to the excluded process removed from its ecological candidate universe. It is not a post-fit coefficient deletion and it does not reuse the selected variables of the unablated model.

The eight frozen base procedures are the four existing strategies under the two established L2 model settings:

- all;
- iterative VIF;
- predictive forward selection;
- niche-recovery forward selection;
- each under linear `C=0.1` and degree-2 `C=1` logistic specifications.

This gives 40 explicit knockout routes before any evidence gate: 8 base procedures × 5 ecological processes.

## Discovery admission

A knockout candidate is admitted only when:

1. every declared discovery taxon × M cell contains exactly the expected outer-fold IDs;
2. every required fold has finite prediction evidence;
3. mean presence rank is at least 0.51;
4. mean presence rank minus one SEM is at least 0.50.

This is an absolute adequacy rule. A knockout need not be close to the best AUC, and AUC is not the ecological objective.

For each process, discovery evidence freezes one of three states:

- `exclusion_witness_frozen`: at least one explicit knockout route is complete and admitted;
- `required_by_frozen_discovery_contract`: all 8 routes are complete and none passes the frozen adequacy gate;
- `unresolved_discovery_evidence`: at least one route lacks complete evidence, so failure cannot be interpreted as requirement.

## Validation process certificate

An admitted knockout refutes necessity for one validation taxon only if at least one frozen knockout route fits successfully under every required M. Otherwise its transfer status is unresolved.

The final labels are:

- `refuted_as_necessary`;
- `required_by_frozen_evidence_contract`;
- `unresolved`.

The word `necessary` is deliberately asymmetric: positive necessity is never inferred merely because all retained ordinary models contain a process. The only positive label is contract-relative and requires complete failure of every explicit exclusion route under the frozen discovery rule.

## Coverage-first boundary envelope

For each retained procedure × M member, the complete fitting and selection procedure is rerun under five frozen spatial refits. Every refit produces:

- response optimum;
- lower 5% suitability-mass limit;
- upper 95% suitability-mass limit.

The raw interval is the min–max envelope across all complete retained procedure × M × refit estimates. If any expected member/refit response is absent or non-finite, the corresponding certificate is unavailable rather than silently narrowed.

## Discovery-only calibration

For each predictor × response quantity, discovery truth is opened only after the raw discovery envelope is frozen. The normalized miss is zero when truth lies within the raw interval; otherwise it is the distance to the nearest interval endpoint divided by the environmental span.

The calibration radius is the maximum normalized miss across the three discovery taxa. Validation intervals are expanded by that frozen radius times the validation environmental span on both sides. Validation truth is not used to tune or rescue the radius.

This is intentionally conservative. Width cannot compensate for undercoverage in the v2.4 decision.

## Comparators

The same validation taxa are scored with:

1. `canonical_auc_point`;
2. `complete_adequate_certificate`;
3. the unchanged `v2_3_mean_pareto_certificate`;
4. `v2_4_exclusion_calibrated_certificate`.

The v2.3 rule is reproduced as a comparator only. Its opened v2.3 outcomes do not alter v2.4.

## Unseen panels

Seeds 1–323 are excluded. Exact v2.4 panels are frozen in `configs/product_a_v2_4_exclusion_certificate_panels.json`:

- D1: discovery 371/381/391; validation 401/411/421;
- D2: discovery 372/382/392; validation 402/412/422;
- D3: discovery 373/383/393; validation 403/413/423.

## Decision states

- `exclusion_certificate_supported`;
- `exclusion_certificate_process_only`;
- `exclusion_certificate_boundary_only`;
- `exclusion_certificate_not_supported`;
- `exclusion_certificate_unavailable`.

Full support requires every panel and validation taxon to be evaluable, zero false required-process claims, possible-process recall of 1.0, boundary coverage no worse than the complete-adequate certificate, and a verified absence of validation-truth use before freeze.

A process-only result requires the process conditions but not boundary non-inferiority. A boundary-only result requires the boundary condition but not the process conditions. Neither partial state authorizes empirical confirmation.

## Stop and no-rescue rules

Do not:

- reuse known-truth seeds at or below 323 as v2.4 validation;
- change process aliases after seeing a knockout outcome;
- drop failed knockout routes from the denominator;
- treat missing evidence or a failed transferred fit as process necessity;
- choose the number of spatial refits or interval radius from validation coverage;
- replace maximum discovery miss with a smaller quantile after observing validation truth;
- relax AUC, fold, M or coverage gates to obtain support;
- promote v2.4 directly to Product-A or merge PR #1 into `main`.

Even a supported known-truth result would only permit freezing the method before a newly rebuilt empirical sealed-before-M confirmation.
