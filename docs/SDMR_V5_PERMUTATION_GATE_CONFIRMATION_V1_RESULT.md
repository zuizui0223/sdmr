# SDMR v5 permutation-gate confirmation v1 — terminal result

Status: **development confirmation PASS / full-system permutation gate independently confirmed / integration authorized**

## Frozen execution

- workflow run: `36081546640`
- workflow head: `26b2e576c9fe46fba54d8c7fb5bce515ef325009`
- terminal artifact: `sdmr-v5-permutation-gate-confirmation-v1`
- artifact id: `10841589899`
- artifact digest: `sha256:f4f9aab2bf0358d25c66767a687519ad6581f9554df671c8554df1a974a7aa6a`
- validation source: workflow `36070724122`, artifact digest `sha256:74190cc9022fd024a1be2a00748f6dd9053b76a61adc3f2163dc36a22c71d0d9`
- confirmation seeds: **52001–52050**
- reserved prospective seeds 53001–53020 opened: **false**
- fresh empirical data opened: **false**
- Product-A: **closed_not_reopened**

## Frozen rule

The full system is authorized only if:

```text
mean balanced log score >= -0.75
mean gain over -log(2) > 0
held-out within-fold permutation p <= 0.001
```

Permutation design:
- B = 999
- alpha = 0.001
- permutation RNG seed = 0
- labels permuted within held-out folds
- fold class counts preserved
- models never refit during permutations

No rule changed after validation.

## Independent confirmation result

| world | authorized |
|---|---:|
| unique_process | **50 / 50** |
| redundant_representation | **50 / 50** |
| shared_carrier | **50 / 50** |
| null_correlated | **50 / 50** |
| interaction | **50 / 50** |
| geographic_shift | **50 / 50** |
| observation_confounded | 48 / 50 — report-only |
| omitted_driver | **0 / 50** |

Frozen PASS conditions:
- W7 = 0 / 50;
- each informative control >= 48 / 50;
- W6 report-only;
- strict conjunction.

All passed.

## Sequential evidence

The gate now has two outcome-separated positive validations:

### Validation 51001–51100
- W7: **0 / 100**
- every informative control: **100 / 100**
- W6: 98 / 100 report-only

### Confirmation 52001–52050
- W7: **0 / 50**
- every informative control: **50 / 50**
- W6: 48 / 50 report-only

Combined development evidence is descriptive only and is not a new pooled confirmation denominator.

## Decision

The v5 permutation authorization layer is retained unchanged for full-pipeline integration.

The next admissible panel is the already pre-frozen development integration denominator:

```text
61001–61020
```

It must test the complete Stage-P process-state pipeline and Stage-T spatial transfer under strict INT-A–INT-F conjunction.

Reserved prospective seeds `53001–53020` remain unopened until the complete integration gate passes.
