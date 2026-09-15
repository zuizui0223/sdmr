# Nonlinear occurrence learner v25 — consumed development

Freeze before outcomes. Same 152 pairs, 122 contexts, consumed seeds, occurrence
and background samples, target/source omissions, observation correction,
observation marginalization, scores, four routes and classifier as v23.
Use the identical v23 development screen: specific precision >=95%, correct
specific attribution among all mixed pairs >=20%, false inclusion <=5%.

Change the learner only: replace the polynomial-logistic ModelSpec ensemble
with one deterministic HistGradientBoostingClassifier. Settings: log loss,
balanced classes, 200 rounds, 31 leaves, minimum leaf size 20, learning rate
.08, L2 .001, seed 0, no early stopping. These capacity settings follow the
v24 oracle model; the classifier trains only on observed occurrence/background
labels. This changes the model family and its internal ensemble, not just a
single complexity parameter. It does not train on privileged suitability.

Model predictions are passed through the unchanged observation marginalization
and ecological scoring. No oracle score, truth target or generating membership
enters candidate fitting or classification. Complete paired source omissions
remain the uncertainty units; a single nonlinear model is not replicated to
create additional pseudo-observations.

The v23 defaults remain unchanged for historical callers. New dependency
arguments permit this learner comparison without duplicating its evaluator.
Record the entire denominator and retain every abstention. v23 and v24 are
not rerun or reclassified. A failed screen cannot authorize fresh validation.
