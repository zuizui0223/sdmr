# SDMR v3 shallow3 8x positive-power tail v2 — terminal development result

Status: **development-only terminal result / recovery still increases materially beyond 4x / 8x promoted to candidate sample-size regime for safety testing / no prospective freeze**

## Frozen execution

- workflow run: `35981741906`
- workflow head: `62c85b38488c0c8efe5bd8476b0dd81618e01cfe`
- HGB profile: **shallow3**
- ODO v2 state hash: `966d5fc5c2bc60951386c4c83e666c9a1d7fb6ae8168f2139706e49900a2943d`
- multiplier: **8x = 1440 occurrence / 4800 background records**
- resampling replicates: **3**
- positive denominator: **32 ODO-positive process cells × 3 replicates = 96 rows per split**
- Product-A: **closed_not_reopened**
- prospective seeds opened: **none**
- fresh empirical data opened: **false**

Artifacts:

- spatial: artifact `10801581626`, digest `sha256:d5ffb683b8a3dc0eba12cc6a8515755cbdbc823f65f09bd28ec82744f283fbe7`
- random_cell: artifact `10801478002`, digest `sha256:bb9e8d8fb9b416424b460d6b2cace75feee85cddfedadf6c1f8ebdc5355c5985`

## Main result

### random_cell Stage-P

| multiplier | positive recovery | unresolved | replaceable | unavailable | mean delta | mean SEM |
|---|---:|---:|---:|---:|---:|---:|
| 4x | 0.71875 | 0.25000 | 0.03125 | 0 | 0.01777 | 0.00399 |
| **8x** | **0.85417** | **0.14583** | **0.00000** | **0** | 0.01736 | **0.00272** |

The 4x → 8x gain is **+0.1354** in positive recovery. This is too large to call a practical plateau.

### spatial Stage-T

| multiplier | positive recovery | unresolved | replaceable | unavailable | mean delta | mean SEM |
|---|---:|---:|---:|---:|---:|---:|
| 4x | 0.61458 | 0.34375 | 0.04167 | 0 | 0.02038 | 0.00789 |
| **8x** | **0.70833** | **0.29167** | **0.00000** | **0** | 0.02115 | **0.00740** |

Spatial recovery also increases materially, by **+0.09375**.

## Process-level result at 8x

### random_cell

- thermal: **0.80556**
- water: **1.00000**

### spatial

- thermal: **0.62500**
- water: **0.95833**

Water-process information is effectively saturated under the random-cell Stage-P denominator. Thermal information remains the harder process class.

## World-level result at 8x

### random_cell

- unique_process: **0.91667**
- interaction: **0.89583**
- geographic_shift: **0.70833**

### spatial

- unique_process: **0.58333**
- interaction: **0.91667**
- geographic_shift: **0.41667**

The dominant residual hard family is **geographic_shift thermal**. Its weaker recovery is consistent with its smaller ODO population gap, which lies closer to the fixed 0.01 process-information margin.

## Interpretation

The tail diagnostic strengthens the power-limited interpretation.

- recovery rises again from 4x to 8x;
- uncertainty continues to shrink;
- mean process loss remains above the fixed 0.01 margin overall;
- unavailable and false-replaceable states disappear from the positive denominator at 8x;
- random-cell Stage-P recovery reaches ~85%.

Therefore 4x was underpowered for the intended process-identification task.

The 8x regime is now the **candidate development sample size** for prospective known-truth design, but it is not yet prospectively frozen.

## Required safety check before any freeze

The positive-only power curve cannot establish specificity.

Before selecting 8x for a prospective contract, run an 8x development-only safety audit on:

- ODO `replaceable` cells: false-positive rate;
- ODO `unresolved` cells: over-resolution rate;
- ODO `unavailable` cells: no favorable coercion;
- observation-confounded and identical-shared-closure cells: refusal preservation.

Run shallow3 at both:
- `random_cell` Stage-P;
- `spatial` Stage-T.

The same margin, adequacy floor, process closures, ODO target, ecological seeds, and three resampling replicates must be retained.

Only if safety remains controlled may 8x become the candidate sample-size regime for prospective KT threshold design.

No v2 tail result is prospective evidence.
