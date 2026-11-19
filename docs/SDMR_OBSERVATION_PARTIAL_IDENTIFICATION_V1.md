# SDMR × Structural: sharp observation-selection partial identification v1

**New algebraic method extension, 2026-11-19. No new ecological data opened.** This is not a rerun of M5 or the 80-case Structural known-truth experiment. It is a separate *finite-population identification calculation* for an explicitly defined binary endpoint and complete original observation opportunity.

## Question

When recorded forest responses are selected or missing in ways that may depend on their actual biological outcome, how much of the between-group response contrast is nevertheless identified *without asserting missing at random*?

The earlier [exact two-world counterexample](SDMR_STRUCTURAL_SELECTION_NONIDENTIFIABILITY_V1.md) proves point identification can fail even when full observed opportunity and marginal effort are identical. The appropriate response is not to tune predictors until a positive result appears, but to report the set of outcomes compatible with what was actually observed.

## Estimand and observable inputs

Let \`X=0\` and \`X=1\` be two **predefined** categories (e.g., a source-verified context or structural stratum). Let \`Y\` be the original binary **measured** response. \`S=1\` means the outcome was actually observed.

For each \`x\` require a complete, audited at-risk physical sampling-opportunity denominator:

- \`p_x\`: actually recorded binary outcomes \`Y=1\`
- \`z_x\`: actually recorded binary outcomes \`Y=0\` after real observation effort; **not** GBIF nondetections, records absent from a table, missing trees or unsampled plots
- \`m_x\`: outcomes genuinely unknown despite an eligible opportunity
- \`N_x=p_x+z_x+m_x>0\`: **all** eligible physical units or preregistered risk-events in that group

No assumption about the missingness mechanism \`P(S=1|X,Y)\` is imposed. If every missing outcome could be either zero or one, then the sharp population-mean bounds are

\[
\frac{p_x}{N_x}
\le P(Y=1\mid X=x)
\le \frac{p_x+m_x}{N_x}.
\]

For the observed-population **association contrast** \(\Delta=E[Y|X=1]-E[Y|X=0]\),

\[
\Delta_{\min}=\frac{p_1}{N_1}-\frac{p_0+m_0}{N_0},\qquad
\Delta_{\max}=\frac{p_1+m_1}{N_1}-\frac{p_0}{N_0}.
\]

The bounds are *sharp*: each endpoint is attained by a completion of the unobserved binary responses. They are **identification bounds**, not confidence intervals; they do not account for sampling error and do not identify an intervention or a biological mechanism. No spatial or temporal independence is presumed by this algebra; external generalization requires a separate physical-block design.

## Worked exact example on the already synthetic two-world construction

The two indistinguishable worlds have exactly the following **conditional probability masses**, scaled to eight opportunities per \`X\` group. These eight counts are *fractional-probability bookkeeping, not sampled trees*.

| Group | Recorded positive | Recorded negative | Unknown outcome | Eligible total | Compatible risk |
| --- | ---: | ---: | ---: | ---: | --- |
| X=0 | 1 | 3 | 4 | 8 | 1/8 to 5/8 |
| X=1 | 3 | 1 | 4 | 8 | 3/8 to 7/8 |

Consequently **\(\Delta\in[-1/4,\,3/4]\)**. The true association contrast \(\Delta=1/2\) in the ecological-response world and \(\Delta=0\) in the selection-only world are both admissible. This is an exact, non-asymptotic representation of the failure to identify a unique process response from recorded data.

## When is the sign identified despite unknown outcomes?

A positive sign requires \(\Delta_{\min}>0\), i.e.
\[
\frac{p_1}{N_1} > \frac{p_0+m_0}{N_0}.
\]
A negative sign requires \(\Delta_{\max}<0\). With an *illustrative synthetic* ten-opportunity group where \`X=0:(p,z,m)=(1,8,1)\` and \`X=1:(8,1,1)\`, every missing-data completion gives \(\Delta\in[3/5,4/5]\), so the association sign is positive regardless of arbitrarily outcome-dependent recording. Reversing groups gives a negative interval. These are **not field ecological effect estimates**.

If the interval contains zero, the program returns \`unresolved_including_zero\`; it must not replace that result with a consensus-learner positive call.

## Code and guards

- [Implementation](../src/sdmr/observation_partial_identification_v1.py) in exact Python \`Fraction\` arithmetic; strict integer denominator and distinct group IDs.
- [Regression tests](../tests/test_observation_partial_identification_v1.py) exhaustively check sharpness for every valid small denominator up to five opportunities per group, positive/negative/unresolved cases, invalid denominators, and the exact pre-existing two-world proof.
- No finite bounds are emitted unless \`complete_source_frame_verified=True\` **and** \`actual_recorded_negatives_verified=True\` are explicitly supplied. These are *caller declarations*, not a self-proving absence of hidden observation bias. A separate source audit must establish them.
- Result receipts always declare \`causal_process_identified=False\`, \`biological_result_estimated=False\`, \`newly_opened_field_responses=False\`.
- Results remain **conditional on the declared source risk set**. Stratification choices, post-outcome selected subcohorts, missing entire sampling opportunities or extra latent unrecorded taxa can destroy the population-frame interpretation.

**Not directly applicable to presence-only GBIF.** GBIF occurrence records do not enumerate verified \`Y=0\` nor the complete number of eligible unrecorded sites. Only an independent survey with an audited opportunity and actual negative-outcome frame can use these numeric bounds without a different, separately justified identification model.

## Forest field-source development boundary

Harvard Forest HF453 (2021–2024) and the 2026 BCI Dryad source remain **codebook-level candidates**. A published tag or file preview does not establish valid original individual event identities, verified survey effort or a complete at-risk denominator, and \`HF453 DN\` (not found) cannot be silently coded as an observed dead tree. HF453 is one forest, not a cross-biome replication. No original raw tree file was retrieved or parsed during this extension. Both candidate data sources remain blocked for new biological inference.

The next field step is the **source/original-file hash → measured status and risk set → prospective response freeze** sequence. The partial-identification algebra can then be used as an additional conservative analysis alongside the standard source-observation audit, never to rescue the original Product A or M5 frozen outcome.

## Original frozen science unchanged

- Product-A v2.8.4 remains \`not_promoted\`; Product B remains blocked.
- Original M5 71/80 and 0/700, Structural KT 30/30 and 0/50 are separate results, not summed.
- Existing FIA spatial BA 5/5 and temporal BA-change 2/5 remain retrospective selected-survivor comparisons; neither is upgraded to causal forest dynamics.
- The new sign-identification algebra is **a methodological implication, not an observed forest result**.
