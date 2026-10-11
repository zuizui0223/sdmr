# Real-v5 first10: spatial transfer versus random-location interpolation

**Status:** post-terminal exploratory development, not independent ecological validation. The original frozen fresh-v5 result remains **failed_closed**, with 16/300 stable-sharp cells. No sealed answer-check data, post-hoc species exclusions, or altered scientific thresholds enter this diagnostic.

## Identical models, same 10 plants, different validation split

The earlier first10 process-closure study used the exact original frozen three spatial GroupKFold folds. To test whether **spatial generalization** is the bottleneck, this follow-up uses three-fold KFold (seed 0) on **sorted unique frozen `location_id`**, assigning all records from an exact location to one fold. It retains the same 10 selection-ranked taxa, 46 predictors, six process closures, L2 formulations, fixed HGB recipe, full-system authorization rule (balanced log score >= -0.75, >= 0.01 gain over -log 2, p<=0.001 after 999 fixed-seed permutations), interval margin 0.01 and one-fold-SEM state rule. Every closure knockout excludes **all** registered predictors for its named process.

| Same-runtime learner | Spatially held-out full-system authorization | Random-location full-system authorization |
|---|---:|---:|
| Converged original raw-feature L2 | 1/10 | 9/10 in the full closure run; 8/10 in independent full-system screen (see numerical caveat) |
| Train-fold standardized isotropic L2 | 1/10 | **9/10** |
| Unchanged shallow3 HGB | 4/10 | **10/10** |

The **predeclared primary agreement pair** for this new diagnostic is standardized isotropic L2 versus HGB. **Both were authorized for zero taxa in the original spatial folds, versus nine taxa (54 process cells) under random-location interpolation.** An absence of jointly authorized taxa does **not** yield a 0% conditional agreement rate: that conditional quantity is undefined for the spatial arm.

## Process-closure results in random-location folds

All 10 taxa × 3 learners × (full + six whole-process knockouts) × 3 folds = **630 fits** were evaluated, with **210/210** numerical/execution certificates per learner in the full closure run. A separate arithmetic audit reproduced **180 process classifications**, **120 pair classifications**, all **630 fit records** and both full-system counts. It does not independently refit models or recompute the permutation p-values.

For standardized isotropic L2 versus HGB, among the 60 declared taxon–process cells:

| Joint state | Count | Interpretation |
|---|---:|---|
| Replaceable | **29** | Both learners provide a noninferior process-free information route |
| Contributory | **3** | Both indicate information loss on whole-closure knockout |
| Required | **0** | None reached the particularly strong required-state rule |
| Unresolved | **22** | Both may be adequate but sharp process information does not agree |
| Unavailable | **6** | One entire taxon fails the standardized linear full-system gate |

Thus **32/60 (53.3%)** cells were stably sharp under random-location interpolation; among jointly authorized cells it is **32/54 (59.3%)**, a descriptive *conditional* rate that does not replace the fixed denominator. The spatial contrast yielded zero jointly eligible cells and hence zero stably sharp cells by the mandatory abstention rule. **These are not biological process-truth recovery rates.** The original prespecified empirical threshold 240/300 (80%) cannot be reused to claim that this development result passes or fails a new independent test.

Within the nine jointly eligible taxa, the unresolved counts are particularly frequent for **thermal** (7 of 10 total thermal cells, with one unavailable). For **productivity**, eight of ten cells are jointly replaceable, one unresolved, one unavailable. Both describe how predeclared environmental information is reconstructed; neither proves absence or causal unimportance of either process. There is no independently known biological ground truth in these real species.

## Solver certificate sensitivity is not suppressed

The *secondary* original-objective L2 model is sensitive to a value-preserving matrix-memory-layout change for *Tinospora smilacina*. A standalone full-system-only calculation classified one of its three raw-ridge fits as numerically nonconverged (8/10 authorized); the full-closure calculation used an equivalent but Fortran-contiguous full predictor matrix and certified that fit (9/10 authorized). The held-out score difference is < 1e-12. In the C-contiguous case the **second initialization** hit the fixed `max_iter=100` limit, whereas both initializations passed with the Fortran-contiguous copy. No convergence tolerance or data were changed. The affected taxon's **secondary** eligibility and up to six consensus cells therefore depend on numerical certification details; do not select a layout by which produces more favorable states. The **primary standardized L2 + HGB result (32/60)** is unaffected by this observed contrast.

## Interpretation and next methodological choice

Random-location KFold admits nearby locations into both training and validation; an easier interpolation problem is **not** evidence of transfer to new regions, stable physiological niches, ecological causes or superior SDM tuning. Conversely, the spatial-arm failure does not prove that ecological processes are intrinsically nonidentifiable. It shows that reliable spatial prediction itself was not jointly attainable for these fixed species and learners. Even where random-location interpolation makes nine species jointly eligible, 22/54 comparison-ready process cells remain unresolved.

**Next priority:** define a *new prospective* matched-eligibility benchmark that tests both information-state accuracy with known process truth **and** spatial transfer under comparable learners and split regimes. An independent cohort or preregistered holdout is required before an ecological/generalization claim. Reclassifying the original v5 by substituting random-location results is prohibited.

## Evidence and provenance

- Frozen raw first10 model-pool input: SHA-256 `9a2574ab03506123b1119ed92b5432f5929a293b4d790bed38ac5290ac281237`, archived GitHub Actions run 38134483278.
- Frozen feature artifact with source `location_id`: SHA-256 `7488bff59e4da00db8420afcdccbb1627f1b52455609483ab9413a0b1f166aa0`, run 37545674411. Read only the frozen occurrence/background **model-pool indices**.
- Frozen registry Git blob: `6e3e7fc8d3d46cbd4bb983914beadf315635d45b`; frozen process-classifier Git blob: `7ff69d91d88025bfcb5c69aac95aa7b9b723ae0c`.
- Original three-fold spatial output SHA-256 `53d77d314a04f96c6c9bd7adfdf4d635fb683532926e2a9025d52746e7e693c2`.
- Random-location first10 full-closure output SHA-256: `7c05f11b12232beb340ff56c3e0ca9b6ac24d0b1102bb5b7ae36671766fe2f84`.
- Compact species-wise and 120 pair-state evidence are in `results/v5_matched_split_taxa_v1.csv` and `results/v5_matched_random_consensus_v1.csv`. Full fold-level files are available in the research evidence bundle; this summary is **not** an independent prospective ecological validation.
