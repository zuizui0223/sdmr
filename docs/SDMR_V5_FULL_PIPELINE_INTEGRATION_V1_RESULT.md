# SDMR v5 full-pipeline integration v1 — terminal result

Status: **development integration FAIL / INT-E only / prospective KT remains unopened**

## Frozen execution

- workflow run: `36082238336`
- workflow head: `2f802e22b5a09774fccee94e49f514dc67d15d77`
- terminal artifact: `sdmr-v5-full-pipeline-integration-v1`
- artifact id: `10842358603`
- artifact digest: `sha256:01506d0643cdb79e37111650c9a6ad5f43eb2c50fff064055eb7b828c1ec6326`
- integration seeds: **61001–61020**
- prospective seeds 53001–53020 opened: **false**
- fresh empirical data opened: **false**

## Frozen gate result

- INT-A: PASS
- INT-B: PASS
- INT-C: PASS
- INT-D: PASS
- INT-E: **FAIL**
- INT-F: PASS

Strict conjunction: **FAIL**.

## Metrics

- Stage-P positive recovery: **0.925**
- false-positive rate among ODO-replaceable: **0**
- over-resolution among ODO-unresolved: **0**
- structural-refusal violation: **0**
- unavailable favorable-positive rate: **0**
- unavailable sharp-state rate: **0.05**
- non-W7 full-system authorization: **1.00**
- W7 full-system authorization: **0.05**
- Stage-P-positive → spatial-replaceable contradiction: **0.01351**
- spatial structural-refusal violation: **0**

## Exact INT-E failure

Only:

`seed 61014 / omitted_driver`

Full-system permutation gate:

- observed mean balanced log score = **-0.691131**
- mean gain over -log(2) = **+0.002016**
- permutation p = **0.001**
- exceedances among 999 permutations = **0**
- absolute adequacy = PASS
- positive gain = PASS
- permutation significance = PASS

Therefore the full system was authorized and all six ODO-unavailable process states became `replaceable`.

All other W7 seeds were correctly `unavailable`.

## Interpretation

This is not a wiring failure. The frozen v5 permutation gate itself produced one finite-data false authorization.

The failure reveals a scale mismatch:

- process-specific meaningful information margin = **0.01**
- full-system authorization required only **gain > 0**

Thus a total full-system gain of only **0.002** could authorize process-specific negative claims whose own meaningful-loss criterion is 0.01.

## Non-retroactivity

v5 integration remains failed.

Prohibited:
- changing alpha/B and rescoring 61001–61020;
- replacing seed 61014;
- relaxing INT-E;
- opening 53001–53020 under v5.

Seeds 61001–61020 are burned for postmortem/development only.

## Next design

SDMR v6 retains the independently validated permutation p-value gate but adds a **full-system information magnitude floor equal to the existing process-information margin 0.01**.

Authorization becomes:

```text
mean full score >= -0.75
AND mean gain over -log(2) >= 0.01
AND permutation p <= 0.001
```

The value 0.01 is not tuned to seed 61014; it is the already-frozen scientific margin used to define meaningful process information throughout SDMR v3–v5.

The revised rule must be validated, independently confirmed, and re-integrated on entirely unused seed panels before any prospective activation.
