# SDMR v6 magnitude-permutation confirmation v1 — terminal result

Status: **development confirmation PASS / full-pipeline integration authorized / prospective seeds remain unopened**

## Frozen execution

- workflow run: `36121116341`
- workflow head: `a7873b05b9b9a3b3a4408a7421b562413a8ae1bd`
- terminal artifact: `sdmr-v6-magnitude-permutation-confirmation-v1`
- artifact id: `10858132902`
- artifact digest: `sha256:70e5a02d7a74494915dc3e06e505fd59fc9c8f3caa2eb51eba15559f757ae956`
- validation prerequisite: workflow `36088891887`, artifact digest `sha256:f9dc1b593e77a33648d494a784aded984669830cc587da0f06825277ff25328e`
- confirmation seeds: **72001–72050**
- integration seeds 73001–73020 opened: **false**
- prospective seeds 74001–74020 opened: **false**
- fresh empirical data opened: **false**

## Frozen rule

```text
mean full balanced log score >= -0.75
AND mean gain over -log(2) >= 0.01
AND held-out permutation p <= 0.001
```

with:
- B = 999
- alpha = 0.001
- permutation seed = 0
- shallow3 HGB
- 8x finite sample
- random_cell Stage-P

No rule changed after validation.

## Independent confirmation

| world | authorized |
|---|---:|
| unique_process | **50 / 50** |
| redundant_representation | **50 / 50** |
| shared_carrier | **50 / 50** |
| null_correlated | **50 / 50** |
| interaction | **50 / 50** |
| geographic_shift | **50 / 50** |
| observation_confounded | 2 / 50 — report-only |
| omitted_driver | **0 / 50** |

Frozen PASS:
- W7 = 0 / 50
- every informative control >=48 / 50
- W6 report-only
- strict conjunction

Decision: **PASS**.

## Sequential v6 evidence

Validation 71001–71100:
- W7: 0/100
- each informative control: 100/100
- W6: 1/100 report-only

Independent confirmation 72001–72050:
- W7: 0/50
- each informative control: 50/50
- W6: 2/50 report-only

The combined 150-seed description is not treated as a new pooled inferential denominator.

## Decision

The v6 magnitude-permutation authorization gate is retained unchanged.

The next admissible panel is the already pre-frozen full-pipeline integration denominator:

```text
73001–73020
```

Integration must test complete Stage-P process-state recovery and Stage-T spatial transfer under the frozen INT-B–INT-F conjunction.

Prospective seeds `74001–74020` remain unopened until integration passes.
