# SDMR v4 full-system information-gate calibration

Date: 2026-09-24
Status: development design frozen before v4 calibration outcomes

## 1. Motivation

Prospective SDMR v3 failed only KT-E.

The failure was one finite-sample false authorization:

```text
seed 33009 / omitted_driver
full-system lower gain over null = +0.000794
→ full system declared informative
→ six ODO-unavailable processes sharpened to replaceable
```

All other prospective gates passed.

This failure must not be repaired by rescoring v3. Seeds 33001–33020 are permanently burned.

SDMR v4 changes only the **authorization to ask a process-specific question**. It does not change:
- ODO v2;
- process-state definitions;
- process margin 0.01;
- shallow3 learner profile;
- Stage-P random_cell geometry;
- Stage-T spatial separation;
- observation-confounding refusal;
- identical-closure refusal.

## 2. New development denominators

### Calibration panel

Seeds: **41001–41100** (100 seeds)

Purpose: select one uncertainty multiplier for the full-system information gate.

### Independent confirmation panel

Seeds: **42001–42050** (50 seeds)

Purpose: test the selected multiplier once without reselection.

### Reserved future prospective band

Seeds: **43001–43020**

These remain unopened during v4 development.

Repository search before this freeze found no prior use of these three seed bands.

## 3. Frozen finite architecture

For every world × seed:

- exact W1–W8 world generator unchanged;
- finite sample size: 8x = 1440 occurrence / 4800 background;
- one deterministic development resample per ecological seed;
- learner: shallow3 HGB;
- split: random_cell;
- n_splits: 3;
- adequacy floor: -0.75;
- equal-prior null score: -log(2).

Only the **full model** is fit in this calibration. No process knockout or process state is opened during gate selection.

## 4. Gate statistic

For fold k:

```text
gain_k = full_balanced_log_score_k - (-log 2)
```

For each world × seed:

```text
mean_gain = mean(gain_k)
SEM_gain  = SEM(gain_k)
lower_gain(c) = mean_gain - c * SEM_gain
```

Candidate gate:

```text
full_system_information_adequate(c) =
    mean_full_score >= -0.75
    AND
    lower_gain(c) > 0
```

## 5. Predeclared candidate multipliers

Exactly this ordered grid:

```text
1.000
1.645
1.960
2.326
2.576
3.090
```

Interpretation follows conventional one-sided normal critical values, but candidate selection is empirical development calibration rather than a claim that the three fold estimates are exactly independent Gaussian observations.

No value outside this grid may be introduced after outcomes are opened.

## 6. Calibration targets

### Null world

W7 `omitted_driver` is the primary false-authorization world.

For candidate c:

```text
W7 false authorization rate <= 0.01
```

Across 100 seeds, this means at most 1 authorized W7 seed.

### Informative control worlds

Selection controls:

- W1 unique_process
- W2 redundant_representation
- W3 shared_carrier
- W4 null_correlated
- W5 interaction
- W8 geographic_shift

For every one of these six worlds:

```text
authorization rate >= 0.95
```

W6 `observation_confounded` is **report-only** for gate selection because its focal thermal process is structurally nonseparable by design. Its authorization rate is recorded but cannot force a weaker Type-I gate.

This does not turn W6 into a positive process claim. The existing observation-process refusal remains authoritative.

## 7. Candidate selection rule

Select the **smallest multiplier in the frozen grid** that simultaneously satisfies:

1. W7 false authorization <= 0.01; and
2. each of W1/W2/W3/W4/W5/W8 authorization >= 0.95.

Smallest-c selection maximizes finite information retention subject to null control.

If no candidate qualifies:
- calibration fails;
- no confirmation panel is opened;
- no prospective v4 contract is permitted.

## 8. Independent confirmation rule

Only the selected multiplier is evaluated on seeds 42001–42050.

Pass requires:

### W7

```text
0 / 50 false authorizations
```

because 1/50 = 0.02 exceeds the calibration target 0.01.

### Informative controls

For each W1/W2/W3/W4/W5/W8:

```text
>= 48 / 50 authorized
```

which is the smallest integer count meeting an authorization rate >=0.95.

### W6

Report-only; no pass/fail role.

Strict conjunction across W7 and all six informative controls.

If confirmation fails:
- selected multiplier is not retuned;
- confirmation seeds are not replaced;
- v4 gate development is terminally failed.

## 9. Development-only interpretation

Calibration and confirmation authorize only the full-system information gate.

They do **not** establish:
- process recovery;
- false-positive process-state control;
- spatial transfer;
- empirical superiority.

After confirmation passes, the full v4 Stage-P/Stage-T method must undergo a new development integration check before any future prospective contract is activated.

## 10. Prospective barrier

Seeds 43001–43020 remain unopened throughout calibration and confirmation.

No fresh empirical plant cohort may be opened until a future prospective KT version passes its own frozen conjunction.
