# SDMR v3 occurrence-distribution oracle audit v1 — terminal diagnostic

Status: **development-only terminal result / measurement-boundary signal detected / numerical oracle not yet adequate / no prospective freeze**

## Frozen execution

- workflow run: `35488904447`
- workflow head: `af2da0e81942810c781ae59ef5ee35a4a9c9eeb7`
- artifact: `sdmr-v3-occurrence-distribution-oracle-audit-v1`
- artifact id: `10599016408`
- artifact digest: `sha256:c04dbf9199b1c5acaeceaafadbb90f7b6469163ba471731907036235bcd84824`
- config SHA-256: `2b8b32274b080cdc80b1e6d648b74d99d94e2d538f7bc5c3c79f61f195ebcd85`
- seeds: **23001–23008**, already-burned development evidence
- worlds: all W1–W8
- process cells: **384**
- Product-A: **closed_not_reopened**
- prospective seeds opened: **none**
- fresh empirical data opened: **false**

No biological margin, adequacy floor, or prospective threshold was tuned after opening this audit.

## Main three-level result

The audit confirms that the hierarchy

```text
truth-surface identifiability
        !=
occurrence-distribution identifiability
        !=
finite-sample learner recovery
```

is not merely conceptual.

There were **38 truth-surface-positive process cells**. Only **7/38 = 0.1842** were called positive by the occurrence-distribution oracle (ODO).

Among those 7 ODO-positive cells:

- linear finite learner recovered **1/7 = 0.1429**;
- quadratic finite learner recovered **0/7**.

Thus even after conditioning on the currently ODO-positive denominator, finite-sample recovery remains weak.

However, these numbers are not yet suitable for prospective denominator definition because ODO numerical availability itself is poor.

## Numerical-oracle availability problem

ODO returned `unavailable` for **221/384** process cells, with **222/384** cells failing the full-oracle numerical adequacy criterion before the observation-boundary override.

Because full-model numerical adequacy is shared by all six processes within a world × seed case, this corresponds to **37/64 world × seed cases** failing the oracle approximation check.

Availability by world:

- unique_process: 4/8 world-seeds numerically adequate;
- redundant_representation: 4/8;
- shared_carrier: 4/8;
- null_correlated: 4/8;
- interaction: **0/8**;
- observation_confounded: 7/8;
- omitted_driver: **0/8**, expected to be difficult because the hidden driver is absent;
- geographic_shift: 4/8.

The simple/noninteraction worlds show a strong seed-locked pattern: the same base-landscape seeds tend to fail together across unique_process, redundant_representation, null_correlated and geographic_shift.

For example, upper full-model Bayes-regret is below 0.01 for seed 23006 in all four families, while seeds such as 23002 and 23004 fail in all four. This synchrony is not explained by process-state semantics.

## Root-cause diagnosis

The v1 ODO estimates the Bayes posterior with a `HistGradientBoostingRegressor` and evaluates numerical adequacy under **spatial GroupKFold**.

That introduces an extra requirement:

> the numerical oracle must extrapolate the posterior into held-out spatial blocks.

But occurrence-distribution identifiability is a population/representation question:

> does the retained predictor sigma-field contain information about the exact observation distribution?

Spatial transferability is a different estimand. A tree learner is particularly poor at extrapolation beyond the training support, so spatial folds can create Bayes regret even when the full declared predictors contain the required process information.

The seed-locked regret pattern across otherwise different worlds is consistent with this numerical-oracle / spatial-transfer confounding.

Therefore the large ODO-unavailable count must not be interpreted as evidence that occurrence distributions are intrinsically uninformative.

## Truth-positive cells under v1 ODO

The 38 truth-positive cells decompose as:

- unique_process thermal: 8; ODO contributory 4, unavailable 4;
- interaction thermal/water: 14; ODO unavailable 14;
- observation_confounded thermal: 8; ODO unresolved 8 by the explicit observation nonseparability boundary;
- geographic_shift thermal: 8; ODO contributory 3, unresolved 1, unavailable 4.

The observation-confounded contraction is an intended inferential boundary. The interaction and many seed-specific unavailable calls are primarily numerical-oracle failures and cannot yet define the scientific occurrence-level target.

## Safety diagnostics

Among ODO-replaceable cells, neither finite learner produced a positive false call in this audit.

Finite over-resolution among ODO-unresolved cells was also 0 for both learners.

Those safety results are useful but secondary until ODO availability is repaired.

## Decision

**Occurrence-distribution oracle v1 is not ready to define the prospective learner-recovery denominator.**

The next admissible development step is not margin tuning and not another finite learner substitution. It is a numerical-oracle correction:

1. preserve the exact complete observation distributions and Bayes target;
2. preserve the 0.01 process-information margin and 0.01-nat Bayes-regret tolerance;
3. remove spatial-transfer extrapolation from the numerical conditional-expectation approximation;
4. use deterministic random cross-fitting over the complete cell distribution for oracle approximation;
5. rerun only already-burned development seeds;
6. compare numerical availability and state contraction against this terminal v1 result.

Spatial transfer remains scientifically important, but it belongs in the later held-out transfer gate, not inside the population identifiability oracle itself.

No current v1 ODO output may be promoted to prospective evidence.
