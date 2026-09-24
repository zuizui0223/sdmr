# SDMR v3 8x safety audit v1 — terminal development result

Status: **development-only terminal result / positive specificity and abstention are strong / ODO-unavailable state not preserved / full-system information gate required before prospective freeze**

## Frozen execution

- workflow run: `35987109202`
- workflow head: `690be530d03a68234c29f25c7f7bc46929ade09c`
- aggregate artifact: `sdmr-v3-8x-safety-audit-v1`
- artifact id: `10802923720`
- artifact digest: `sha256:2fa5e2b3661ce395a4a2523a62ca30d38b51170f3a5390dfa727d7b893138418`
- state rows: **2304**
- shards: **16/16 successful**
- sample regime: **8x = 1440 occurrences / 4800 backgrounds**
- HGB profile: **shallow3**
- ODO v2 state hash: `966d5fc5c2bc60951386c4c83e666c9a1d7fb6ae8168f2139706e49900a2943d`
- Product-A: **closed_not_reopened**
- prospective seeds opened: **none**
- fresh empirical data opened: **false**

The first workflow attempt stopped in preflight before any shard was executed because of a duplicate-column wiring bug. The bug was fixed without changing scientific logic, and this successful execution is the authoritative v1 safety result.

## Main safety result

Each split contains:
- 96 ODO-positive rows = 32 positive process cells × 3 resampling replicates;
- 840 ODO-replaceable rows;
- 72 ODO-unresolved rows;
- 144 ODO-unavailable rows;
- 72 explicit structural-refusal rows.

### random_cell — Stage-P

| endpoint | result |
|---|---:|
| positive recovery | **0.91667** |
| false positive among ODO-replaceable | **0.00000** |
| over-resolution among ODO-unresolved | **0.00000** |
| favorable positive call among ODO-unavailable | **0.00000** |
| structural-refusal violation | **0.00000** |
| structural-refusal unresolved preservation | **1.00000** |
| positive unavailable rate | **0.00000** |

### spatial — Stage-T

| endpoint | result |
|---|---:|
| positive recovery | **0.72917** |
| false positive among ODO-replaceable | **0.00000** |
| over-resolution among ODO-unresolved | **0.00000** |
| favorable positive call among ODO-unavailable | **0.00000** |
| structural-refusal violation | **0.00000** |
| structural-refusal unresolved preservation | **1.00000** |
| positive unavailable rate | **0.00000** |

Thus the 8x shallow3 regime achieves high positive recovery without creating positive false attribution or violating declared abstention boundaries.

## Exact state confusion

### random_cell

- ODO contributory → contributory: **88**
- ODO contributory → unresolved: **8**
- ODO replaceable → replaceable: **840**
- ODO unresolved → unresolved: **72**
- ODO unavailable → replaceable: **144**

### spatial

- ODO contributory → contributory: **70**
- ODO contributory → unresolved: **26**
- ODO replaceable → replaceable: **839**
- ODO replaceable → unresolved: **1**
- ODO unresolved → unresolved: **72**
- ODO unavailable → replaceable: **144**

No ODO-replaceable, unresolved, or unavailable cell was promoted to contributory/required.

## Structural refusal

All explicit refusal rows remained unresolved:

- observation_confounded / thermal: 24/24 unresolved per split;
- shared_carrier / thermal: 24/24 unresolved per split;
- shared_carrier / water: 24/24 unresolved per split.

Structural-refusal violation rate is therefore exactly zero.

## Remaining defect: ODO-unavailable collapses to replaceable

All **144 ODO-unavailable rows per split** are called `replaceable`, not `unavailable`.

These are the omitted-driver W7 cells. They do not create favorable process claims, but they create a different scientific error:

```text
declared predictor system cannot support the process-identification question
        ↓
finite procedure says
the tested process is replaceable
```

This collapses a whole-system inadequacy into a process-specific negative conclusion.

## Root-cause diagnosis

The current finite full-system adequacy check is only:

```text
mean full balanced log score >= -0.75
```

But the equal-prior null model has score:

```text
-log(2) = -0.693147...
```

At 8x, W7 omitted-driver full models pass the loose -0.75 absolute floor while providing no information above the null:

### random_cell W7

- mean full score: **-0.69708**
- mean gain over null: **-0.00393**
- positive-gain rate: **0 / 24**

### spatial W7

- mean full score: **-0.69970**
- mean gain over null: **-0.00656**
- positive-gain rate: **1 / 24**

By contrast, under random_cell every non-W7 world has positive full-model gain over null in 24/24 world-seed-replicate cases.

Representative means:

- unique_process: +0.04094 nats
- redundant_representation: +0.04087
- null_correlated: +0.03900
- shared_carrier: +0.03452
- geographic_shift: +0.03507
- interaction: +0.05261
- observation_confounded: +0.00598

This suggests a missing **full-system information adequacy gate** rather than a process-margin problem.

## Decision

**8x remains the candidate sample-size regime, but prospective freezing is blocked until whole-system unavailability is handled fail-closed.**

The next development step is to test a natural zero-information gate:

> before classifying any process, require positive evidence that the full declared predictor system improves held-out balanced log score over the equal-prior null score (-\log 2).

This gate must:
- operate before process-specific classification;
- use the same fold uncertainty convention as the process evidence;
- leave the 0.01 process-information margin unchanged;
- preserve W6 observation-confounding and shared-carrier refusal semantics;
- make W7 unavailable rather than replaceable;
- be evaluated on burned development evidence only.

No threshold may be tuned against W7 beyond the natural null-information boundary of zero gain.

No v1 safety result is prospective evidence.
