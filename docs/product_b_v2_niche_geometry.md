# Product-B v2: universal ecological processes from niche-geometry degradation

## Current boundary

Product B already has a v1-era implementation in `drivers.py`, `universality.py`, and
`product_b_cli.py`.  That implementation is useful, but its unseen-taxon necessity
checks are still centered on conventional predictive performance (especially
presence-rank/AUC-like transfer).

Product A v2.6 changed the scientific target: model adequacy remains a guardrail,
while ecological tuning is based on recovery of realized environmental niche
geometry.  Product B v2 therefore upgrades the universal-driver question to the
same target rather than reverting to predictive-score importance.

Formal Product-B empirical inference remains blocked until the separate Product-A
promotion decision explicitly unblocks it.  The code in this document is safe to
develop and test before that point because it consumes only already-frozen
Product-A model-pool evidence and never opens sealed empirical environments.

## Unit of evidence

For a frozen Product-A ecological representative, compare:

- the unmodified procedure; and
- the exact same procedure after removing one ecological process domain.

Pair evidence within the identical `taxon × M × spatial fold` cell.  Positive
process-loss values always mean that process removal made niche recovery worse.

The four Product-A ecological axes are retained separately:

1. Schoener D in frozen PC1–PC2 audit space — higher is better;
2. niche centroid distance — lower is better;
3. breadth log-SD error — lower is better;
4. quantile-profile error — lower is better.

Prediction loss (`presence_rank_loss`) is retained as a guardrail/diagnostic, not
as the definition of ecological necessity.

## No weighted importance score

A process drop is called Pareto-worsening only when it does not improve any of the
four niche-recovery axes beyond numerical tolerance and makes at least one axis
strictly worse.  Trade-offs remain explicit rather than being hidden in an
arbitrary weighted score.

## Hierarchy

1. `taxon × M × fold × process`: paired niche-geometry loss;
2. `taxon × process`: complete-M/fold process-constraint profile;
3. discovery taxa: nominate process-core candidates;
4. unseen validation taxa: confirm or reject transfer of those candidates;
5. repeated taxon splits: estimate universality stability.

This makes Product B a genuine second product:

- **Product A:** which modelling procedure most faithfully recovers the niche?
- **Product B:** once that procedure is frozen, which ecological processes are
  repeatedly necessary to recover niche geometry across taxa?

## Important claim boundary

The output is evidence for a cross-taxon **realized environmental process core**.
It is not automatically a causal physiological requirement or a fundamental-niche
limit.  Stronger causal language still requires independent physiological,
demographic, experimental, or known-truth evidence.
