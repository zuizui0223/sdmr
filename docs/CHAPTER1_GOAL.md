# Chapter 1 goal — SDMR

Program ID: `niche-to-survey-four-chapter-v1`

**Chapter 1 = environmental niche-driver selection.**

## Scientific goal

Develop and communicate an interpretable, leakage-resistant way to decide which environmental dimensions should define a species' realized environmental niche. Occurrences used for variable/model choice belong to a model pool; separate occurrences are withheld as a sealed answer-check pool. Background/reference environments support fitting and projection but are not the biological answer key.

The chapter is therefore about **which environmental axes/drivers are defensible for niche interpretation**, not about maximizing a generic model-accuracy score. Ordinary prediction remains an adequacy/guardrail layer; the ecological target is recovery of the environmental distribution occupied by previously unseen occurrences. Literal generating-driver truth is available only in known-truth simulation.

## Hierarchical interpretation

Chapter 1 now fixes a future interpretation/design hierarchy rather than treating every raster as the same kind of object:

```text
geophysical template
    → direct environmental field
    → integrated biological exposure
    → composite summary representation
```

The preferred future logic is **process selection → representation selection → sealed answer-check**. Predictors can be explicitly tagged as spatial geometry, substrate, direct environment, derived exposure, proxy, or composite summary. A selected raster is not automatically a causal driver.

See [`CHAPTER1_HIERARCHICAL_DRIVER_FRAMEWORK.md`](CHAPTER1_HIERARCHICAL_DRIVER_FRAMEWORK.md) and [`../configs/chapter1_predictor_role_schema.json`](../configs/chapter1_predictor_role_schema.json).

## Current chapter endpoint

The completed Product-A v2.8.4 fresh endpoint and the separate `not_promoted` decision remain authoritative. The empirical result did not support general strict ecological improvement over the AUC-selected comparator under the frozen panel, while the known-truth lane remains valid evidence about recovery under controlled truth.

## Current implementation goal

No new Product-A scientific experiment is allowed. Remaining Chapter-1 work is:

1. manuscript framing around interpretable environmental-variable/niche-driver selection;
2. precise explanation of model-pool versus sealed answer-check occurrence roles;
3. hierarchical interpretation of predictor roles without post-outcome reselection;
4. figures/tables that separate known-truth recovery from empirical non-promotion;
5. journal formatting, copyediting and submission.

## Boundaries

- Do not retune taxa, M, seeds, sealed fraction, thresholds, candidate library, predictor universe or denominator.
- Do not reopen Product B under the current Product-A decision.
- Do not absorb Chapter-2 z/t niche geometry into Product A.
- Do not reinterpret background points as biological absences or as the answer-check truth.
- Do not use the hierarchy as a post-outcome rescue of Product A; any hierarchy-aware empirical method requires a genuinely new prospective contract and independent evidence.
