# Frozen real-v5 learner failure: post-terminal diagnostic, not a promotion

Authoritative source: model-pool-only GitHub Actions run **37613738626**, artifact **11487215382**, `model_pool_freeze/` CSVs. Analyses below use only its **frozen** `full_system_authorization_all_taxa.csv`, `route_states_all_taxa.csv`, and `stable_states_all_taxa.csv` data, with no answer-check or model refit.

## Where the gate fails

| Frozen condition | L2 logistic, raw 46 predictors | shallow3 HGB |
|---|---:|---:|
| Complete 46 environmental rasters | 50 | 50 |
| Full system meets absolute balanced log score ≥ −0.75 | **15/50** | **41/50** |
| Mean improvement over chance ≥ 0.01 | **10/50** | **32/50** |
| Fixed-prediction within-fold permutation p ≤ 0.001 | **44/50** | **48/50** |
| Strict full authorization | **10/50** | **32/50** |
| Median held-out balanced log score | **−0.83357** | **−0.62743** |

The paired HGB score exceeds logistic for **48/50 taxa**; the frozen difference HGB − logistic has median **+0.24873** and mean **+0.50021**. The logistic route is **not** merely failing due to a null p value: its minimum prediction improvement is the primary authorization bottleneck. A significant permutation result can coexist with poor absolute prediction.

Breakdown of the 40 logistic authorization failures:
- **29** fail absolute adequacy + minimum gain although the permutation test is significant;
- **5** pass absolute adequacy but fail minimum gain with a significant permutation result;
- **6** fail adequacy + minimum gain + permutation significance.
Thus **34/40** lack sufficient improvement **even though p is significant**.

### Significant does not mean adequate prediction

Of 50 taxa, **33** on raw logistic had both permutation p ≤ .001 **and** a held-out balanced log score worse than the constant 0.5-probability baseline (−log 2 ≈ −0.6931); HGB had **15** such taxa. Among the **34** significant-but-insufficient-gain logistic failures, median observed score was **−0.8837**, while the median corresponding shuffled-label null mean was approximately **−2.049**. For example, *Pentapogon quadrisetus* had logistic score **−1.13469** (below chance calibration) but mean permuted-label score **−2.31001** and p = .001. Thus fixed-prediction permutation significance can coexist with poor absolute calibrated log score: it detects information relative to the particular shuffled-label null, not reliable predictive probability or process identification.

## After both learners authorize

The same 10 taxa authorize on both routes, so 10 × 6 = 60 process cells. Frozen final states are:
- replaceable **15**;
- contributory **1**;
- required **0**;
- unresolved **44**.

The 44 unresolved include **34** different learner states and **10** cells unresolved on both learners. The median process knockout `delta_sem` on these jointly authorized taxa is **0.03224** for logistic vs **0.006806** for HGB. These are uncertainty summaries of the same type of held-out score difference, not direct estimates of biological variance.

Within the jointly authorized ten taxa, the six process groups each have ten cells. Stable-sharp counts by process are:
thermal **2**, water **2**, seasonality **4**, radiation_energy **3**, soil_substrate **2**, productivity **3**. No process has enough consistently sharp cross-learner evidence to support a broad claim.

## Fixed-HGB upper bound on any logistic-only repair

The frozen rule requires both learners to report the same sharp process state. Define `S` as the stable-sharp subset and `H` as the sharp states returned by the **unchanged frozen HGB**. Necessarily `S ⊆ H`, even if a scaled/new logistic classifier perfectly predicts and agrees with HGB on every eligible cell. Since `|H| = 125` of the 300 frozen process cells, **a logistic-only modification cannot produce more than 125/300 = 41.7% stable-sharp decisions**, below the original prespecified EMP-D minimum **240/300 = 80%**. This is a deterministic set-inclusion ceiling under a fixed HGB, not a new inferential success or failure. The original v5 is already closed and cannot be rescued.

Therefore the exploratory standardization intervention is diagnostic of the source of learner authorization differences, **not** a route to pass the original EMP-D gate. A genuinely new process-identification design would also need to understand and improve the HGB closure-evidence stage, or establish that abstention is ecologically appropriate.

## Plausible, NOT yet demonstrated causes

1. **Scaling and penalization**. v5 fitted a linear L2-logistic model with the raw 46 environmental representations, **without standardization**. Because an L2 penalty operates on coefficient magnitudes, unit/scale differences can change regularization pressure. This is a modifiable implementation choice, not an ecological result.
2. **Nonlinear capacity**. HGB may represent interactions/nonmonotonic environmental responses unavailable to plain linear logistic; this alone does not prove ecology is nonlinear, because the models also differ in estimation and scale behavior.
3. **Information-state uncertainty**. Even with both learners authorized, 44/60 remain unresolved or disagree. Real process closures may be observationally inseparable, undersampled, spatially confounded or affected by missing variables; the frozen result does not discriminate among these mechanisms.

### Safe next test

`experiments/v5_standardization_probe.py` isolates the **scaling** factor on the first ten selection-ranked taxa without changing folds or using answer-check data. It first checks that a replay of the original raw logistic matches the archived scores. The comparison is exploratory/post-terminal, not a new independent prospective validation. Other hypotheses must be tested separately.

### Original terminal boundary

Frozen fresh-v5 **EMP-D failed** at 16/300 stable sharp cells against prespecified ≥0.80, **before answer-check opening**. EMP-A/B/C also later failed; E/F passed. This report does **not** turn unavailable process states into biological absence and does not alter the original denominator or promotion status.
