# SDMR fresh empirical pre-freeze v1

Status: **prefreeze scaffold / no fresh empirical outcomes opened**

## Current authorization boundary

SDMR v6 prospective known-truth v2 passed its one-shot unused-seed panel:

- workflow run: `36212033498`
- artifact id: `10896590112`
- artifact digest: `sha256:7c0c3dd6f12a0478abcd0fadabdb013a26356ac7ac6dacca7bc2cbdabee7fe68`
- KT-A through KT-F: **PASS**
- fresh empirical data opened: **false**

This satisfies the prerequisite for designing the fresh plant validation. It does **not** authorize immediate answer-check access.

## What is frozen now

The pre-freeze scaffold already fixes the boundaries that must not drift during cohort construction:

- Product-A remains `closed_not_reopened`;
- first fresh cohort = vascular plants, occurrence-only;
- historical Product-A taxa are excluded;
- post-outcome taxon replacement is forbidden;
- outer answer-check split is coordinate-only and frozen before environmental feature access;
- answer-check remains sealed;
- plant process taxonomy remains:
  - thermal
  - water
  - seasonality
  - radiation_energy
  - soil_substrate
  - productivity
- primary ecological reconstruction metric = balanced presence/background log score;
- comparator families are predeclared:
  1. AUC-oriented flat selector
  2. correlation/VIF flat filter
  3. matched-learner strong flat predictive selector
  4. SDMR process-first
- learner disagreement is not averaged away; disagreement remains unresolved;
- scientific promotion is the strict conjunction `EMP-A & ... & EMP-F`;
- EMP-E allows zero abstention-integrity violations;
- EMP-F requires declared-denominator integrity.

## Still intentionally unfrozen

No fresh outcome may be opened until all of these are fixed:

1. exact cohort denominator inside the predeclared 30–50 planning range;
2. cohort eligibility rules and exact taxon identity manifest;
3. source/provider manifest, temporal window, occurrence QC, accessible-area rule;
4. process-registry manifest;
5. prediction guardrail;
6. primary flat comparator;
7. learner/design panel;
8. numerical EMP-A through EMP-D thresholds.

The validator therefore has two levels:

- `validate_prefreeze_contract`: checks the no-outcome boundary and structural invariants;
- `validate_final_freeze_contract`: additionally requires every execution-critical denominator, manifest, comparator, learner route, guardrail, and EMP threshold.

## Next scientific task

Select the exact denominator and EMP-A–EMP-D thresholds using development/power calculations that do not inspect the future fresh answer-check. Then freeze the source/taxon manifests and only after that create a one-shot empirical execution receipt.
