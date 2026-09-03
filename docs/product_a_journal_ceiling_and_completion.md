# Product-A journal ceiling and completion gates

Status: **submission strategy / no scientific endpoint change**.

This document separates (i) the highest journal that the current frozen Product-A evidence can reasonably challenge, (ii) the strongest realistic target, and (iii) what additional independent science would be needed for a higher-tier successor paper. Journal scope should be rechecked immediately before submission.

## Current-paper journal ladder

### Challenge ceiling — Ecology Letters, Method

Why it is a legitimate challenge:

- the manuscript is no longer a taxon-specific SDM benchmark; its central claim concerns the distinction between model selection and ecological identification under observational substitutability;
- the method is computational/conceptual and has a falsification sequence rather than a single software demonstration;
- the framework is potentially general across occurrence-only ecological modelling problems and across taxa;
- the paper contains a concrete new inferential technique: set-valued, falsification-first process identification with explicit unresolved/unavailable states and protected information barriers.

What must be true before an Ecology Letters Method proposal is sent:

1. Main text is compressed to a general ecological problem, not a repository/version history.
2. The method is demonstrated as taxon-general in controlled truth and framed as applicable beyond the 12 empirical plants.
3. Figure 1 makes the conceptual advance immediately visible: prediction adequacy versus ecological identification.
4. Figure 2 supplies the decisive counterexample: predictive/stable models can attribute the wrong process; Pareto sharpening can create false necessity.
5. Figure 3 shows the positive solution: falsification-first exclusion and v2.7.2 recovery.
6. Figure 4 shows the empirical boundary without trying to rescue it.
7. A concise proposal explains why the problem matters to ecologists beyond SDM specialists.

Main risk: the frozen fresh empirical endpoint does not demonstrate strict ecological advantage over AUC. Therefore the paper must be evaluated as a general identification-method contribution, not as an empirically superior predictor-selection algorithm.

### Primary target — Methods in Ecology and Evolution

Best current fit because the manuscript's main contribution is the description, analysis and falsification of a new analytical/conceptual methodological framework. The complete evidence sequence, known-truth performance, deterministic implementation and explicit empirical boundary are strengths rather than mismatches.

Submission condition: all scientific completion gates below pass. No additional Product-A experiment is required or allowed.

### Strong fallback — Ecological Informatics

Appropriate if editors/reviewers regard the work primarily as computational SDM methodology, reproducibility/governance and ecological information separation rather than a broad methodological advance.

## Dream ceiling beyond the current paper

### Nature Ecology & Evolution — possible only for a successor-level advance

The current Product-A paper alone should not be rewritten to manufacture this route. A genuinely stronger successor would need to show that the identification distinction changes ecological conclusions of broad importance, not merely that the inference framework works under known truth.

A plausible future Nature Ecology & Evolution package would require independent prospective evidence such as:

- process/representation exclusion under a fully predeclared proxy closure;
- multiple independent empirical systems with externally measurable ecological truth or intervention/experimental evidence;
- demonstration that winner-based SDM interpretation gives materially different biological conclusions whereas identification-aware inference avoids those errors;
- broad consequences for macroecology, conservation prioritisation, climate-response inference or biodiversity forecasting;
- no reuse of the consumed Product-A endpoint as confirmatory evidence.

This is a new research programme, not missing Product-A analysis.

### Nature Methods — not a current-paper target

Although computational/statistical biological methods are in scope, the expected validation and application are broad across life-science research. Product A is presently an ecology-specific inferential framework with controlled-truth validation and a non-promoted empirical endpoint. Reaching this level would require major generalisation beyond SDM plus important biological applications across domains.

## Scientific completion gates for the current paper

### Gate 1 — Claim audit

Pass `docs/product_a_manuscript_claim_audit.md`:

- controlled truth versus empirical evidence separated everywhere;
- no complete proxy-closure claim;
- no causal-driver claim from raster selection;
- v2.8.4 preserved as non-support/not-promoted;
- Product B blocked.

### Gate 2 — Main-text compression

The main text must contain five scientific Results, not a chronological software-version diary:

1. prediction/stability != process identification;
2. retained-model agreement != necessity;
3. falsification + abstention protects truth;
4. deterministic set inference becomes safe and sharp;
5. fresh empirical test bounds external validity.

Version/run/artifact details move to Methods or Supplement unless essential to an information-boundary argument.

### Gate 3 — Figures

Required main figures:

1. **Conceptual identification diagram** — model selection versus ecological identification, including model-pool/sealed and unseen-taxon barriers.
2. **Prospective falsification sequence** — which interpretation failed and what inferential rule replaced it.
3. **Known-truth positive result** — v2.6 safety to v2.7.2 safe+sharp recovery; include P/R/F1 and deterministic parity.
4. **Fresh empirical boundary** — 3/3 evaluable, guardrail pass, nondominated 3/3, strict improvement 0/3, delta 0.0, not-promoted.

Optional Extended/Supplement figure: availability-state taxonomy (`supported`, `not_supported`, `unavailable`, `technical`) and examples v2.4/v2.5/v2.7.3/v2.8.3.

### Gate 4 — Methods/provenance supplement

Complete a compact reproducibility supplement containing:

- data/source fingerprints;
- spatial and unseen-taxon barriers;
- candidate/procedure definitions;
- known-truth generator families and frozen seeds;
- calibration and abstention rules;
- process certificate semantics;
- observation-process correction;
- deterministic RNG identity;
- v2.8.4 fresh execution identity and full denominator;
- claim-state glossary.

The repository remains the full audit trail; the supplement should make the paper independently understandable without asking a reviewer to read hundreds of commits.

### Gate 5 — Literature positioning

The Introduction/Discussion must explicitly distinguish SDMR from:

- predictive discrimination/calibration metrics (AUC, Boyce/CBI, omission);
- information-criterion/parsimony tuning (AICc where valid);
- multicollinearity/VIF filtering;
- spatial cross-validation and transferability assessment;
- ensemble/model-selection uncertainty;
- variable importance and permutation/drop-one analyses;
- causal/ecophysiological inference;
- partial identification/set-valued inference and falsification concepts where relevant.

Novelty should be claimed for the ecological-identification synthesis and its prospectively falsified necessity, not for inventing every individual component.

### Gate 6 — Submission package

For MEE:

- final title and abstract;
- main manuscript;
- 4 main figures;
- concise evidence/provenance supplement;
- code/data availability;
- cover letter centred on the identification problem and prospective falsification;
- explicit statement that the fresh empirical endpoint did not support strict advantage and was not retuned.

For an Ecology Letters Method challenge, first prepare the journal's Method proposal/pitch from the same frozen paper; do not add favorable post hoc Product-A data to improve the pitch.

## Current next action

No new Product-A scientific computation.

The remaining work is manuscript validation and production in this order:

1. evidence-to-claim audit;
2. figures from frozen evidence;
3. literature-positioning audit;
4. full Methods/provenance supplement;
5. MEE-ready manuscript package;
6. decide whether to send an Ecology Letters Method proposal first or submit directly to MEE.
