# SDMR v6 full-pipeline integration v2 — terminal result

Status: **development integration PASS / prospective KT v2 activation authorized**

## Frozen execution

- workflow run: `36124407533`
- workflow head: `8d776d54ac7d712c8a832b8333b614cbbece0319`
- terminal artifact: `sdmr-v6-full-pipeline-integration-v2`
- artifact id: `10859533239`
- artifact digest: `sha256:de57d1ad14f431a0b9bce0862ae6621d9065a6d09a9522b9cecd070807fe26eb`
- integration seeds: **75001–75020**
- reserved prospective seeds 74001–74020 opened: **false**
- fresh empirical data opened: **false**
- Product-A: **closed_not_reopened**

## Frozen scientific architecture

- ODO v2 target unchanged
- Stage P = random_cell
- Stage T = spatial
- 8x = 1440 occurrence / 4800 background
- shallow3 HGB
- process margin = 0.01
- full-system authorization = v6 magnitude-permutation gate
  - B = 999
  - alpha = 0.001
  - permutation seed = 0
  - minimum gain over null = 0.01
- W1/W2/W3/W4/W5/W8 = informative controls
- W6 observation_confounded = report-only
- W7 omitted_driver = null control

The only design change relative to failed integration v1 was the predeclared INT-E authorization scope: W6 was returned to report-only status, matching the earlier validation and confirmation contracts.

## Strict integration result

All gates passed:

```text
INT-A = PASS
INT-B = PASS
INT-C = PASS
INT-D = PASS
INT-E = PASS
INT-F = PASS
```

Strict conjunction:

```text
INT-A & INT-B & INT-C & INT-D & INT-E & INT-F = TRUE
```

## Primary metrics

- Stage-P positive recovery: **0.8875**
- false-positive rate among ODO-replaceable: **0.0000**
- over-resolution among ODO-unresolved: **0.0000**
- structural-refusal violation: **0.0000**
- unavailable sharp-state rate: **0.0000**
- unavailable favorable-positive rate: **0.0000**
- W7 authorized count: **0**
- minimum informative-control authorization rate: **1.0000**
- W6 report-only authorization rate: **0.0500**
- Stage-P-positive → spatial-replaceable contradiction: **0.01408**
- spatial structural-refusal violation: **0.0000**
- Stage-T completeness: **1.0000**

The ODO process-state denominator was exactly preserved:

- positive: **80**
- replaceable: **700**
- unresolved: **60**
- unavailable: **120**
- structural refusal: **60**

## Decision

The complete v6 process-identification pipeline has now passed:

1. magnitude-permutation validation;
2. independent magnitude-permutation confirmation;
3. fresh full-pipeline integration under the correctly scoped W6 report-only rule.

Therefore the already-frozen prospective KT v2 contract may be activated **without changing**:

- seeds 74001–74020;
- model;
- sample size;
- ODO target;
- process margin;
- authorization thresholds;
- Stage-P/Stage-T roles;
- KT-A–KT-F thresholds.

Prospective seeds 74001–74020 remain unopened until the activation receipt is committed.
