# Separating-evidence refinement v24 — development contract

## Question

v23 established that forcing one winner from the same occurrence-derived support evidence is often the wrong estimand. The next question is not how to rank the same evidence more aggressively, but:

> Can genuinely new, prospectively declared separating evidence shrink a v23 co-supported process set without deleting truly active processes?

## Base object

The base object is the frozen v23 `supported_set` for one context. v24 never adds a process that was not already in that set. It is therefore a **refinement operator**, not a new activity detector.

## What counts as new separating evidence

A separator is eligible only if:

1. its input source is disjoint from the information used to create the v21 support call;
2. its decision rule is frozen before separator outcomes are inspected;
3. its context and process keys align with the v23 set member being evaluated;
4. its required separator roster is declared before outcome access.

Examples that could satisfy this in a future study include temporally resolved observations, an independent observation channel, direct physiological/demographic measurements, intervention or natural-experiment contrasts, or external transfer conditions in which currently co-supported processes make different predeclared predictions.

A relabeling, transformation or reranking of the v21/v22 evidence is not new separating evidence.

## Evidence states

Every required separator returns one of four states for one currently supported process:

- `exclude`: qualified positive evidence against retaining that member;
- `compatible`: evidence remains compatible with that member;
- `indeterminate`: the comparison does not resolve the member;
- `unavailable`: the required evidence could not be evaluated.

Only `exclude` can support deletion.

## Refinement rule

For process `p` in base set `S_v23`, remove `p` only if **every required predeclared separator** is present, qualified and returns `exclude`.

Any of the following retains the member:

- a compatible separator;
- an indeterminate separator;
- unavailable separator evidence;
- a missing required separator;
- an unqualified separator.

This gives a monotone rule:

`S_v24 subseteq S_v23`

but contraction is never forced. Empty refined sets are allowed if every base member is independently excluded under the frozen rule.

## Why unanimous exclusion

The failure mode uncovered in earlier SDMR development was repeatedly the same: absence of sufficient positive evidence was converted into a stronger biological state. v24 therefore makes deletion harder than retention. Uncertainty does not count as exclusion.

This is intentionally conservative. Its scientific value is not that it guarantees contraction, but that any observed contraction has a clear evidentiary meaning.

## Future performance target

The primary successor comparison is not top-1 accuracy. It is the trade-off between:

- set-size contraction;
- false deletion of a truly active process already present in the v23 set.

Development readouts include:

- mean set-size contraction;
- fraction of contexts contracted;
- true-base-member false-deletion rate;
- false-base-member removal rate;
- context-level probability of deleting any true member;
- exact truth-set rate after refinement in known-truth benchmarks.

A useful separator should reduce false-member burden and/or set size while keeping true-member deletion below a prospectively frozen tolerance.

## Governance

This PR freezes the refinement semantics only. It does not choose a winning separator from consumed v21/v23 outcomes and does not authorize empirical validation.

Before a future performance test, the following must be frozen on a new unused denominator:

1. separator evidence class and source;
2. separator acquisition/sampling design;
3. separator decision rule and calibration;
4. required separator roster;
5. false-deletion tolerance and contraction endpoint;
6. fresh denominator.

Forbidden rescue routes include v22 winner reuse, v21 support reuse masquerading as new evidence, process-specific penalties, post-truth member deletion, and post-outcome separator replacement.
