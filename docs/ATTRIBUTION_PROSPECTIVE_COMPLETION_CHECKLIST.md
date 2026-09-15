# Prospective attribution completion checklist

This is a completion audit, not authorization to execute a new simulation
cohort. The large goal is not complete when a consumed-development screen
passes, when CI passes, or when an implementation is pushed.

## 1. Candidate admission

- Preserve each previous consumed-development endpoint, including failures.
- Replay the candidate's entire frozen pair denominator from saved scores.
- Verify source/target omission identities and incomplete-evidence accounting.
- Apply the existing development screen without changing its thresholds:
  specific precision >= 0.95, correct mixed-pair specificity >= 0.20, mixed
  false inclusion <= 0.05. All three are required for this admission route.
- Record the exact candidate implementation, configuration, dependencies,
  receipts, and raw-evidence archive hash. A development pass is not evidence
  of unused-simulation performance.

## 2. Freeze before fresh execution

- Audit the proposed seed namespace against repository history, saved runs,
  workflow records, and accessible artifacts. Record the search scope and any
  gaps; absence from the current checkout alone does not establish non-use.
- Freeze the complete seed/family cohort, simulation parameters, selection
  implementation, candidate implementation, and scoring/classification rules.
- Freeze the pair-selection rule and its eligible denominator before looking
  at generating truth. The realized pair count may depend on the predeclared
  selection rule; it must not be forced to equal the consumed 152-pair count.
- Specify all screening denominators, empty-denominator handling, unresolved
  and failed-fit treatment, success criteria, and technical stop rules.
- Publish the frozen contract and exact implementation reference before
  generating the new cohort. Do not choose seeds or families based on outcomes.

## 3. Execute and preserve the full endpoint

- Record exact runtime provenance and the realized selection manifest.
- Fit/classify without generating truth as an input; freeze pair states before
  scoring against generating labels.
- Keep every selected pair in the declared endpoint, including unavailable,
  inadequate, uncertain, and otherwise unresolved results. Account separately
  for contexts that yield no selected pairs.
- Preserve raw score evidence, execution failures, and terminal run status.
- Replay all classifications and recompute all denominators from saved files.
- Do not restart a valid slow run or silently repair a failed scientific
  endpoint. Any permitted infrastructure retry must retain the original
  attempt and use the same frozen scientific inputs and rules.

## 4. Terminal audit

- Report the prospectively defined pass, failure, or technical-stop outcome;
  distinguish technical inability to evaluate from a scientific negative.
- Include all family-level and overall readouts required by the frozen
  protocol, not just the best subset.
- Retain claim boundaries: simulation- and model-conditional predictive
  attribution is not biological causality or general observational
  identifiability. An unresolved contrast is not evidence of absence.
- Archive the complete evidence with checksums and reproducibility commands,
  and verify the remote implementation and relevant CI.
- A failed prospective endpoint may complete the evaluation objective when
  it is faithfully recorded; it does not establish that the method succeeded.
  Later tuning must be a separately labeled development stage, never a
  reinterpretation of the frozen endpoint.

Product A remains closed and not promoted. Product B remains blocked. No
new empirical acquisition or empirical confirmation is part of this goal.
