# Observation standardization: analytic diagnostic

This diagnostic was written while v25 ran, without changing its frozen code
or reading its final outcomes. It does not establish the cause of v25's result.

## Identity under a declared toy model

Suppose the balanced occurrence/background density ratio factorizes as
`r(x) * w(z)`, with ecological environment x independent of observation covariate
z under the reference distribution, and both reference means equal to one.
The exact balanced posterior is `p(x,z) = r(x)w(z)/(1+r(x)w(z))`.

For an ecological reference population, the balanced posterior is
`r(x)/(1+r(x))`. Averaging `p(x,z)` over z does not in general recover it.
Averaging the odds `p/(1-p)` does recover r under these assumptions, followed
by converting the averaged odds back to probability.

The current `score_ecological_suitability` averages probabilities. That is a
valid partial-dependence operation, but it is not generally the same estimand
as standardizing a multiplicative density ratio. The balanced log-score
function remains proper; the issue is calibration of its ecological input.

## Exact finite example

Take ecological ratios `[0.25, 0.75, 2.0]` with uniform reference weights and
observation multipliers `[0.2, 1.8]` with equal weights. Both means are one.

| Ecological ratio | Mean probability | Ecological posterior | Odds-based recovery |
| --- | ---: | ---: | ---: |
| 0.25 | 0.178982 | 0.200000 | 0.200000 |
| 0.75 | 0.352451 | 0.428571 | 0.428571 |
| 2.00 | 0.534161 | 0.666667 | 0.666667 |

The population balanced log scores are -0.643675 for mean probability and
-0.621689 for the correctly standardized posterior. The difference, about
0.021986, is not model estimation error: the conditional posterior was exact.

## Connection to consumed evidence

Among v23's 87 pairs lacking established joint contribution, 44 passed the
rank-loss gate but failed the density-loss gate, 31 failed both, and 12 passed
density but failed rank. This makes density calibration worth investigating;
it does not show that correcting it would recover those 44 pairs.

## Restrictions on a successor

Finish v25 unchanged. If a separate successor is justified, standardization
must use only training-reference data, preserve observation-role separation,
and explicitly state its factorization assumptions. It must be tested on
occurrence data, including the observation-confounded family, with the same
fixed advancement screen. No true suitability values may enter that learner.
Do not infer calibrated ecological probabilities under arbitrary ecological /
observation dependence or unrestricted interaction from this toy identity.
