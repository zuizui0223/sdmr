# v6 known-truth determinism probe — retired attempt 1

## Terminal classification

The first prospective v6 known-truth attempt is **retired at the determinism gate**.

- workflow run: `34103111132`
- head SHA: `1334100e35e84afc0046bd48edccb937c714c727`
- frozen seed denominator: `14001–14010`
- family × replicate nontruth jobs: `12 / 12` technically completed
- generating-process truth opened: **no**
- scientific performance claim from this denominator: **not allowed**

The terminal evaluator stopped while comparing the two independently executed nontruth artifacts, before the code path that calls `infer_true_processes`.

## Failure

The predeclared transport parity envelope was `atol=1e-12`, `rtol=1e-10`. Independent hosted runners produced small floating differences in route-level summaries. The first terminal failure was:

- field: `mean_presence_rank`
- reference: `0.7392363922140741`
- reconstructed: `0.7392496838619734`
- absolute difference: `1.3291647899316139e-05`

This is a determinism-gate failure, not a failed ecological-process result.

## Full truth-blind replicate audit

The two replicate artifacts were compared for all six frozen families before any generating-process labels were opened.

| family | maximum absolute floating drift | discrete differences | finite-mask differences |
|---|---:|---:|---:|
| gaussian | 0 | 0 | 0 |
| asymmetric | 0 | 0 | 0 |
| soft_threshold | 2.3423839166696048e-05 | 0 | 0 |
| interaction | 0 | 0 | 0 |
| omitted_driver | 0 | 0 | 0 |
| observation_confounded | 5.8711274099999995e-05 | 0 | 0 |

Across the complete audit:

- process states and other discrete outputs differed in **0 cells**;
- finite/non-finite masks differed in **0 cells**;
- the maximum observed absolute floating drift was **5.87112741e-05**;
- floating drift was confined to route-summary metrics in `soft_threshold` and `observation_confounded`.

Therefore the retired attempt establishes only that the original numerical transport envelope was too strict for independent hosted execution. It does **not** reveal or score generating-process truth.

## Frozen technical successor

The successor is defined in `configs/proxy_closed_route_process_challenge_v6_known_truth_validation_successor_v2.json`.

Only two technical changes are allowed:

1. retire seeds `14001–14010` and use fresh seeds `15001–15010`;
2. replace the transport-only floating parity envelope with `atol=1e-4`, `rtol=1e-6` while retaining exact discrete identity.

The estimator, process registry, model family, purge degree/ridge, interval margins, and all scientific promotion gates are unchanged. The new absolute tolerance is 1% of the smallest scientific evidence margin (`0.01`), so it cannot itself relax a scientific process decision threshold.

The retired 14001–14010 denominator may be used only as this truth-blind technical reproducibility probe and may not be reused for a prospective performance claim.
