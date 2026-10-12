# v5: objective-preserving convergence comparison (first10, post-terminal)

## Result

Numerical convergence alone did **not** solve the real-v5 calibration problem in the first ten frozen taxa. Holding the original raw-feature L2 objective fixed, the converged solution reduced the training objective in **30/30 folds**, but spatial held-out balanced log score improved in only **3/10 taxa**, worsening in **7/10**. Paired mean score change was **-0.13794939**, median **-0.14272697**. All 30 final numerical certificates passed.

| Same-runtime route | Mean spatial balanced log score | Full-system authorized taxa |
|---|---:|---:|
| Original raw-feature L-BFGS recipe, max_iter=1000 | -1.64363720 | 0/10 |
| Same raw-feature L2 objective, converged Newton | -1.78158659 | 1/10 |
| Train-fold standardized features with isotropic L2 | -1.16344347 | 1/10 |

Higher log score is better. The last route changes the regularization geometry; it is not an optimizer-only intervention. It outscored the converged original-objective route in 10/10 taxa, but still authorized only one taxon. No predictor selection, hyperparameter search, taxon replacement, or sealed answer-check was used.

## Objective equivalence

For training-fold mean mu and scale s, let z=(x-mu)/s and theta=s*beta. The unchanged original objective is:

    sum_i(weight_i*logloss_i)/sum(weight)
    + sum_j(theta_j^2/s_j^2)/(2*C*sum(weight)), C=1.

The intercept is not penalized. The scale is learned on each training fold only. The inverse-scale-squared diagonal preserves the raw-feature penalty exactly; ordinary standardized C=1 L2 does not.

Unit tests cover objective identity, central-difference gradient/Hessian checks, comparison with an independent raw Newton-Cholesky solution on a well-conditioned fixture, zero-iteration failure, constants/intercept handling, prediction-only data isolation, and two initializations. **9 tests pass**. On the real first10, the maximum original/transformed objective difference is **5.06e-15**. Two initializations agree within **7.67e-9** in held-out probability. An independent SciPy trust-exact optimization agrees within **1.67e-6**, below the fixed 2e-6 comparison tolerance. The converged Newton solver takes **5-24 iterations**, while the raw L-BFGS recipe hits the 1000-iteration limit in **30/30 folds**.

## Transparent numerical development history

The initial independent raw Newton-Cholesky reference reported an ill-conditioned Hessian and fell back to un-converged L-BFGS in some folds. Those warnings were retained, not treated as a valid reference. A separate trust-exact solver of the identical transformed objective was added. An initial first10 run then passed 29/30 precision comparisons: one weak-curvature fold stopped too early to agree at the fixed probability tolerance. For **all** folds, Newton gradient tolerance was tightened from 1e-9 to 1e-12 and decrement from 1e-6 to 1e-9. No data, penalty, scientific gate, or probability-agreement tolerance was relaxed. The final 30/30 result is numerical method development, not an independent prospective study. Preliminary results and computational amendments are retained in the chat evidence package.

## Provenance and limits

Inputs were exported by workflow **38134483278**, artifact **11700850978**, ZIP SHA-256 **9a2574ab03506123b1119ed92b5432f5929a293b4d790bed38ac5290ac281237**. Feature values, labels, spatial groups, and each training/validation matrix exactly match the prior original-input-path audit **38127240195**. Only first10 model-pool matrices were exported. The new comparison ran locally with Python 3.13.5, NumPy 2.3.5, pandas 2.2.3, SciPy 1.17.0, and scikit-learn 1.8.0; these differ from historical CI versions. All three arms share this runtime. The table is **not** a claim to reproduce or improve archived original-v5 scores.

Full fold-level output SHA-256: **f1b7462b02cc3355f7ab9e61afa209e49fd1a940f42f5a2ed7c2b6b95edeea24**. The retained user-facing evidence ZIP contains the exact inputs, tested source, full output, preliminary outputs, amendment history, and verification script. It is a chat attachment, not a permanent public archive.

**Conclusion boundary:** the optimization defect is real and fixable, but fixing it is not sufficient for reliable spatial prediction in this fixed first10 panel. Poor transfer after numerical repair does not prove biological nonidentifiability. Stable process-closure attribution was not recomputed here. Original fresh-v5 remains `failed_closed`; M5 known-truth claims and all original scientific thresholds are unchanged. Next, examine closure-level evidence with reliable learners under matched identification conditions rather than equating optimizer convergence with ecological correctness.
