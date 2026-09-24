# SDMR v5 permutation-calibrated full-system information gate

Date: 2026-09-25
Status: design frozen before v5 validation outcomes

## 1. Motivation

SDMR v4 independently rejected the fold-SEM authorization rule.

Frozen confirmation result:

- selected multiplier: 1.0
- informative controls W1/W2/W3/W4/W5/W8: 50/50 authorized each
- W7 omitted_driver: 2/50 falsely authorized
- W6: report-only
- confirmation: FAIL

The failure is upstream of process-specific states. The process-state margin, ODO v2, shallow3 learner profile, Stage-P random_cell geometry, Stage-T separation, observation-confounding refusal, and identical-closure refusal remain unchanged.

SDMR v5 replaces only the finite-data authorization test for the complete predictor system.

## 2. Statistical object

For Stage-P random_cell cross-fitting:

1. fit the complete predictor system on each training fold;
2. obtain predictions for the held-out fold;
3. never refit those predictions during the information test.

For held-out fold k:

```text
S_k = balanced Bernoulli log score
G_k = S_k - (-log 2)
```

The observed statistic is:

```text
T_obs = mean_k S_k
```

and the mean information gain is:

```text
G_obs = mean_k G_k
```

## 3. Conditional held-out label permutation

Under the full-system no-information null, held-out occurrence/background labels are exchangeable with respect to predictions produced without using those held-out labels.

For each permutation b:

- independently permute held-out labels **within each fold**;
- preserve each fold's class counts exactly;
- keep predictions fixed;
- recompute the balanced log score for each fold;
- average the fold scores:

```text
T_b = mean_k S_{k,b}^{perm}
```

No model is refit during permutations.

## 4. Frozen permutation design

Exactly:

```text
B = 999 permutations
alpha = 0.001
permutation RNG seed = 0
alternative = greater
```

Monte-Carlo permutation p-value:

```text
p = (1 + # {T_b >= T_obs}) / (B + 1)
```

The smallest attainable p-value is therefore 0.001.

No alternative B, alpha, seed, or tail may be introduced after validation outcomes are opened.

## 5. Full-system authorization rule

The full system is information-adequate only if **all three** conditions hold:

```text
mean full balanced log score >= -0.75
mean full gain over -log(2) > 0
permutation p <= 0.001
```

If the conjunction fails:

```text
all Stage-P process states = unavailable
reason = full_system_not_informative
```

This gate applies to Stage P only.

Stage T remains a separate spatial-transfer endpoint and does not redefine Stage-P information availability.

## 6. Why this replaces fold-SEM

The previous gate treated three fold scores as if their SEM supplied a calibrated sampling distribution.

Sequential independent evidence showed:

- prospective v3 W7: 1/20 false authorizations;
- v4 calibration W7: 0/100;
- v4 confirmation W7: 2/50.

The held-out permutation gate instead conditions on the fitted predictions and tests whether held-out labels align with them more strongly than expected under exchangeability.

It therefore avoids interpreting three overlapping-CV fold means as an approximately Gaussian sample.

## 7. Development validation denominator

Seeds:

```text
51001–51100
```

100 seeds.

Worlds: W1–W8.

Frozen finite architecture:

- 8x = 1440 occurrence / 4800 background;
- one deterministic resample per ecological seed;
- shallow3 HGB;
- random_cell;
- 3 folds;
- same world/process registry and observation architecture as SDMR v3/v4;
- only full-system model fitted during validation.

### Validation PASS

Strict conjunction:

#### W7 null control

```text
omitted_driver authorized = 0 / 100
```

#### Informative controls

For each W1/W2/W3/W4/W5/W8:

```text
authorized >= 95 / 100
```

#### W6

observation_confounded is report-only.

No process knockouts are opened during this validation.

## 8. Independent confirmation denominator

Only if validation passes, open:

```text
52001–52050
```

50 seeds.

Same frozen gate. No parameter change.

Confirmation PASS:

- W7: 0/50 authorized;
- each W1/W2/W3/W4/W5/W8: >=48/50;
- W6 report-only;
- strict conjunction.

If confirmation fails:
- no alpha/B/permutation change on that panel;
- no seed replacement;
- v5 gate confirmation is terminally failed.

## 9. Reserved future prospective denominator

Reserved, unopened during validation/confirmation:

```text
53001–53020
```

These seeds are not activated until:
1. permutation-gate validation passes;
2. independent confirmation passes;
3. the complete Stage-P/Stage-T pipeline is re-integrated and development safety checks pass.

## 10. Scope lock

v5 does not change:

- ODO v2;
- process-state definitions;
- process margin 0.01;
- shallow3 model hyperparameters;
- Stage-P random_cell;
- Stage-T spatial transfer;
- 8x sample regime;
- W1–W8;
- structural refusals.

Only full-system information authorization changes.

Fresh empirical validation remains closed.
