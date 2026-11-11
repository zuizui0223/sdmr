# Product-A v2.7.2 family-level reporting audit

Status: **reporting-only audit of frozen consensus-first process-stability evidence / no new scientific experiment**.

This document derives manuscript-ready family-level summaries from the already frozen v2.7.2 known-truth artifact. It does not alter the endpoint, thresholds, seeds, candidate set or interpretation.

## Estimand boundary

The v2.7.2 `stable_process_core` is the intersection of process sets supported by the canonical ecological-recovery selector and the perturbation-robust ecological-recovery selector. It is a **consensus-first process-stability** object. It is **not** the process-exclusion necessary-process set evaluated in the v2.4–v2.6 branch.

## Frozen source

- workflow run: `32629842082`;
- implementation: `9b40393dda3d03943a403d0e7875e2d616b914e7`;
- frozen ref: `frozen/product-a-v2-7-2-known-truth-9b40393d`;
- replicate-A artifact: `9490817718`, digest `sha256:78b261f95c31d6c1df1f29aa02988abba2398bfca2765e7afdfe83d0acf74d4e`;
- terminal artifact: `9490827277`, digest `sha256:033b5393444f0d7365d6823d068e08778454496213f0f438188680740f846a17`;
- unused seeds `3101–3110`;
- six preregistered niche families × 10 cases = 60 total.

The audit reads only frozen `ecological_inference_certificates.csv` and `observation_signal_summary.csv`.

## Stable-process-core recovery by niche family

| niche family | n | mean precision | mean recall | mean F1 | process-set consensus | exact model consensus |
|---|---:|---:|---:|---:|---:|---:|
| asymmetric | 10 | 1.0000 | 1.0000 | 1.0000 | 0.80 | 0.40 |
| gaussian | 10 | 1.0000 | 1.0000 | 1.0000 | 0.90 | 0.50 |
| interaction | 10 | 1.0000 | 1.0000 | 1.0000 | 0.80 | 0.60 |
| observation-confounded | 10 | 1.0000 | 1.0000 | 1.0000 | 1.00 | 1.00 |
| omitted-driver | 10 | 1.0000 | 0.9000 | 0.9400 | 0.70 | 0.70 |
| soft-threshold | 10 | 0.9333 | 1.0000 | 0.9600 | 0.80 | 0.60 |

Across all 60 cases the frozen headline remains precision `0.9889`, recall `0.9833`, F1 `0.9833`.

## Family-level failure envelope

The pooled result is not driven by one easy generator. Four families—asymmetric, gaussian, interaction and observation-confounded—had perfect mean stable-core precision and recall.

The two boundary families fail differently:

1. `omitted_driver`: precision remains 1.0 while recall falls to 0.90. The stable core misses part of the generating process set but does not add a false stable-core process in the pooled family mean.
2. `soft_threshold`: recall remains 1.0 while precision falls to 0.9333, so an additional non-generating process can persist in the selector-consensus core.

These statements concern stable-core inclusion/omission, not process-exclusion necessity or `unresolved` certificate states.

## Process consensus versus exact model consensus

Across 60 cases, exact model consensus occurred in `38/60`, whereas process-set consensus occurred in `50/60`. The largest contrasts were asymmetric (`0.40` exact-model versus `0.80` process-set) and gaussian (`0.50` versus `0.90`).

This directly supports the bounded claim:

> **process information can be more stable across ecological selectors than exact fitted-model identity under controlled truth.**

It does not establish that stable processes are necessary.

## Observation-process specificity

Observation correction activated in `10/10` observation-confounded cases and `0/50` cases from the other five families.

## Nature-track use

Use this audit for Figure 3 / Extended Data on **consensus-first process stability**. Always label the six rows as controlled niche-generating families, not empirical ecosystem types. Never attribute these P/R values to the exclusion-based necessity estimator.