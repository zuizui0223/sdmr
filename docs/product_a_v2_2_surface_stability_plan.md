# Product-A v2.2: procedure-level ecological surface stability

## Current decision

Product-A v2.1 repaired candidate availability and complete-fold evidence, but its
repeated unseen-seed known-truth replication ended in
`differentiated_not_supported`. Canonical ecological recovery differed from
canonical AUC in only one of three panels and was not non-inferior across the full
hidden-truth profile in that disagreement panel. No empirical confirmation may be
opened from that result.

## v2.2 target

Reuse the already-defined ecological surface-stability semantics from
`sdmr.niche_recovery_stability` at the **procedure** level. Independent outer
spatial refits of the same procedure must be projected onto one deterministic
model-pool background reference after observation-process marginalization.
Selection remains staged:

1. complete candidate evidence in every predeclared taxon × M × outer-fold cell;
2. absolute record-prediction adequacy gate;
3. mean held-out ecological recovery Pareto front;
4. common-reference ecological surface-stability Pareto/minimax gate;
5. ecological predictor count only as a final tie-break.

Recovery and stability are never added into a weighted score. A stable but
biologically uninformative surface cannot bypass the preceding recovery gate.

## Information barrier

- Old empirical external-sealed results remain falsification-only.
- Known-truth panels with seeds 11–123 are opened development evidence and cannot
  validate v2.2.
- Real empirical data are not read by the v2.2 known-truth line.
- Generating truth opens only after all discovery-taxon selectors are frozen.
- Negative, indistinguishable and abstention outcomes remain valid.

## Predeclared unseen panels

Run all panels without changing thresholds, procedures, selectors or truth metrics
between panels.

- panel S1 discovery: gaussian 171, asymmetric 181, interaction 191;
  validation: soft_threshold 201, omitted_driver 211,
  observation_confounded 221.
- panel S2 discovery: gaussian 172, asymmetric 182, interaction 192;
  validation: soft_threshold 202, omitted_driver 212,
  observation_confounded 222.
- panel S3 discovery: gaussian 173, asymmetric 183, interaction 193;
  validation: soft_threshold 203, omitted_driver 213,
  observation_confounded 223.

## Decision rule

Compare `canonical_auc`, `canonical_ecology`, `robust_ecology` and
`stable_ecology`.

- `surface_stability_supported`: stable ecology is selected in every panel,
  differs from canonical AUC in at least one panel, every disagreement panel is
  truth-evaluable, and stable ecology is not worse than canonical AUC in both
  hidden-truth worst-rank and mean-rank.
- `surface_stability_indistinguishable`: stable ecology never differs from AUC.
- `surface_stability_not_supported`: at least one evaluable disagreement is worse.
- `surface_stability_unstable_or_abstained`: stable ecology cannot be selected in
  every panel.

None of these outcomes authorizes empirical promotion. A supported result only
permits freezing the procedure before a newly rebuilt sealed-before-M empirical
confirmation.
