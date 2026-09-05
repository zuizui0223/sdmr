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

## Formal learning object

Let `M` be the predeclared family of fitted model procedures, `g(m)` the inner-CV predictive adequacy statistic and `tau` the frozen adequacy threshold. The learner first estimates the admissible set

`A(D_model) = {m in M : g(m; D_model) >= tau}`.

It does **not** choose `argmax g(m)` from that set.

For an ecological process `p`, let `C(p)` be the prospectively declared information closure (all direct, derived, proxy and composite predictors carrying information about `p`). For each admitted learner `m`, refit the same procedure after removing `C(p)` and evaluate

`g(m[-C(p)]; D_model)`

on the same frozen inner spatial evidence structure.

Define the adequate knockout witness set

`W_p = {m in A : knockout route for m and p is complete and g(m[-C(p)]) >= tau}`.

Then the process estimator is set-valued:

- `refuted_as_necessary` if `W_p` is non-empty;
- `required_by_evidence_contract` if every admitted knockout route is complete and `W_p` is empty;
- `unresolved` otherwise.

The prediction estimator is an ensemble over `A`, currently the mean relative-suitability prediction across admitted learners.

This is a **constraint-based set-valued learner** rather than a scalar winner-selection criterion. In particular, it does not reward a smaller process set or narrower uncertainty. That is deliberate: Product-A known-truth work showed that post-adequacy sharpening can create false necessity by removing viable alternatives.

## Relationship to conventional learners

The current prototype uses the existing SDMR regularized logistic-response family (`ModelSpec`) as the base learner. The algorithmic novelty is the **set-valued falsification learning objective and information barrier**, not a new sigmoid or tree primitive. In future, the base learner interface can be generalized to GAM, MaxEnt, boosted trees or random forests while retaining the same outer contract.

A new base estimator is not required for this to be a new learning algorithm: meta-learning, conformal prediction and ensemble methods likewise define new learned objects and decision rules on top of familiar fitting primitives. What must be validated prospectively is whether the new learned object improves ecological identification without unacceptable predictive loss.

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

The answer-check is an **outer answer key**, not another CV fold. Inner CV inside `D_model` is used for learning/adequacy decisions; the outer answer-check is opened once only after `A`, all process states and a deterministic selection receipt have been frozen.

## Why this does not retrospectively strengthen Product A

This learner was designed after Product A closed. Using it to reinterpret v2.8.4 would be post-outcome method replacement and is forbidden. A publishable performance claim for this learner requires a new prospective contract, unused known-truth seeds and a fresh empirical cohort.

## Nature-level implication

A new algorithm alone is not sufficient for a Nature-family claim. A strong future test would need to show, prospectively, that the learner changes the ecological inferential object relative to conventional winner selection—for example by recovering true process status under known truth and then producing a nontrivial, independently checkable ecological contrast in fresh empirical data.
