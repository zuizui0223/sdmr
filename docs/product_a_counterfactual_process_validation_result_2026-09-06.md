# Product A counterfactual process validation — fresh 4301–4305 result

Status: **SUPPORTED under the frozen validation contract / new scientific result / thresholds unchanged after validation**.

## Why this validation was required

The earlier v2.7.2 stable-process-core result was strong within its six known-truth families, but temperature and water were generating processes in all 60 cases. A new prospectively frozen 35-case factorial test on seeds 4201–4205 independently varied temperature, water and soil truth and falsified broad generalization of the old stable-core rule:

- old stable-core exact process-set recovery: `22/35 = 0.6286`;
- AUC-selected winner exact process-set recovery: `25/35 = 0.7143`;
- temperature specificity: `0.6667`;
- water sensitivity: `0.70`;
- soil specificity: `0.8667`;
- predeclared factorial support status: **not supported**.

Those 4201–4205 cases were then consumed as discovery evidence only.

## Successor estimand

The successor no longer infers process membership from the process set of a selected fitted model. For each declared process, it asks a direct counterfactual ecological-recovery question:

> How much does the best achievable held-out environmental niche overlap decline when every candidate carrying that declared process is excluded, after retaining the same prediction-adequacy gate?

The score uses only model-pool/held-out ecological recovery evidence, not hidden generating truth. The metric is `niche_overlap_schoener_d_pc12`; it is not a weighted super-score.

For each of five frozen perturbations:

1. apply the existing independent-transfer adequacy gate (`mean presence-rank >= 0.51` and `mean - SEM >= 0.50`);
2. find the best overlap among adequate candidates carrying the process;
3. find the best overlap among adequate candidates after all representations of that process are excluded (`temp_proxy` is grouped with `temperature`);
4. normalize their overlap difference by the overlap range among adequate candidates;
5. average the process-specific score across perturbations.

## Discovery calibration, frozen before fresh validation

Discovery seeds `4201–4205` were never reused for validation.

The discovery score separated true versus false process membership with the following observed boundaries:

| process | max false score | min true score | frozen midpoint threshold |
|---|---:|---:|---:|
| temperature | 0.252195 | 0.278597 | 0.265396 |
| water | 0.052498 | 0.081836 | 0.067167 |
| soil | 0.206753 | 0.461730 | 0.334242 |

Thresholds, process sets, candidate library, perturbations and validation seeds were frozen before seeds `4301–4305` were opened.

## Fresh validation design

- process identities: `{T}`, `{W}`, `{S}`, `{T,W}`, `{T,S}`, `{W,S}`, `{T,W,S}`;
- unused seeds: `4301–4305`;
- denominator: `7 × 5 = 35` cases;
- each process true in 20 cases and false in 15;
- same factorial generator, 12-candidate library and five perturbations as discovery;
- primary gate: exact process-set recovery >=0.80 and sensitivity/specificity >=0.80 for each of temperature, water and soil.

## Fresh result

**All preregistered support gates passed.**

### Complete process-set recovery

- counterfactual process rule: **`30/35 = 0.8571`**;
- old stable-process-core rule on the same fresh cases: `23/35 = 0.6571`;
- AUC-selected fitted winner: `25/35 = 0.7143`.

This comparison is descriptive for the old stable/AUC roles; the scientific support gate was defined prospectively for the counterfactual estimator.

### Per-process identification

| process | true n | false n | TP | FN | TN | FP | sensitivity | specificity |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| temperature | 20 | 15 | 20 | 0 | 14 | 1 | **1.000** | **0.933** |
| water | 20 | 15 | 20 | 0 | 12 | 3 | **1.000** | **0.800** |
| soil | 20 | 15 | 20 | 0 | 14 | 1 | **1.000** | **0.933** |

The new estimator therefore recovered **all 60 true process-presence decisions** across the three process dimensions, with five false-positive process decisions among 45 true absences.

### Model disagreement

The canonical and perturbation-robust ecological selectors selected different fitted models in `18/35` fresh cases. The counterfactual process set remained exactly correct in **`15/18 = 0.8333`** of those cases.

### Paired comparison with AUC winner

Across the same 35 fresh cases:

- both exact: `24`;
- counterfactual exact / AUC wrong: **`6`**;
- AUC exact / counterfactual wrong: `1`;
- both wrong: `4`.

Thus the new process-specific counterfactual estimator solved six cases that a direct AUC-winner process interpretation missed, while losing one case that AUC got exactly right.

## Five remaining counterfactual errors

The remaining errors were all false-positive process inclusions; there were no false-negative process decisions:

- `{T}`, seed 4301 → false water added;
- `{T}`, seed 4304 → false water added;
- `{W}`, seed 4303 → false soil added;
- `{S}`, seed 4305 → false temperature added;
- `{T,S}`, seed 4303 → false water added.

Thus the current failure mode has shifted from missing true drivers (especially water under the old stable-core rule) to conservative over-inclusion of an extra process.

## Frozen provenance

- validation workflow: `Product A counterfactual process validation`;
- run: `34015684015`;
- source head: `8cdcef922a25c1655907657e06e9ba8cc6004a1b`;
- artifact: `9983844728`;
- artifact digest: `sha256:9a53abc38c45e93eb8696f1de7af5051776881c59ec5079f45b4ecc029068554`;
- validation contract: `configs/product_a_counterfactual_process_validation_contract.json`.

## Scientific interpretation

This result materially changes Product A. The broad independent-process problem that the old stable-core rule failed (`22/35`) now has a prospectively frozen successor that passes on unused process identities/seeds (`30/35`) while achieving 100% sensitivity for all three independently varying ecological processes and >=80% specificity for each.

The method does **not** establish causal or physiological necessity, and it does not alter the earlier fresh empirical v2.8.4 `not_supported / not_promoted` endpoint. It establishes controlled-truth recovery of declared environmental-process information from occurrence-only ecological-recovery evidence when process identities genuinely vary.
