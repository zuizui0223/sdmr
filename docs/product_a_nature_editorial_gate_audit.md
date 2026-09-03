# Product A — Nature Ecology & Evolution editorial-gate audit

Status: **submission-readiness audit / no new Product-A science**.

Nature Ecology & Evolution states that editorial review considers the advance to field understanding, soundness of conclusions, whether the evidence supports those conclusions, and the wide relevance of the conclusions to the journal readership. This document maps the frozen Product-A evidence to those gates.

## Gate 1 — Does the paper advance understanding of ecology rather than only SDM software?

**Current status: PASS if the manuscript leads with ecological identification; FAIL if it leads with tuning performance.**

Nature-level advance:

> predictive validation and ecological necessity are different inferential tasks; necessity must be challenged against adequate alternatives.

Evidence making this more than a conceptual essay:

- controlled truth separates prediction/stability from process correctness;
- Pareto sharpening prospectively creates false necessity;
- falsification-first exclusion recovers process truth without false-required claims;
- process information is more stable than exact model identity in v2.7.2 (`50/60` vs `38/60` consensus);
- fresh empirical evidence shows distinct selection objectives can collapse to exactly the same fitted solution (`108/108` cells).

The manuscript must avoid presenting `SDMR` as the novelty noun in the title/first paragraph. The novelty noun is **ecological identification**.

## Gate 2 — Are the conclusions supported by the evidence?

**Current status: PASS with strict claim boundaries.**

Supported:

- process-identification logic is measurable and high-performing under controlled truth;
- good-model agreement can be anti-conservative;
- explicit unresolved/unavailable states prevent unsupported negative claims;
- deterministic implementation matters when numerical drift can alter discrete selected predictors;
- fresh empirical superiority over AUC was not supported;
- empirical selector contrast was exactly absent in the frozen endpoint.

Not supported and therefore prohibited:

- universal empirical superiority over AUC;
- direct empirical recovery of true generating ecological processes;
- fundamental-niche recovery;
- universal plant-driver claims;
- a complete real-world proxy closure around each process.

The formal v2.8.4 `empirical_confirmation_not_supported` and `not_promoted` states must remain visible in the Abstract/Results/Discussion.

## Gate 3 — Is the result broadly relevant across ecology and evolution?

**Current status: PARTIAL/PASSABLE; this is the main editorial risk.**

The argument generalizes beyond SDMs whenever an ecological analysis has:

1. observational rather than experimental evidence;
2. correlated or substitutable measurements/proxies;
3. a winner selected from multiple fitted explanations;
4. a biological interpretation that is stronger than the predictive criterion used to choose the winner.

Examples include habitat-driver models, trait–environment regressions, ecological network predictors, observational community models, macroecological driver selection and some comparative analyses.

The manuscript should state this general class explicitly but must not claim these domains were empirically validated by Product A. SDMs are the worked test bed from which the identification principle is derived.

## Gate 4 — Is there a striking empirical biological consequence?

**Current status: LIMITATION, not fixable within closed Product A.**

The fresh endpoint did not produce a case in which ecological and AUC selectors chose different fitted candidates and led to different ecological conclusions. Instead they collapsed to the same candidate in `108/108` cells.

For a Nature editor this is weaker than an empirical example where a new inference method changes a major biological conclusion. The manuscript therefore has to make the collapse itself scientifically important:

> observational equivalence can prevent a model-selection contest from carrying any information about ecological necessity.

Do not seek a new favorable plant panel to manufacture divergence. That would violate the Product-A hard stop and weaken the prospective evidence story.

## Gate 5 — Is the paper understandable outside the SDM specialist community?

**Current status: PARTIAL; manuscript production task.**

Required language changes:

- introduce the problem using “prediction”, “alternative explanations” and “necessity” before AUC, Boyce, M or predictor-universe terminology;
- define presence-only data in one sentence;
- move workflow/version names to Methods and Extended Data;
- use one conceptual figure to show winner selection versus identification;
- use “unresolved” before implementation labels such as `unavailable`;
- explain observational equivalence without assuming statistical-identification jargon.

## Nature first-decision risk assessment

### Strongest reasons to send for review

- prospective falsification sequence rather than one favorable benchmark;
- direct known-truth counterexample to false necessity;
- high final controlled-truth accuracy across six generating families;
- exact computational reproducibility;
- unusually transparent retention of a full-denominator negative empirical endpoint;
- exact 108/108 empirical selector collapse provides a clean identification result.

### Strongest reasons for editorial rejection

- method could be viewed as SDM-specific;
- empirical lane lacks observed process truth;
- no empirical biological conclusion changes because the selectors do not diverge;
- the long development history could look technical if version provenance leaks into the main narrative.

## Submission decision

**Proceed with Nature Ecology & Evolution first.**

The current evidence is strong enough to justify the attempt, provided the final Article is written as a general ecological-inference paper rather than a software/method benchmark. No additional Product-A science is required or permitted before submission.

If rejected for breadth/priority, transfer the same frozen evidence package to Nature Communications. If rejected for methodological specialization rather than validity, route to Methods in Ecology and Evolution. Do not modify the scientific endpoint between these submissions.
