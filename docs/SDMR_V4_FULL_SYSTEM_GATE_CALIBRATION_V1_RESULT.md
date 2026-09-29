# SDMR v4 full-system gate calibration v1 — terminal result

Status: **development calibration PASS / selected multiplier = 1.0 / independent confirmation still unopened**

## Frozen execution

- workflow run: `36014081688`
- workflow head: `ec2afba5702c877df30a145fcac779b77445ee7a`
- terminal artifact: `sdmr-v4-full-system-gate-calibration-v1`
- artifact id: `10814773861`
- artifact digest: `sha256:77024e0489f55fa2e4a229c667372503f95a71a9b20f66a42956b4c23846fbf6`
- config SHA-256: `5ef81e07298da147cce27b0216053de0e1afe6e057058db234aef91fba167e6f`
- calibration seeds: **41001–41100**
- confirmation seeds 42001–42050 opened: **false**
- reserved future prospective seeds 43001–43020 opened: **false**

## Frozen candidate grid

```text
1.000
1.645
1.960
2.326
2.576
3.090
```

Selection rule was frozen before outcomes:

1. W7 omitted_driver false authorization <= 0.01;
2. each of W1/W2/W3/W4/W5/W8 authorization >= 0.95;
3. choose the smallest qualifying multiplier;
4. W6 observation_confounded is report-only.

## Result

All six candidate multipliers qualified.

| multiplier | W7 false authorization | minimum informative-control authorization | W6 report-only authorization | eligible |
|---:|---:|---:|---:|---|
| 1.000 | **0.00** | **1.00** | 0.90 | yes |
| 1.645 | 0.00 | 1.00 | 0.82 | yes |
| 1.960 | 0.00 | 1.00 | 0.74 | yes |
| 2.326 | 0.00 | 1.00 | 0.68 | yes |
| 2.576 | 0.00 | 1.00 | 0.63 | yes |
| 3.090 | 0.00 | 1.00 | 0.49 | yes |

Therefore the frozen smallest-c rule selects:

```text
selected multiplier = 1.0
```

## World-level calibration at c = 1.0

- unique_process: **100 / 100 authorized**
- redundant_representation: **100 / 100**
- shared_carrier: **100 / 100**
- null_correlated: **100 / 100**
- interaction: **100 / 100**
- geographic_shift: **100 / 100**
- omitted_driver: **0 / 100**
- observation_confounded: **90 / 100** — report-only

## Interpretation

The prospective v3 KT-E failure at seed 33009 did not recur in the 100-seed v4 calibration panel.

The v4 calibration therefore does **not** justify increasing the uncertainty multiplier. Under the predeclared loss-minimizing selection rule, the existing 1×SEM gate remains the selected candidate because it controlled W7 perfectly while retaining all six informative control worlds perfectly in this development panel.

This does not rescind the prospective v3 failure. The 33001–33020 denominator remains burned and v3 remains terminally failed.

Instead, the result means:

> the 1×SEM full-system gate must now be independently confirmed on a fresh 50-seed panel before it may be reused in a new prospective programme.

## Next step

Open exactly the frozen confirmation seeds:

```text
42001–42050
```

using only multiplier `1.0`.

Confirmation PASS requires:

- W7 omitted_driver: **0 / 50 authorized**
- every informative control W1/W2/W3/W4/W5/W8: **>= 48 / 50 authorized**
- W6: report-only
- strict conjunction
- no reselection

If confirmation fails, multiplier 1.0 is not retuned on the same confirmation panel.

Reserved future prospective seeds `43001–43020` remain unopened.
