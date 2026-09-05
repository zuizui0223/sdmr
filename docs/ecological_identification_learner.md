# Prospective ecological-identification learner

Status: **new prospective prototype; not part of frozen Product A**

## Why this is a learning algorithm rather than only a reporting layer

The learner does not optimize a single winning SDM. It learns a **set-valued ecological model** from model-pool data only:

1. freeze occurrence identities into model-pool versus sealed answer-check spatial blocks before ecological feature use;
2. evaluate a predeclared learner family on inner spatial folds using only model-pool rows;
3. retain every learner that passes an absolute predictive adequacy gate;
4. for each retained learner and each predeclared ecological process, remove the full process-information closure and refit in the same inner folds;
5. classify each process as `refuted_as_necessary`, `required_by_evidence_contract`, or `unresolved`;
6. refit all admitted baseline learners on the full model-pool and use their mean prediction as the predictive output;
7. only after a deterministic selection receipt exists may the outer answer-check occurrences be opened once for evaluation.

The learned object is therefore:

`admissible predictive model set + process certificate + ensemble prediction`

rather than one best model.

## Relationship to conventional learners

The current prototype uses the existing SDMR regularized logistic-response family (`ModelSpec`) as the base learner. The algorithmic novelty is the **set-valued falsification objective and information barrier**, not a new sigmoid or tree primitive. In future, the base learner interface can be generalized to GAM, MaxEnt, boosted trees or random forests while retaining the same outer contract.

## Occurrence answer-check philosophy

The outer split is frozen from occurrence IDs and coordinates only. Sealed occurrence IDs must not influence:

- environmental feature extraction decisions;
- accessible-area (`M`) construction;
- background sampling;
- model fitting;
- hyperparameter selection;
- predictor/process classification;
- process knockout definition;
- stopping rules.

If an answer-check ID is present in a learner fit table, fitting fails closed.

## Why this does not retrospectively strengthen Product A

This learner was designed after Product A closed. Using it to reinterpret v2.8.4 would be post-outcome method replacement and is forbidden. A publishable performance claim for this learner requires a new prospective contract, unused known-truth seeds and a fresh empirical cohort.

## Nature-level implication

A new algorithm alone is not sufficient for a Nature-family claim. A strong future test would need to show, prospectively, that the learner changes the ecological inferential object relative to conventional winner selection—for example by recovering true process status under known truth and then producing a nontrivial, independently checkable ecological contrast in fresh empirical data.
