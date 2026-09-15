# Coalition attribution v23: consumed development

Frozen before evaluating v23 outcomes. Uses the same hash-pinned 152 unordered
pairs / 122 contexts from v22, seeds 17001–17010, across all six families.
No generating truth enters selection, fitting, or classification.

## Four paired routes

Fit full, drop-A, drop-B, and drop-both routes on identical training rows and
score on the same held-out target block. Omit each other source block from
training in turn. Inherit the v22 simulation, splits, observation corrections,
ModelSpecs, ecological process closures and scores.

Average frozen ModelSpecs within each complete source omission. Require at
least three complete source omissions. Use the inherited one-SEM descriptive
bands on paired losses; correlated training sets mean these are not formal
independent-replicate confidence intervals.

The full route must pass the unchanged prediction and ecological rank gate:
mean >= 0.51 and mean - SEM >= 0.50. Knockout routes need not pass adequacy:
their failure can be the loss being measured. Each contrast is full minus
knockout, separately on ecological rank and density log score.

- `supported`: lower bands exceed 0.02 rank and 0.01 density.
- `bounded_small`: upper bands are <= both margins.
- `uncertain`: every other interval configuration.

Both-process removal must show a supported loss before any attributed state.
Given that gate, two supported individual losses yield `joint_required`;
one supported loss and the other's bounded-small loss yield `a_specific` or
`b_specific`; two bounded-small individual losses yield
`redundant_predictive_support`. Other combinations retain uncertain attribution.
These are predictive route states, not causal mechanism identifications.

## Development advancement gate

Publish all state counts on all 152 pairs, retaining unavailable/uncertain
states. Among the 43 mixed generating-truth pairs, count correct specific
attribution and every false inclusion (wrong specific attribution or joint
necessity that includes the false process).

Before considering an unused-seed endpoint, development must show at least
95% precision among specific calls, correct specific attribution on at least
20% of all mixed pairs, and false inclusion on no more than 5% of mixed pairs.
This conservative engineering screen requires accuracy and coverage together;
it is not a new empirical success claim. These screen values are fixed before
running v23. Failure keeps fresh validation unauthorized.

Record source identities and implementation commit. Preserve v21/v22 results
and Product A's non-promotion. Product B stays blocked.
