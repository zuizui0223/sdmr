# Product-A v2.3 unseen known-truth decision

- decision: `identified_set_not_supported`
- scientific promotion allowed: `False`
- source head: `6804981c1479b5bff23e5ac70f3c4af429252ee0`
- source run: `32074720946`
- artifact: `9303137688`
- artifact digest: `sha256:b9d39711ce6a3fc5d232ba56839cb99d5d71d90e3e3919a72bd9c2631b3e0723`

The discovery candidate sets were frozen before validation truth was opened. This is development known-truth evidence, not empirical Product-A promotion.

## Decision

- all three panels were evaluable;
- the Pareto certificate was narrower than the complete-adequate certificate in all three panels;
- full truth coverage failed;
- coverage was not non-inferior to the complete-adequate certificate;
- therefore the correct next action is diagnosis of coverage and sharpness, not empirical confirmation.

## Decision row

- decision: `identified_set_not_supported`
- scientific_promotion_allowed: `False`
- negative_or_trivial_outcome_accepted: `True`
- n_panels: `3`
- all_panels_available: `True`
- full_truth_coverage: `False`
- coverage_no_worse_than_complete_adequate: `False`
- pareto_no_broader_than_complete_adequate: `True`
- n_panels_with_strict_sharpness_gain: `3`
- next_action: `retain negative evidence and diagnose certificate coverage/sharpness`

## Product summary

| panel | product | n validation taxa | n complete certificates | false necessary processes | possible-process recall | possible-process precision | boundary coverage | interval width | possible processes | necessary processes | canonical point error |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| panel_C1 | canonical_auc_point | 3 | 3 | 8 | 1.0000 | 0.4667 | 0.1852 | 0.0000 | 5.0000 | 5.0000 | 0.0442 |
| panel_C1 | complete_adequate_certificate | 3 | 3 | 2 | 1.0000 | 0.4667 | 0.3333 | 0.2526 | 5.0000 | 2.3333 | — |
| panel_C1 | ecological_pareto_certificate | 3 | 3 | 8 | 1.0000 | 0.4667 | 0.3333 | 0.0556 | 5.0000 | 5.0000 | — |
| panel_C2 | canonical_auc_point | 3 | 3 | 1 | 0.7222 | 0.8333 | 0.1481 | 0.0000 | 2.0000 | 2.0000 | 0.0507 |
| panel_C2 | complete_adequate_certificate | 3 | 3 | 0 | 1.0000 | 0.4667 | 0.2963 | 0.2500 | 5.0000 | 0.0000 | — |
| panel_C2 | ecological_pareto_certificate | 3 | 3 | 0 | 1.0000 | 0.4667 | 0.2407 | 0.0963 | 5.0000 | 1.3333 | — |
| panel_C3 | canonical_auc_point | 3 | 3 | 2 | 0.5556 | 0.7222 | 0.0741 | 0.0000 | 2.0000 | 2.0000 | 0.0971 |
| panel_C3 | complete_adequate_certificate | 3 | 3 | 0 | 1.0000 | 0.4667 | 0.2963 | 0.1652 | 5.0000 | 1.0000 | — |
| panel_C3 | ecological_pareto_certificate | 3 | 3 | 0 | 1.0000 | 0.4667 | 0.2963 | 0.1464 | 5.0000 | 1.0000 | — |

## Scientific boundary

The Pareto subset produced sharper intervals, but in panel C1 it retained a false five-process necessary core and in panel C2 it reduced boundary coverage relative to the complete-adequate certificate. The procedure therefore cannot be frozen for empirical confirmation. PR #1 remains blocked from `main`.
