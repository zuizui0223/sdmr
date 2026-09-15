# v24 matched-context truth-surface diagnostic

Development diagnostic only. Retain v23's exact 152 pairs, 122 contexts,
consumed seeds 17001–17010 and six families. No new seeds or empirical data.

Reconstruct the same occurrence-coordinate-derived spatial partition as v23,
then assign all environment cells to its frozen centers. The target block is
always excluded from training; omit each other source block in turn, exactly
as in v23. Occurrence coordinates determine the existing partition only;
occurrence response labels/scores never enter oracle fitting.

The oracle uses the full true-suitability surface as its response and the same
ecological predictor closures. Fit full, drop-A, drop-B and drop-both routes
with the unchanged PR #200 HistGradientBoostingRegressor settings: 200 rounds,
31 leaves, 20 minimum samples per leaf, learning rate .08, L2 .001, seed 0,
no early stopping. Observation predictors are excluded from this ecological
truth-surface diagnostic.

Score held-out R2. Require all source omissions to be recorded and at least
three complete ones. Inherit the oracle's full R2 floor .80, paired loss margin
.02 and one-SEM descriptive bands. Full inadequacy yields unavailable.
Drop-both must show a supported loss before attributing either process.
Individual lower bounds > .02 support a loss; upper bounds <= .02 bound it
below the declared resolution; overlapping bands remain uncertain.

Persist truth-surface pair states before joining v23 occurrence states or
generating membership. Report the entire denominator and crosswalk. This is
a diagnostic contrast using a different target and model family, so a gap
cannot by itself be attributed to a single cause such as sample size, score,
observation correction or estimator choice. It is not a new inference method
or evidence permitting fresh validation. Preserve v23's failed screen.
