# SDMR v3 Stage-P safety v3 — terminal development result

Status: **development prerequisite passed / prospective KT v3 may be activated**

## Provenance

Scientific shard run:
- workflow run: `35992320576`
- scientific shards: **8/8 success**
- shards recomputed during repair: **false**

Aggregate-only repair:
- workflow run: `35997608669`
- artifact: `sdmr-v3-stage-p-safety-v3-repaired-aggregate`
- artifact id: `10806253612`
- artifact digest: `sha256:4a7174bdb701225de22c5735a80923df0a37944ec071f90f421662fc105e4847`

The original aggregate failure was not scientific. It came from hashing 17-digit CSV floating-point strings. Positive-tail semantic states were identical, and the maximum numeric difference was approximately `1.1e-16`. The repaired aggregate uses exact semantic hashing plus a 14-decimal numerical hash.

## Frozen development design

- ODO v2 target unchanged
- shallow3 HGB unchanged
- 8x = 1440 occurrence / 4800 background records
- three development resampling replicates
- Stage P = random_cell
- margin = 0.01
- adequacy floor = -0.75
- SEM multiplier = 1
- full-system information gate:
  - full mean score >= -0.75
  - lower gain over equal-prior null > 0
- Product-A remains closed
- no prospective seeds opened

## Stage-P result

Across 1,152 process rows:

| endpoint | result |
|---|---:|
| ODO-positive recovery | **0.85417** |
| false-positive rate among ODO-replaceable | **0.00000** |
| over-resolution among ODO-unresolved | **0.00000** |
| sharp-state rate among ODO-unavailable | **0.00000** |
| favorable-positive rate among ODO-unavailable | **0.00000** |
| structural-refusal violation rate | **0.00000** |
| positive unavailable rate | **0.00000** |

State counts:
- ODO positive: 96
- ODO replaceable: 840
- ODO unresolved: 72
- ODO unavailable: 144
- structural-refusal cells: 72

Finite states:
- contributory: 82
- unresolved: 85
- replaceable: 835
- unavailable: 150

## Full-system information gate

| world | adequacy |
|---|---:|
| unique_process | 24/24 |
| redundant_representation | 24/24 |
| shared_carrier | 24/24 |
| null_correlated | 24/24 |
| interaction | 24/24 |
| geographic_shift | 24/24 |
| observation_confounded | **23/24** |
| omitted_driver | **0/24** |

Thus:
- non-W7 adequacy = **167/168 = 0.99405**
- W7 omitted-driver adequacy = **0/24 = 0**

The full-system gate therefore fixes the prior `unavailable → replaceable` failure mode without sacrificing positive recovery.

## Positive-tail identity

Compared with the previously frozen 8x positive-power tail:

- semantic hash:
  `16fcea7cc49c64bb3f90f7f6f43fd93803286bc740f2b6eab228c6760666ebe5`
- 14-decimal numeric hash:
  `da8bc77209c2e08bbc598d0591670b27739bd1c39b4f4bfed351ba3bee1c64c7`

Both match exactly.

## Decision

The development prerequisite for prospective KT v3 is **passed**.

The already-frozen prospective contract may now be activated without modifying:
- seeds;
- worlds;
- sample size;
- learner;
- process margin;
- adequacy floor;
- full-system gate;
- KT-A–KT-F thresholds.

Prospective seeds `33001–33020` remain unopened until the activation receipt is committed.
