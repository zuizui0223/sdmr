# Nature Ecology & Evolution editorial-readiness gate — updated 2026-09-06

Status: **submission-production assessment after supported counterfactual validation and independent replication**.

## Current recommendation

**Proceed toward a first-shot Nature Ecology & Evolution Article submission once final CI/visual QA and external metadata are complete.** The scientific package is materially stronger than the earlier problem-framing version because Product A now contains a prospectively validated and independently replicated process-membership estimator.

## Gate 1 — Concrete advance beyond one tuner

**PASS.**

The central advance is a process-specific counterfactual estimand:

> among prediction-adequate models, how much best attainable held-out ecological niche recovery is lost when every declared representation of one environmental process is excluded?

The output is process membership under a frozen representation registry, rather than variable importance or selected-model identity.

## Gate 2 — Advance beyond `prediction ≠ explanation`

**PASS strongly.**

Prior work already establishes prediction/explanation and discrimination/functional-recovery distinctions. Product A goes further by prospectively showing:

1. ecological Pareto sharpening can create false necessity;
2. a stable-process intersection that looked strong in an easier suite fails when T/W/S truth is allowed to vary independently (**22/35** exact);
3. a process-specific counterfactual recovery statistic can be calibrated on discovery truth, frozen, validated on unused truth and independently replicated unchanged;
4. process membership and stronger process necessity remain distinct estimands.

## Gate 3 — Positive controlled-truth evidence

**PASS with independent replication.**

### Strong factorial falsification

Seven non-empty T/W/S process combinations × seeds 4201–4205 = 35 discovery cases.

- predecessor stable core exact: **22/35 = 62.9%**;
- AUC winner exact: **25/35 = 71.4%**;
- predecessor exact under model disagreement: **12/20 = 60%**.

The old method was not rescued.

### Fresh counterfactual validation

Unused seeds 4301–4305, n=35:

- exact process set: **30/35 = 85.7%**;
- T sens/spec **1.000/0.933**;
- W **1.000/0.800**;
- S **1.000/0.933**;
- exact under model disagreement **15/18 = 83.3%**.

Every preregistered ≥0.80 gate passed.

### Unchanged independent replication

Unused seeds 4401–4410, n=70; no method or threshold change:

- counterfactual exact: **65/70 = 92.9%**;
- AUC winner exact: **56/70 = 80.0%**;
- predecessor exact: **49/70 = 70.0%**;
- exact under ecological-model disagreement: **27/30 = 90.0%**;
- T sens/spec **1.000/0.933**;
- W **1.000/0.933**;
- S **0.975/1.000**.

All replication support gates passed.

This is now the primary Nature-level positive result.

## Gate 4 — Necessity claim remains bounded

**PASS.**

The earlier v2.6 exclusion certificate remains a separate stronger estimand:

- false-required=0;
- possible-process recall=1.0;
- possible-process precision≈0.467;
- `required_processes` empty in 9/9 validation taxa.

Therefore the 92.9% counterfactual result must be called **process-membership identification**, not physiological or causal necessity.

## Gate 5 — Empirical lane adds an honest boundary

**PASS but remains the principal editorial vulnerability.**

Frozen v2.8.4:

- complete 3/3 denominator;
- prediction guardrail passed;
- ecological nondomination 3/3;
- strict ecological improvement 0/3;
- `empirical_confirmation_not_supported`;
- `not_promoted`;
- ecological/AUC candidate and predictors identical in 108/108 matched cells.

The new controlled-truth success does not generate a real-plant process answer key. The main desk-risk therefore remains limited direct empirical biological consequence.

## Gate 6 — Claim boundaries

**PASS.** The manuscript now distinguishes:

- process membership from process necessity;
- counterfactual recovery loss from selected-variable importance;
- controlled generating truth from real occurrence evidence;
- declared alias/process registry from complete real-world proxy closure;
- descriptive AUC comparison from a preregistered universal-superiority claim;
- 108 empirical reporting cells from the n=3 primary empirical denominator.

## Gate 7 — 30-second editorial argument

1. Standard model selection does not identify ecological process membership.
2. We made the problem harder by independently switching temperature, water and soil across all seven possible non-empty process sets; our preceding estimator failed at **22/35**.
3. We then measured counterfactual ecological-recovery loss when a process and all declared aliases were removed from prediction-adequate candidates.
4. Thresholds were frozen on discovery truth, followed by **30/35** fresh validation and **65/70** unchanged independent replication; T/W/S sensitivity was 0.975–1.000 and specificity 0.933–1.000 in replication.
5. Exact process truth remained recoverable in **27/30** cases even when the ecological fitted models themselves disagreed.
6. Fresh plant data remain empirically non-identifying (108/108 selector collapse), so the paper preserves its external-validity boundary instead of inventing a biological answer.

## Main editorial risk

The biggest remaining NEE risk is no longer “there is only a problem statement.” It is **external biological validation**: the strongest process-identification evidence is controlled truth. Real plant data supply neither an independent process answer key nor divergent selected models in the frozen endpoint.

That is a legitimate Nature desk-risk, but the paper now has a concrete estimator, prospective falsification, fresh validation and unchanged independent replication. This is substantially stronger than the earlier inferential-framework-only package.

## Article production gate

Scientifically **PASS**. Final production requires:

- latest Nature reporting workflow green with the new counterfactual Fig.3 and all hard assertions;
- visual QA of Fig.3;
- standard repository CI and real-API smoke green;
- external author/funding/competing-interest metadata;
- permanent DOI archive of exact submission state.

## Transfer rule

If NEE rejects mainly for insufficient empirical biological validation/breadth rather than validity, transfer the same frozen evidence to **Nature Communications**, then **Methods in Ecology and Evolution** if needed. Do not retune the counterfactual estimator between submissions.

## Hard stop

Discovery, fresh validation and independent replication are complete. No favorable-seed search, process-set deletion, threshold change, candidate addition, perturbation change or empirical rescue is authorized.
