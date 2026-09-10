# Functional compensation v13 — development contract

Status: **development only**. No fresh known-truth or empirical validation is authorized.

## Why v13

v11 and v12 tested the representation-sharing interpretation of the v9 `shared_candidate` state. Neither any single other process nor any non-empty coalition of the other declared process closures could transportably reconstruct the target process P on background environments: v12 found 0/13 shared-candidate cells with an eligible carrier coalition.

Therefore `shared_candidate` is no longer interpreted as evidence that other process closures carry P's environmental representation. The next hypothesis is **functional compensation / predictive substitutability**: when P is weakened, other processes may preserve ecological recovery through a different predictive route without reconstructing P itself.

## Estimand

For each v9/v8 `shared_candidate` target process P and every non-empty coalition S of the other declared processes, evaluate the **conditional marginal contribution of P given S is disabled**.

Within the same frozen inner spatial-CV fold and ModelSpec:

1. fit a model after hard-knocking out the union closure of S (`S-only knockout`);
2. fit a model after hard-knocking out the union closure of P ∪ S (`P+S knockout`);
3. compare their held-out, candidate-independent observation-corrected ecological recovery.

If P appears replaceable in the ordinary model but causes a material additional loss once S is disabled, S is a candidate **functional compensator** for P.

This is a predictive redundancy statement under the declared model/evidence contract. It is not physiological causality and does not imply that S reconstructs P.

## Frozen decision rule

All non-empty S subsets are enumerated before inspecting compensation outcomes.

A coalition S qualifies only when:

- the S-only route is complete and remains absolutely adequate under the already-frozen v5 absolute floor;
- P+S leaves at least one ecological predictor and yields finite held-out evidence;
- conditional rank loss = rank(S-only) - rank(P+S) exceeds **0.02 + 1 SEM**;
- conditional density loss = density(S-only) - density(P+S) exceeds **0.01 + 1 SEM**.

ModelSpecs are averaged within folds; ModelSpecs are not pseudo-replicates. Folds are the uncertainty units. Only inclusion-minimal qualifying S coalitions are retained.

No new numerical threshold is introduced: 0.02, 0.01, the absolute adequacy floor, and the 1-SEM rule are inherited from the existing frozen learner contracts.

## Governance

- development denominator: consumed seeds 15001–15010 only;
- target `shared_candidate` state is reconstructed exactly from frozen v5 total evidence and v8 unique evidence;
- all compensator coalitions are enumerated without truth or external biological labels;
- candidate-independent observation correction remains active;
- no post-outcome threshold relaxation;
- fresh known-truth validation is not authorized;
- empirical validation is not authorized.
