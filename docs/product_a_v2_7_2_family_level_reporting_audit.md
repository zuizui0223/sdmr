# Product-A v2.7.2 family-level reporting audit

Status: **reporting-only audit of frozen evidence / no new scientific experiment**.

This document derives manuscript-ready family-level summaries from the already frozen v2.7.2 known-truth artifact. It does not alter the v2.7.2 endpoint, thresholds, seeds, candidate set, or scientific interpretation.

## Frozen source

- workflow run: `32629842082`
- implementation: `9b40393dda3d03943a403d0e7875e2d616b914e7`
- frozen ref: `frozen/product-a-v2-7-2-known-truth-9b40393d`
- replicate-A artifact: `v272-known-truth-a`, artifact `9490817718`, digest `sha256:78b261f95c31d6c1df1f29aa02988abba2398bfca2765e7afdfe83d0acf74d4e`
- terminal decision artifact: `9490827277`, digest `sha256:033b5393444f0d7365d6823d068e08778454496213f0f438188680740f846a17`
- unused seeds: `3101–3110`
- six preregistered niche families, 10 cases each, 60 total.

The audit reads only `ecological_inference_certificates.csv` and `observation_signal_summary.csv` from the pinned artifact.

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

## New reporting insight from existing evidence

The aggregate result is not driven by one easy generator. Four distinct families — asymmetric, gaussian, interaction and observation-confounded — had perfect mean stable-core precision and recall. The two informative boundary cases are different:

1. `omitted_driver` retains perfect precision but recall falls to `0.90`, showing that missing driver information primarily creates unresolved/omitted truth rather than false necessity;
2. `soft_threshold` retains recall `1.00` but precision falls to `0.9333`, showing that gradual threshold structure is the principal family in which an extra stable-core process can survive.

This distinction should be shown rather than hidden behind the pooled mean because it makes the failure envelope of the estimator explicit.

## Process consensus is more stable than exact model consensus

Across the 60 v2.7.2 cases, exact model consensus occurred in `38/60`, whereas process-set consensus occurred in `50/60`. Family-level contrasts are strongest for asymmetric (`0.40` model vs `0.80` process) and gaussian (`0.50` vs `0.90`).

This is direct evidence for the manuscript claim that ecological information can remain identifiable even when the exact fitted model is not.

## Observation-process specificity

The global observation correction activated in `10/10` observation-confounded cases and in `0/50` cases from the other five niche families. This is the family-level form of the frozen headline activation result (`1.000` in the confounded family, `0.000` elsewhere).

## Nature-track use

Use this audit in the main or Extended Data figure that demonstrates breadth of the controlled-truth result. The preferred display is a six-row precision/recall panel plus model-consensus versus process-consensus markers.

Do **not** describe these as six empirical ecosystem types. They are six controlled niche-generating families and support generality across declared simulation structures, not direct transfer to ecological truth in nature.
