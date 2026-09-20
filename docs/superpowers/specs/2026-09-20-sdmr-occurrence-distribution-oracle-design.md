# SDMR v3 occurrence-distribution identifiability oracle — design

Date: 2026-09-20
Status: development design; prospective validation remains unopened

## 1. Motivation

The positive-evidence audit showed that truth-surface-positive process cells often have no established positive held-out occurrence score gap.

This creates a missing level in the current hierarchy:

```text
generating process
    !=
truth-surface representation identifiability
    !=
occurrence-distribution identifiability
    !=
finite-sample learner recovery
    !=
unique attribution
```

The current benchmark compares the finite occurrence learner directly with the truth-surface oracle. That comparison can count a process as a learner false negative even when the occurrence-vs-background distribution contains too little process-specific information to support the same sharp state.

## 2. Oracle estimand

For one complete simulated world, define exact cell probabilities

[
q_1(i) \propto s_i e_i
]

for focal occurrence records and

[
q_0(i) \propto e_i
]

for target-group/background records, where (s_i) is true ecological suitability and (e_i) is the simulated observation effort.

Under equal class priors, the exact full-information posterior is

[
p_i = \frac{q_1(i)}{q_1(i)+q_0(i)}.
]

The mixture measure is

[
m_i = \tfrac12\{q_1(i)+q_0(i)\}.
]

For a reduced process-free predictor system (Z=X_{-P}), the Bayes-optimal reduced posterior is

[
p_P(z)=E_m[p_i\mid Z=z].
]

Thus process identifiability from the observation distribution is the proper-score information loss between the full posterior and the best reduced posterior measurable from the retained predictor system.

## 3. Numerical oracle

The conditional expectation is estimated with a flexible deterministic `HistGradientBoostingRegressor`:

- response: exact full posterior (p_i);
- training weights: mixture mass (m_i);
- predictors: either all declared predictors or the complete process-free closure;
- spatial GroupKFold: same declared spatial grouping concept as the existing truth-surface oracle;
- predictions clipped to `[1e-6, 1-1e-6]`.

For each held-out spatial fold compute equal-prior expected log score:

[
S = \tfrac12 E_{q_1}[\log \hat p] +
    \tfrac12 E_{q_0}[\log(1-\hat p)].
]

The process loss is

[
\Delta_P = S_{full}-S_{-P}.
]

Positive values mean process removal loses occurrence-distribution information.

## 4. Oracle approximation check

The exact Bayes score on each held-out fold is calculated directly from (p_i).

Full-model regret is

[
R = S_{Bayes}-S_{full}.
]

The occurrence oracle is unavailable for a process cell if the full flexible representation cannot approximate the exact Bayes score within a predeclared approximation tolerance.

Development-v1 tolerance is fixed at **0.01 nats**, before running this oracle on the burned outcome panel. It is an oracle numerical-adequacy criterion, not a biological effect threshold.

## 5. State classification

When the full oracle is numerically adequate:

- `replaceable`: upper uncertainty bound of (Delta_P) is at or below the unchanged biological margin 0.01 nats;
- `contributory`: lower uncertainty bound is above 0.01 and the process-free score remains above the unchanged -0.75 absolute floor;
- `required`: lower uncertainty bound is above 0.01 and the process-free score is below -0.75;
- `unresolved`: interval overlaps the 0.01 margin;
- `unavailable`: full-oracle approximation regret exceeds tolerance or evidence is incomplete.

Identical process closures still force `unresolved` for sharp process-specific states.

## 6. Development comparison

Using only burned seeds 23001–23008, compute for all W1–W8:

1. truth-surface oracle state;
2. occurrence-distribution oracle state;
3. finite linear occurrence state;
4. finite quadratic occurrence state.

Primary diagnostic quantities:

- truth-positive cells that contract to occurrence-oracle replaceable/unresolved;
- finite-learner positive recovery among **occurrence-oracle-positive** cells;
- finite false-positive rate among occurrence-oracle-replaceable cells;
- abstention calibration among occurrence-oracle-unresolved cells;
- full-oracle numerical availability.

No prospective threshold or seed is opened by this diagnostic.

## 7. Scientific consequence

If the occurrence oracle contracts a substantial fraction of truth-surface-positive cells, those cells are not finite-learner failures. They demonstrate a measurement boundary: the ecological process exists in the full suitability surface but is not sharply identifiable from the declared occurrence observation system.

The prospective SDMR target should then be the occurrence-distribution oracle for occurrence-only inference, while the truth-surface oracle remains a separate ecological-information target.

If occurrence-oracle-positive cells remain numerous and finite recovery is still poor, the learner/evidence procedure remains the limiting component.

## 8. Non-retroactivity

- Product-A remains closed.
- Development v1–v3 and the positive-evidence audit remain terminal records.
- The 0.01 biological margin and -0.75 occurrence adequacy floor are not tuned against prior outcomes.
- Prospective seeds and fresh empirical data remain unopened.
