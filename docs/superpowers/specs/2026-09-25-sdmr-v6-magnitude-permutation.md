# SDMR v6 magnitude-calibrated permutation authorization

Date: 2026-09-25
Status: design frozen before v6 validation outcomes

## 1. Motivation

SDMR v5 solved the fold-SEM problem but the full-pipeline integration still failed INT-E.

Frozen failure:
- integration seeds 61001–61020;
- only seed 61014 / omitted_driver was falsely authorized;
- permutation p = 0.001;
- mean full-system gain over -log(2) = 0.002016;
- all six ODO-unavailable process states sharpened to replaceable.

The p-value gate alone therefore permits a statistically extreme but biologically tiny full-system signal to open process-specific inference.

## 2. Scope lock

v6 changes only the full-system authorization magnitude condition.

Unchanged:
- ODO v2;
- shallow3 HGB;
- 8x sample regime;
- Stage-P random_cell;
- Stage-T spatial;
- B=999;
- alpha=0.001;
- permutation seed=0;
- process-state margin=0.01;
- process-state definitions;
- structural refusals.

## 3. Authorization rule

Frozen v6 rule:

```text
mean full balanced log score >= -0.75
AND mean gain over -log(2) >= 0.01
AND permutation p <= 0.001
```

The new magnitude floor equals the already-frozen process-information margin.

Rationale:

> a process-specific question should not open unless the complete declared predictor system contains at least as much held-out information above the null as the minimum loss already defined as biologically meaningful for process attribution.

The value 0.01 is therefore inherited from the existing SDMR process-information contract, not tuned to seed 61014.

## 4. Development validation panel

Seeds:
- 71001–71100 (100 seeds)

Worlds:
- W1–W8

PASS:
- W7 omitted_driver: 0/100 authorized
- each W1/W2/W3/W4/W5/W8: >=95/100
- W6 report-only
- strict conjunction

## 5. Independent confirmation panel

Only after validation PASS:
- 72001–72050

PASS:
- W7: 0/50 authorized
- each W1/W2/W3/W4/W5/W8: >=48/50
- W6 report-only
- no rule change

## 6. Full-pipeline integration panel

Only after confirmation PASS:
- 73001–73020

Use complete Stage-P/Stage-T pipeline.

PASS:
- INT-A denominator/provenance
- INT-B positive recovery >=0.80
- INT-C false positive <=0.01
- INT-D zero unresolved/refusal violations
- INT-E zero unavailable sharp/favorable calls and W7 authorized=0
- INT-F spatial contradiction <=0.05 and zero spatial refusal violations

## 7. Reserved prospective denominator

- 74001–74020

Remains unopened throughout validation, confirmation, and integration.

No fresh empirical cohort may open before a future v6 prospective KT pass.
