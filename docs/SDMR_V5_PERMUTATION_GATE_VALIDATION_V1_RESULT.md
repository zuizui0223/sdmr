# SDMR v5 permutation-gate validation v1 — terminal result

Status: **development validation PASS / independent confirmation authorized / future prospective seeds remain unopened**

## Frozen execution

- workflow run: `36070724122`
- workflow head: `89dd508e3367417fc077c2b71511e6567cf60813`
- terminal artifact: `sdmr-v5-permutation-gate-validation-v1`
- artifact id: `10838468711`
- artifact digest: `sha256:74190cc9022fd024a1be2a00748f6dd9053b76a61adc3f2163dc36a22c71d0d9`
- validation seeds: **51001–51100**
- confirmation seeds 52001–52050 opened: **false at validation terminal**
- reserved future prospective seeds 53001–53020 opened: **false**
- fresh empirical data opened: **false**
- Product-A: **closed_not_reopened**

## Frozen v5 rule

Full-system Stage-P authorization required all three:

```text
mean balanced log score >= -0.75
mean gain over -log(2) > 0
held-out within-fold label-permutation p <= 0.001
```

Permutation design:

- B = 999
- alpha = 0.001
- RNG seed = 0
- greater-tail Monte Carlo p-value
- no model refitting during permutations

## Validation result

| world | authorized |
|---|---:|
| unique_process | **100 / 100** |
| redundant_representation | **100 / 100** |
| shared_carrier | **100 / 100** |
| null_correlated | **100 / 100** |
| interaction | **100 / 100** |
| geographic_shift | **100 / 100** |
| observation_confounded | 98 / 100 — report-only |
| omitted_driver | **0 / 100** |

Validation PASS required:

- W7 omitted_driver = 0 / 100;
- each informative control W1/W2/W3/W4/W5/W8 >= 95 / 100;
- W6 report-only.

Strict conjunction passed.

## Interpretation

The held-out permutation gate removed the false-availability pattern that defeated the fold-SEM gate in prospective v3 and v4 confirmation, while preserving all six informative control worlds in the 100-seed validation panel.

This does not yet authorize a new prospective programme.

The next required step is the already-frozen independent confirmation panel:

```text
52001–52050
```

with the identical B=999, alpha=0.001 rule.

Confirmation PASS requires:

- W7 = 0 / 50;
- each informative control >= 48 / 50;
- W6 report-only;
- no rule change.

Reserved future prospective seeds `53001–53020` remain unopened until confirmation and full-pipeline integration both pass.
