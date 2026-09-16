# Sealed answer-check superiority separator v26 — prospective contract

## Status

v26 is a **new prospective successor** to the failed v25 non-inferiority separator. It does not edit, reinterpret, or tune v25.

The scientific rule in this document is frozen before any v26 fresh outcome is opened.

## Motivation and new estimand

v25 showed that

> process knockout is predictively non-inferior on an independent outcome source

is not separating evidence for process absence: on the consumed 17001–17010 denominator, v25 removed 52 true members and 29 false members.

v26 asks a stronger question:

> Is removal of the process consistently **predictively superior** to retaining it on a source-disjoint sealed outcome source?

A v26 exclusion is therefore evidence that the retained process representation is predictively harmful under the frozen model family and transfer design. It is not, by itself, a causal proof that the biological process is absent.

## Frozen fresh denominator

- known-truth families: `gaussian`, `asymmetric`, `soft_threshold`, `interaction`, `omitted_driver`, `observation_confounded`
- fresh seeds: integers `20001–20020`, inclusive
- true processes for terminal scoring only: `temperature`, `water`
- false-control processes for terminal scoring only: `seasonality`, `noise`
- seed replacement: forbidden
- family replacement: forbidden
- null/failed cases remain in the denominator

The 20001–20020 range was checked against the current repository/config and PR history before freeze and had no prior use. The consumed 17001–17010 and 18001–18010 denominators are excluded from v26 performance claims.

## Upstream support/set construction

Fresh v26 must reproduce the existing inference chain without opening truth:

1. generate fresh known-truth data for the frozen family/seed denominator;
2. construct v21 two-tier support using the same support machinery and thresholds;
3. construct v23 context sets exactly with `set_valued_attribution_v23.build_context_sets` from v21 `supported` and `high_confidence_supported` booleans;
4. generate v26 sealed answer-check superiority evidence only for members of the v23 supported set;
5. apply the unchanged v24 set-contraction operator;
6. persist the truth-blind refined sets and an immutable receipt;
7. only then open generating-process truth for terminal scoring.

v22 pairwise rankings are not inputs to v26.

## Evidence source and leakage guard

v26 inherits the v25 evidence-source architecture:

- v21 support is built from occurrence `model_pool` rows only;
- the answer-check occurrence identities are sealed before environmental feature use;
- baseline and process-excluded models are fitted without answer-check outcomes;
- a deterministic prediction/selection receipt is frozen before answer-check opening;
- answer-check occurrence rows are materialized only after that receipt exists;
- separator background rows are source-disjoint from the v21 support background and occurrence rows;
- exclusion removes the full declared process-information closure (e.g. `temperature` and `temp_proxy` together).

A violation of source disjointness, model-freeze ordering, required model roster, or coverage fails closed.

## Frozen superiority rule

For each v23-supported family × seed × process, and for every required frozen model specification, compute sealed-block deltas

`delta_b = excluded_density_log_score_b - baseline_density_log_score_b`.

For model specification `m`:

- `mean_delta_m` = arithmetic mean of finite complete block deltas;
- `sem_delta_m` = sample SD divided by square root of the number of complete sealed blocks;
- `lower_superiority_m = mean_delta_m - 1.96 * sem_delta_m`.

The **1.96 SEM multiplier is frozen prospectively for v26**. It was motivated by a post-v25 consumed-data diagnostic and is therefore development-calibrated, not independently derived. That consumed diagnostic may not be counted as v26 validation evidence.

Evidence states:

- `exclude`: every required model specification is complete and has `lower_superiority_m > 0`;
- `compatible`: complete evidence exists and at least one required model has `mean_delta_m + 1.96 * sem_delta_m <= 0`;
- `indeterminate`: complete evidence exists but neither rule above holds;
- `unavailable`: required model roster or coverage is incomplete.

The zero boundary is fixed. There is no post-outcome positive margin, process-specific threshold, or family-specific threshold.

Only `exclude` may remove a v23 member through the unchanged v24 operator.

## Coverage

Inherited from v25:

- at least 10 complete sealed answer-check occurrences per family/seed separator case;
- at least 2 distinct sealed answer-check spatial blocks;
- all frozen model specifications must produce complete baseline and excluded scores.

Coverage failure is `unavailable`, never evidence of process absence.

## Prospective success gate

v26 passes the known-truth prospective gate only if all of the following hold on the complete frozen denominator:

1. removed true members = **0**;
2. contexts with any true-member deletion = **0**;
3. removed false members >= **1**;
4. every reported removal comes from qualified source-disjoint evidence with the frozen model roster;
5. failed/null cases remain represented in the denominator and cannot be silently dropped.

No threshold may be changed after outcomes are opened.

A pass would show that this particular superiority separator can contract at least one false supported member without false deletion on this frozen known-truth denominator. It would **not** establish universal process identification or authorize a causal claim.

A fail closes v26 as another negative endpoint. No replacement rule may be fit to the same 20001–20020 outcome denominator and called prospective.

## Determinism

Truth-blind construction must be reproducible from frozen seeds and configuration. Discrete support/set/evidence states must match on an independent rerun before terminal truth scoring is accepted. Numerical comparisons use deterministic model specifications already frozen upstream.

## Hard stops

- do not change v21 support thresholds;
- do not use v22 pairwise winners;
- do not alter v23 set construction;
- do not relax the `1.96` multiplier or zero superiority boundary after outcomes;
- do not select favorable families, seeds, processes, contexts, or spatial blocks;
- do not use 17001–17010 or 18001–18010 as fresh v26 performance evidence;
- do not call a v26 refined set a formal confidence set, exhaustive identified set, or causal identified set.
