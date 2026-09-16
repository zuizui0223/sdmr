# Sealed answer-check separator v25 — consumed-development result

## Endpoint

v25 is a **negative development endpoint**. It must not be promoted to fresh validation or empirical use.

The separator used spatially sealed answer-check occurrences that were unavailable to v21 support construction. Baseline and process-excluded routes were fitted and frozen before answer-check opening, and the truth-blind v24 refinement was written before known truth was scored.

Authoritative development workflow: `35085028243`.

## Frozen denominator

- six known-truth families
- consumed seeds `17001–17010`
- 480 context rows
- 467 v23-supported context/process members
- process truth for this diagnostic: `temperature` and `water` true; `seasonality` and `noise` false

No fresh seed was allocated or opened.

## Result

The v25 non-inferiority separator contracted 15.83% of contexts and removed 81 supported members.

- true base members: 424
- false base members: 43
- removed true members: **52 / 424 = 12.26%**
- removed false members: **29 / 43 = 67.44%**
- contexts with at least one true deletion: **10.83%**
- exact truth-set rate after refinement: **16.88%**
- mean set-size contraction: **0.16875**

The predeclared safety screen required zero true-member deletions and at least one false-member deletion. It therefore **failed**.

`development_advancement_screen_passed = false`

`prospective_contract_freeze_authorized = false`

`fresh_seed_allocation_authorized = false`

`fresh_validation_authorized = false`

`empirical_validation_authorized = false`

## Failure localization

False deletion was not confined to singleton v23 sets.

| v23 base set size | true members | true members removed | removal rate |
|---:|---:|---:|---:|
| 1 | 193 | 25 | 12.95% |
| 2 | 201 | 23 | 11.44% |
| 3 | 30 | 4 | 13.33% |

The error was process-asymmetric:

- `temperature`: 13 true deletions
- `water`: 39 true deletions

The highest family-level true-member deletion rates were `interaction` (16/67, 23.88%) and `observation_confounded` (13/55, 23.64%).

The global separator did not fail simply because a true process was supported in too few contexts. Among true family/seed/process cases, the mean fraction of the eight v23 contexts supporting that process was essentially the same for global `exclude` cases (0.464) and non-`exclude` cases (0.465).

## Root-cause interpretation

v25 asked whether removing a process is *non-inferior for sealed predictive transfer*. That is not a separating statement about whether the process is truly active.

The implementation is intentionally indexed by family × seed × process, then copied to every v23 context supporting that process. That cross-context scope contributes a mismatch with context-indexed v23 support, but dilution alone does not explain the observed false deletions: true-process exclusion occurred across the full range of support prevalence.

The stronger diagnosis is therefore structural:

> `process knockout is predictively non-inferior on an independent outcome source` does not imply `the process is absent`.

This is consistent with the broader SDMR identification boundary: independent predictive evidence can still be compatible with multiple ecological process explanations.

## Diagnostic signal for a successor

On the consumed family/seed/process cases, the mean sealed density-score delta had substantial overlap between true and false processes (diagnostic AUC about 0.71 for false-vs-true process status). The v25 `exclude` state classified 18 false global cases and 14 true global cases.

A qualitatively stronger contrast is available without editing v25: require process exclusion to be demonstrably *better*, not merely non-inferior. In a post-endpoint diagnostic only, requiring every frozen model specification to have a lower 1.96-SEM delta bound above zero selected one false global case and zero true global cases. This observation is **not** a v25 result and does not authorize a threshold change inside v25. It may only motivate a separately frozen successor evaluated on unused evidence.

## Governance

v25 remains frozen as the failed non-inferiority separator. Do not:

- relax or tighten its 0.01-nat margin after this result;
- reinterpret the consumed denominator as prospective evidence;
- reuse seeds `17001–17010` to claim successor performance;
- authorize empirical validation from v25.

Any successor must define its new estimand and decision rule in a new contract before opening unused validation outcomes.
