# SDMR v3 shallow3 positive-recovery power curve v1 — terminal development result

Status: **development-only terminal result / finite information is a major limiting factor / recovery still rising at 4x / no prospective freeze**

## Frozen execution

- workflow run: `35976809272`
- workflow head: `d53a1bc4f549b461f59b478ae580263ca54bc1a6`
- program: `sdmr-v3-shallow3-positive-power-v1`
- config SHA-256: `b619b0c83b45c7bb3452aeed705d6c258b46dd5052308fff45e83c0d7fbf4bd0`
- ODO v2 state hash: `966d5fc5c2bc60951386c4c83e666c9a1d7fb6ae8168f2139706e49900a2943d`
- HGB profile: **shallow3**
- ODO-positive denominator: **32 cells**
- resampling replicates per multiplier: **3**
- Product-A: **closed_not_reopened**
- prospective seeds opened: **none**
- fresh empirical data opened: **false**

Each split × multiplier was executed as a separate shard. Artifact digests:

- random_cell 1x: `sha256:17ccf1674afc6fd2eedb319427bf04b3400004edfff6739da0e63a8a002bc5a4`
- random_cell 2x: `sha256:1f8bb9ef2ab04f6c5b53a0ec68a4c5c05747b3ea33f635e789853cfd1fb50960`
- random_cell 4x: `sha256:b44a885b0115af724094ee7863af40947d85383c8f90d27801a73bbf6b4d7bd1`
- spatial 1x: `sha256:567e06517d0558492bb9a02b66b4adef2afc1d667b1fea903e2a887defb3da04`
- spatial 2x: `sha256:48d6a93e99f63e5d7382ffc0fefd849acac1e730f7df058b67d5b09dcd90e667`
- spatial 4x: `sha256:6c9cd514eabcd3d1aa55b7c1ea38156ae1c6c9e11122952a9aa57da9a171c307`

## Main result

### random_cell — within-support Stage-P identification

| sample multiplier | occurrence/background | positive recovery | unresolved | replaceable | unavailable | mean delta | mean SEM |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1x | 180 / 600 | **0.3750** | 0.5000 | 0.1250 | 0 | 0.01399 | 0.00977 |
| 2x | 360 / 1200 | **0.5833** | 0.3646 | 0.0521 | 0 | 0.01834 | 0.00572 |
| 4x | 720 / 2400 | **0.7188** | 0.2500 | 0.0313 | 0 | 0.01777 | 0.00399 |

Recovery increases monotonically while SEM falls by about 59% from 1x to 4x.

### spatial — geographic-transfer challenge

| sample multiplier | occurrence/background | positive recovery | unresolved | replaceable | unavailable | mean delta | mean SEM |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1x | 180 / 600 | **0.3958** | 0.4167 | 0.1667 | 0.0208 | 0.01742 | 0.01358 |
| 2x | 360 / 1200 | **0.4375** | 0.4688 | 0.0938 | 0 | 0.01725 | 0.01098 |
| 4x | 720 / 2400 | **0.6146** | 0.3438 | 0.0417 | 0 | 0.02038 | 0.00789 |

Spatial recovery also improves by 4x, though less cleanly than random_cell.

## Process-level pattern

### random_cell

Thermal:
- 1x: 0.347
- 2x: 0.514
- 4x: **0.653**

Water:
- 1x: 0.458
- 2x: 0.792
- 4x: **0.917**

### spatial

Thermal:
- 1x: 0.389
- 2x: 0.417
- 4x: **0.556**

Water:
- 1x: 0.417
- 2x: 0.500
- 4x: **0.792**

Water/interacting-process information is therefore already highly recoverable at 4x, while thermal information remains more demanding.

## World-specific pattern

At 4x:

### random_cell
- unique_process: **0.750**
- interaction: **0.833**
- geographic_shift: **0.458**

### spatial
- unique_process: **0.583**
- interaction: **0.813**
- geographic_shift: **0.250**

The remaining difficulty is not uniform. Interaction and ordinary unique-process cells respond strongly to increasing n. Geographic-shift thermal remains the hard family.

The ODO population deltas explain part of this difference:

- geographic_shift thermal mean ODO delta ≈ **0.0170**
- unique_process thermal ≈ **0.0200**
- interaction thermal ≈ **0.0326**
- interaction water ≈ **0.0415**

Thus geographic-shift operates closest to the fixed 0.01 biological margin even before finite sampling.

## Interpretation

The v1 curve supports a strong finite-information/power component:

1. full-model adequacy remains stable and unavailable calls disappear;
2. positive recovery rises with n;
3. uncertainty decreases strongly with n;
4. mean paired process loss remains above the 0.01 margin overall rather than collapsing toward zero.

The unresolved fraction is therefore not primarily a no-effect outcome.

However, 4x is still on the rising portion of the curve. It would be premature to freeze 720/2400 as the prospective known-truth sample size without checking whether recovery is approaching an asymptote.

## Stage separation

The development evidence now favors an explicit separation:

- **Stage P:** within-support process identification, represented by random_cell cross-fitting;
- **Stage T:** spatial/geographic transfer, retained as a distinct outer guardrail.

Spatial performance remains important, but it should not be averaged with random_cell into a single process-state metric.

## Decision

**Do not freeze the prospective denominator yet.**

Run one development-only **8x tail diagnostic** with shallow3:

- 1440 occurrences / 4800 backgrounds;
- same 32 ODO-positive cells;
- same three resampling replicates;
- spatial and random_cell kept separate;
- unchanged margin/floor/SEM rule/profile/ODO target.

Purpose: determine whether recovery is still rising materially beyond 4x or has reached a practical plateau.

After that:
- if 8x adds little, use the plateau to design the prospective power requirement;
- if 8x adds substantial recovery, sample size remains the primary design lever;
- geographic-shift must be reported separately because its population gap is closest to the decision margin.

This remains development evidence only.
