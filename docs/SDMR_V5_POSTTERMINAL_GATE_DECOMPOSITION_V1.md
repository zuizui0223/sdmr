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

## Direct 2026-10-11 BLAS falsification and next input parity control

The **post-terminal diagnostic** workflow [38108779636](https://github.com/zuizui0223/sdmr/actions/runs/38108779636) tested the original frozen first four taxa with BLAS thread counts **1, 2, 4, 8**. Every setting returned the **same** frozen-helper and handwritten replay predictions (maximum canonical-vs-handwritten discrepancy ~1.78×10⁻¹⁵), as well as exactly the same mismatches to the 2026-10-07 archive:

| Frozen selected rank | Name | Original log score | Replayed log score | Absolute mismatch |
|---|---|---:|---:|---:|
| 1 | *Pentapogon quadrisetus* | −1.13469 | −1.13469 | 0 |
| 2 | *Westringia eremicola* | −2.98891 | −2.98891 | 0 |
| 3 | *Acacia concurrens* | −1.17838 | −1.21598 | 0.03761 |
| 4 | *Tinospora smilacina* | −1.37608 | −1.60827 | 0.23219 |

Thus **BLAS thread count is not an explanation for the observed differences within the tested settings**. The raw L-BFGS learner hit 1,000 iterations in every one of those 12 held-out folds, whereas training-fold standardized logistic did not; nonconvergence remains a real technical weakness but is not yet established as the *specific cause* of historical replay divergence.

A separate new diagnostic now refits the original **shallow3 HGB full-system learner on the identical assembled inputs and grouped folds**. HGB acts as an independent parity control because it does not use the problematic L-BFGS optimization path. If original HGB scores reproduce even for taxa where logistic does not, the source of the discrepancy is narrowed toward optimizer/computation. If HGB scores also diverge, investigate input row ordering, feature transformations, and original spatial-group membership before discussing a scaling effect. The original v5 promotion status remains closed either way.

## 2026-10-11 decisive cross-learner replay result

The new *unchanged frozen full-46 shallow3-HGB fitting helper* was run on **the same selected first 10 plants, the same model-pool feature arrays, and the same three grouped folds** as the raw logistic replay. The post-terminal development workflow [38109685807](https://github.com/zuizui0223/sdmr/actions/runs/38109685807) completed and archived its [source-backed first10 diagnostic artifact](https://github.com/zuizui0223/sdmr/actions/runs/38109685807).

| Learner's original v5 held-out balanced log score | Exact-match taxa (≤ 0.001) | Maximum absolute error |
|---|---:|---:|
| shallow3 HistGradientBoosting | **10/10** | **0.000000** |
| raw, nonstandardized L2 logistic | **5/10** | **0.23218884** |

For every tested species, HGB matched the archived score **bit-for-bit at recorded floating-point precision**, including Acacia concurrens and Tinospora smilacina, where the raw logistic differed by 0.03761 and 0.23219, respectively. A separate independent raw-logistic implementation agrees with the original v5 logistic fitting helper within **2.7×10⁻¹⁵**, so *its* implementation is not causing the mismatch. Moreover the frozen raw logistic hits `max_iter=1000` in **30/30 folds** on the first ten species, versus **0/30** for a training-fold standardized learner. Taken together, this strongly **localizes** archive-versus-replay drift to the nonconverged logistic numerical optimization path rather than feature loading, predictor order or spatial splitting, **but it does not prove the exact low-level source of the drift**.

**Exploratory new-runtime within-pool comparison (not a v5 replay outcome):** training-fold standardization improved balanced log score for **7/10** first-rank taxa (3 worsened), with a median difference **+0.11159** and arithmetic mean **+0.43427**; the mean is strongly affected by one +2.83060 outlier. The raw new-runtime model authorizes **0/10** taxa and the standardized model **1/10**. Because the frozen raw-logistic archive only matches 5/10, these exploratory values are **not** an authorized v5 improvement estimate, do **not** update promotion evidence, and do **not** establish stable process closure states. The programmed headline `paired_mean_score_gain` remains **null** when original raw replay fails.

**Consequence:** scaling/solver convergence is a strongly supported *technical bottleneck*, but can explain neither the observed real-plant ecological processes nor all original EMP-D failures. The fixed original HGB alone yielded 125/300 sharp cells, far below 240/300, so a logistic-only intervention would not rescue the original method. A successor requires a separate prospective assessment of closure-level identifiability after the basic numerical learner is repaired.

## Plausible, NOT yet demonstrated causes

1. **Scaling and penalization**. v5 fitted a linear L2-logistic model with the raw 46 environmental representations, **without standardization**. Because an L2 penalty operates on coefficient magnitudes, unit/scale differences can change regularization pressure. This is a modifiable implementation choice, not an ecological result.
2. **Nonlinear capacity**. HGB may represent interactions/nonmonotonic environmental responses unavailable to plain linear logistic; this alone does not prove ecology is nonlinear, because the models also differ in estimation and scale behavior.
3. **Information-state uncertainty**. Even with both learners authorized, 44/60 remain unresolved or disagree. Real process closures may be observationally inseparable, undersampled, spatially confounded or affected by missing variables; the frozen result does not discriminate among these mechanisms.

### Safe next test

`experiments/v5_standardization_probe.py` isolates the **scaling** factor on the first ten selection-ranked taxa without changing folds or using answer-check data. It first checks that a replay of the original raw logistic matches the archived scores. The comparison is exploratory/post-terminal, not a new independent prospective validation. Other hypotheses must be tested separately.

### Original terminal boundary

Frozen fresh-v5 **EMP-D failed** at 16/300 stable sharp cells against prespecified ≥0.80, **before answer-check opening**. EMP-A/B/C also later failed; E/F passed. This report does **not** turn unavailable process states into biological absence and does not alter the original denominator or promotion status.
