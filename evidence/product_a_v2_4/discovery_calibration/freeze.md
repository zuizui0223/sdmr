# Product-A v2.4 discovery refit and calibration freeze

## Immutable source

- calibration run: `32099494627`
- calibration head: `54ced575b0751fa7c2ca18fb2544badc6643f37c`
- calibration artifact: `9311087568`
- artifact digest: `sha256:2fad05bc40af18292ff1fb24c2580ef5c603338da302f168cb130299a126363b`
- model-only refit run: `32098266084`
- refit source head: `72ee499f808fb8eefb054bfaac95c5f086aacdb1`
- source worker artifacts: `54`

The old source run's aggregate job was superseded, but all 54 matrix refit jobs and their artifacts were independently verified successful before reuse. No candidate, threshold, seed, process alias, M, fold, response quantity or refit denominator changed.

## Information barrier

- all raw discovery envelopes frozen before generating truth was opened: `true`
- discovery truth opened only for calibration after the raw freeze: `true`
- validation taxa simulated or read: `false`
- validation truth read: `false`
- real empirical data read: `false`
- old external-sealed outcomes read: `false`
- calibration uses validation truth: `false`

## Completeness

- expected procedure × M × fit members: `5130`
- successful members: `5130`
- raw product intervals: `216`
- complete raw intervals: `216`
- calibration keys: `18`
- complete calibration keys: `18`
- validation stage allowed: `true`

## Discovery response coverage

| panel | product | raw boundary coverage | mean raw normalized width | calibrated v2.4 coverage | calibrated v2.4 width |
|---|---|---:|---:|---:|---:|
| D1 | canonical AUC point | 0.1667 | 0.0000 | — | — |
| D1 | complete adequate | 0.2222 | 0.1192 | — | — |
| D1 | v2.3 mean Pareto | 0.2222 | 0.0840 | — | — |
| D1 | v2.4 exclusion/refit envelope | 0.7778 | 0.3289 | 1.0000 | 0.3416 |
| D2 | canonical AUC point | 0.1111 | 0.0000 | — | — |
| D2 | complete adequate | 0.3889 | 0.2310 | — | — |
| D2 | v2.3 mean Pareto | 0.2778 | 0.0621 | — | — |
| D2 | v2.4 exclusion/refit envelope | 0.7222 | 0.3278 | 1.0000 | 0.3631 |
| D3 | canonical AUC point | 0.0556 | 0.0000 | — | — |
| D3 | complete adequate | 0.5000 | 0.2662 | — | — |
| D3 | v2.3 mean Pareto | 0.3889 | 0.0971 | — | — |
| D3 | v2.4 exclusion/refit envelope | 0.6111 | 0.3129 | 1.0000 | 0.3325 |

The calibrated discovery coverage of 1.0 is a construction check, not validation evidence: each radius is the maximum normalized miss among the three discovery taxa in that panel. Its transfer performance is still completely unknown.

## Frozen normalized expansion radii

| panel | response key | radius |
|---|---|---:|
| D1 | temperature lower limit | 0.000000 |
| D1 | temperature optimum | 0.000000 |
| D1 | temperature upper limit | 0.018713 |
| D1 | water lower limit | 0.019151 |
| D1 | water optimum | 0.000000 |
| D1 | water upper limit | 0.000000 |
| D2 | temperature lower limit | 0.039584 |
| D2 | temperature optimum | 0.000000 |
| D2 | temperature upper limit | 0.037788 |
| D2 | water lower limit | 0.025649 |
| D2 | water optimum | 0.000000 |
| D2 | water upper limit | 0.002671 |
| D3 | temperature lower limit | 0.003469 |
| D3 | temperature optimum | 0.000000 |
| D3 | temperature upper limit | 0.026885 |
| D3 | water lower limit | 0.028340 |
| D3 | water optimum | 0.000000 |
| D3 | water upper limit | 0.000000 |

## Next information barrier

The next stage may use only:

1. the frozen D1–D3 discovery candidate artifacts;
2. these frozen calibration radii;
3. the predeclared reserved validation seeds 401–423;
4. the already frozen full-fit and five-refit rules.

It must fit and freeze every validation member, process-exclusion transfer status and raw/calibrated response interval before opening validation truth. PR #1 remains blocked from `main`.
