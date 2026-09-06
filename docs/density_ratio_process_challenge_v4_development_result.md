# Density-ratio process challenge v4 — development result

## Status

Post-outcome development only. This result is **not** prospective performance evidence and does not reopen Product A.

The development algorithm and thresholds were fixed before this run:

- burned development seeds `13001–13010` across six known-truth families (`60` cases);
- rank relative non-inferiority margin `0.02`;
- balanced presence/background density-ratio log-score non-inferiority margin `0.01` nats;
- density SEM multiplier `1.0`;
- probability clipping epsilon `1e-6`;
- v3.2 shared-carrier attribution unchanged.

The density score is an equal-prior presence/background discrimination score. It is **not** interpreted as absolute occurrence probability.

## Authoritative development run

- Workflow: `density-ratio-process-challenge-v4-development`
- Run: `34024183605`
- Aggregate artifact: `9986631789`
- Artifact digest: `sha256:71934efa1f7676bce7c463c8ad95a29e994f1811db1d2c6d07ef4e15dc7c0721`
- Cases: `60`
- Process cells: `300`

All six family jobs and the aggregate completed successfully after the fail-closed `model_label × route × fold` evidence-key checks passed.

## Result

Compared with v3.2 on the same burned development denominator:

| metric | v3.2 | v4 |
|---|---:|---:|
| true-process challenge recall | 86/130 = 0.661538 | 92/130 = 0.707692 |
| false-process challenge rate | 4/170 = 0.023529 | 13/170 = 0.076471 |
| true unique-attribution recall | 82/130 = 0.630769 | 81/130 = 0.623077 |
| false unique-attribution rate | 1/170 = 0.005882 | 5/170 = 0.029412 |
| false-required rate | 0 | 0 |

The v4 status changed from v3 in `15` process cells.

### Fifteen v4 status changes

True generating processes newly changed from `replaceable` to `contributory` (`6`):

- temperature: `5`
  - gaussian seed `13005`
  - observation_confounded seeds `13001`, `13002`, `13004`, `13007`
- water: `1`
  - omitted_driver seed `13010`

Non-generating processes newly changed from `replaceable` to `contributory` (`9`):

- seasonality: `8`
  - asymmetric `13008`
  - gaussian `13001`
  - observation_confounded `13003`, `13008`
  - omitted_driver `13006`, `13009`
  - soft_threshold `13005`, `13010`
- soil: `1`
  - soft_threshold `13005`

The new false seasonality challenge signals also altered shared-carrier attribution. Seven previously uniquely attributed true water signals became `contested_shared_information`:

- asymmetric `13008`
- gaussian `13001`
- observation_confounded `13003`, `13008`
- omitted_driver `13009`
- soft_threshold `13005`, `13010`

This explains why raw challenge recall improved while unique-attribution recall slightly declined.

## Fixed concordance diagnostic

The 15 changed cells were then diagnosed without changing any margin or process status rule.

- Workflow: `density-ratio-v4-concordance-diagnostic`
- Run: `34026164932`
- Aggregate artifact: `9987194174`
- Artifact digest: `sha256:ccb093daa2c3d16bec26681320b585e936bbae34b2e4eb540e4339607618db7c`
- Selection: all and only the 15 cells where `v4_changed_from_v3 == true`
- Refit: same burned cases, same v4 configuration, all matched model/process routes

A simple directional-concordance rescue was **not supported**:

- among the 6 true changed cells, only `1/6` had rank loss in the same negative direction for all density-rejected v3 witness routes;
- among the 9 false changed cells, `4/9` had that all-route rank-direction agreement;
- using an `any-route` rule gives `1/6` true versus `5/9` false.

Thus requiring rank and density to point in the same direction would preferentially discard the true additions rather than the false ones.

### More important: v4 confused uncertainty with positive loss evidence

For each density-rejected v3 witness route, define the symmetric development uncertainty band as

`mean_delta ± 1 × SEM`.

A route would actively demonstrate loss beyond the frozen `0.01`-nat margin only if its **upper** band were below `-0.01`.

That did not happen for the v4 additions:

- `14/15` changed process cells had **zero** density-rejected witness routes with established inferiority beyond `0.01` nats;
- the remaining true-water cell (`omitted_driver`, seed `13010`) had only `1/3` such routes, so a viable route remained indeterminate rather than refuted.

In other words, the added v4 `contributory` calls were generated because non-inferiority was *not established*, not because inferiority was established.

This is a logical state error, not a threshold-calibration problem:

`failure to establish non-inferiority != evidence of meaningful inferiority`.

It directly conflicts with SDMR's abstention principle, under which incomplete or indeterminate evidence must remain unresolved rather than be promoted to a positive ecological claim.

## Decision

**v4 is not promoted as an improvement over v3.2.**

The `0.01`-nat margin will not be tuned against these outcomes. The proposed directional-concordance rule is also rejected by the fixed diagnostic.

The next learner must make paired relative evidence explicitly three-state:

1. `noninferior`: the lower uncertainty bound is at or above `-margin`;
2. `inferior`: the upper uncertainty bound is below `-margin`;
3. `indeterminate`: the interval overlaps `-margin`.

At process level:

- an established non-inferior route can support `replaceable`;
- `contributory` requires positive evidence that all otherwise viable process-free routes are meaningfully inferior;
- any viable indeterminate route forces `unresolved` rather than `contributory`;
- `required` remains reserved for complete process exclusion with no absolutely adequate route.

This is a state-space correction, not a margin rescue. Any performance claim for that successor requires a new unused prospective denominator after development is frozen.
