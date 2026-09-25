# SDMR v6 magnitude-permutation validation v1 — terminal result

Status: **development validation PASS / independent confirmation authorized / integration and prospective panels remain unopened**

## Frozen execution

- workflow run: `36088891887`
- workflow head: `70cd2c8f36f52e33a98ad39bdef668c509124bd3`
- terminal artifact: `sdmr-v6-magnitude-permutation-validation-v1`
- artifact id: `10844948845`
- artifact digest: `sha256:f9dc1b593e77a33648d494a784aded984669830cc587da0f06825277ff25328e`
- validation seeds: **71001–71100**
- confirmation seeds 72001–72050 opened: **false**
- integration seeds 73001–73020 opened: **false**
- prospective seeds 74001–74020 opened: **false**
- fresh empirical data opened: **false**

## Frozen v6 authorization rule

```text
mean full balanced log score >= -0.75
AND mean gain over -log(2) >= 0.01
AND held-out permutation p <= 0.001
```

Unchanged:
- B = 999
- alpha = 0.001
- permutation seed = 0
- shallow3 HGB
- 8x sample regime
- random_cell Stage-P geometry

The 0.01 magnitude floor was frozen before this panel and equals the pre-existing SDMR process-information margin.

## Validation result

Frozen PASS:
- W7 omitted_driver: 0/100 authorized
- each W1/W2/W3/W4/W5/W8: >=95/100
- W6 report-only
- strict conjunction

Observed:

| world | authorized | minimum gain | median gain |
|---|---:|---:|---:|
| unique_process | **100/100** | 0.02920 | 0.03902 |
| redundant_representation | **100/100** | 0.02692 | 0.03839 |
| shared_carrier | **100/100** | 0.02061 | 0.03171 |
| null_correlated | **100/100** | 0.02701 | 0.03654 |
| interaction | **100/100** | 0.04027 | 0.05368 |
| geographic_shift | **100/100** | 0.02605 | 0.03422 |
| observation_confounded | 1/100 | 0.00055 | 0.00556 |
| omitted_driver | **0/100** | -0.00896 | -0.00412 |

Decision: **PASS**.

## Interpretation

The v6 magnitude floor cleanly separates the full-system information scale in this validation panel:

- every informative control exceeds the 0.01 gate and is authorized;
- W7 never reaches authorization;
- W6, whose focal ecology is confounded with observation effort, is almost entirely blocked and remains report-only.

This directly addresses the v5 integration failure, where a statistically extreme but tiny gain of 0.002016 authorized W7.

## Decision

Open exactly the pre-frozen independent confirmation panel:

```text
72001–72050
```

using the identical rule.

Confirmation PASS remains:
- W7 = 0/50;
- each informative control >=48/50;
- W6 report-only;
- no rule change.

Integration seeds 73001–73020 and prospective seeds 74001–74020 remain unopened.
