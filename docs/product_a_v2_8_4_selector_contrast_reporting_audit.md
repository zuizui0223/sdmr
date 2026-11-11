# Product-A v2.8.4 selector-contrast reporting audit

Status: **reporting-only audit of the frozen full-denominator empirical endpoint / no endpoint reinterpretation**.

The authoritative scientific decision remains `empirical_confirmation_not_supported` followed by the separate `not_promoted` decision. This audit asks a narrower reporting question: did the ecological and AUC selection roles actually instantiate different fitted candidates under the fresh empirical endpoint?

## Frozen sources

- workflow run: `33364164527`, attempt 1
- frozen SHA: `1496a6c63b19bf7711511a864ccb448fc123c963`
- terminal artifact: `9750071472`, digest `sha256:a4243eedae221e5ffd289062e27ec949b39f35a4f7a00849a56b047a3ccb8c9f`
- finalized seed-part artifacts:
  - seed `2026082201`: artifact `9750048481`, digest `sha256:56938514d0be4080652514d3900cee2caffea8bd223a3a3bb6cc703abb4e84eb`
  - seed `2026082202`: artifact `9749405054`, digest `sha256:fc5fc6bc9fafc0049d4013e6b9cc1a46c8de61b77a51f3e06d31bbbbcc8672a2`
  - seed `2026082203`: artifact `9749815263`, digest `sha256:2ee21a65f2f7415b785b5b2768c8e5fd61ada01400e45c7898fcd8dab78225af`

Each finalized part contains 12 taxa × 3 M specifications × 2 roles = 72 audited model rows. The reporting audit compares the ecological and AUC rows within every matched taxon × M cell.

## Exact selector contrast

Across the full endpoint there are `3 × 12 × 3 = 108` matched taxon × M × seed cells.

- exact candidate ID equality between ecological and AUC roles: **108/108**;
- exact selected-predictor-string equality between ecological and AUC roles: **108/108**;
- candidate strategy used in all 108 ecological cells: `all`;
- exact candidate ID in all 108 ecological cells: `all|logit_l2_C0.1_degree1_rs0`;
- number of distinct ecological candidate IDs across all 108 cells: **1**.

Thus the fresh empirical ecological and AUC selection roles did not merely tie after evaluation. Under the frozen evidence, they instantiated the same candidate in every matched cell.

## Sealed metric identity

Within each of the 108 matched cells, the ecological and AUC roles are also identical for all audited sealed metrics checked here:

- presence rank;
- continuous Boyce;
- OR10;
- Schoener-D environmental overlap;
- centroid distance;
- breadth error;
- quantile-profile error.

The existing terminal summaries therefore correctly report mean presence-rank delta `0.0`, ecological nondomination `3/3`, and strict ecological improvement `0/3`.

## Interpretation

This audit does **not** change the formal endpoint from `empirical_confirmation_not_supported` to `not_tested`. The preregistered empirical superiority criterion was evaluated and failed under a complete denominator.

It does add a mechanistic explanation for the non-support result:

> the realized empirical selector contrast collapsed to zero because the ecological and AUC rules selected the same fitted candidate in every taxon × M × seed cell.

Accordingly, two statements must remain distinct:

1. **formal empirical superiority claim:** tested and not supported;
2. **empirical test of process-identification performance when ecological and predictive selectors genuinely disagree:** not identified by this endpoint because no realized selector disagreement occurred.

This is an observational-equivalence result, not evidence that AUC is the ecological truth criterion.

## Nature-track use

This audit strengthens the general manuscript argument. In controlled truth, prediction adequacy and process identification can diverge; in fresh empirical occurrence data, the two selection objectives can instead become observationally indistinguishable and collapse to the same model. Together these results show why a winner comparison alone cannot determine whether ecological necessity has been identified.

The preferred figure reports `108/108` candidate identity and the all-cell candidate ID alongside the formal v2.8.4 endpoint. Do not imply that the empirical process truth was observed.
