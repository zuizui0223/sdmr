# Product A counterfactual process-recovery result — 2026-09-06

Status: **authoritative new Product-A controlled-truth result; fresh validation and independent replication complete**.

## Scientific question

Can an occurrence-only SDM procedure identify which environmental processes actually generate a niche when the truth status of temperature, water and soil varies independently, rather than merely retaining process labels that are always true?

The complete non-empty process-set universe was frozen as:

`{T}`, `{W}`, `{S}`, `{T,W}`, `{T,S}`, `{W,S}`, `{T,W,S}`.

Each process is therefore truly present in 4/7 process sets and absent in 3/7. With 10 replication seeds, each process has 40 true and 30 false case-level labels.

## 1. Factorial falsification of the predecessor

The first prospective factorial test used discovery seeds `4201`–`4205` across all seven process sets (`n=35`). Candidate library, perturbations and denominator were frozen in `configs/product_a_factorial_process_recovery_contract.json` before outcomes.

The predecessor consensus-first stable process core did **not** generalize strongly enough:

- exact complete process-set recovery: **22/35 = 62.9%**;
- AUC-selected winner exact process-set recovery: **25/35 = 71.4%**;
- exact recovery when the two ecological fitted models disagreed: **12/20 = 60.0%**;
- temperature sensitivity/specificity: **1.00 / 0.667**;
- water sensitivity/specificity: **0.70 / 0.867**;
- soil sensitivity/specificity: **1.00 / 0.867**.

This result is authoritative non-support for extending the earlier v2.7.2 `55/60` stable-core result to independently varying process membership. The earlier 60-case suite had temperature and water true in every case.

## 2. Counterfactual process estimator

Product A was therefore reformulated at the process level rather than repaired by another winner rule.

For one declared process `p` and one predeclared sampling/background perturbation `q`:

1. candidates must first satisfy the frozen prediction-adequacy gate (mean presence-rank ≥0.51 and mean−SEM ≥0.50);
2. adequate candidates are divided into those carrying `p` and those excluding **all declared representations** of `p` (for example, both `temperature` and `temp_proxy` belong to the temperature process);
3. calculate the best held-out Schoener-D environmental-niche overlap achievable in each class;
4. normalize their difference by the overlap range across all adequate candidates;
5. average the process-specific gap across the five frozen sampling/background perturbations.

For ordinary comparable perturbations,

`g_pq = (best D containing p − best D excluding p) / range(D among adequate candidates)`.

If no adequate excluded candidate exists the perturbation score is `+1`; if no adequate process-containing candidate exists it is `−1`. No hidden process truth enters this score.

The estimand is therefore **counterfactual ecological-recovery loss under process exclusion**, not whether a particular fitted model contains the process.

## 3. Discovery-only threshold freeze

Only the `4201`–`4205` discovery cases were used to calibrate process-specific score thresholds. The observed discovery separation was:

- temperature: maximum false `0.2521953801`, minimum true `0.2785974936` → frozen threshold **0.2653964368**;
- water: maximum false `0.0524983170`, minimum true `0.0818358827` → frozen threshold **0.0671670999**;
- soil: maximum false `0.2067529451`, minimum true `0.4617302231` → frozen threshold **0.3342415841**.

Thresholds were fixed at the midpoint of each discovery gap before any `4301+` outcome was opened. The frozen validation contract prohibits post-outcome threshold, seed, process-set, candidate or perturbation changes.

## 4. Fresh 35-case validation

Unused seeds `4301`–`4305` were then evaluated across all seven process sets (`n=35`) without modifying the method.

The predeclared support gate required complete denominator, exact process-set recovery ≥0.80, and sensitivity and specificity ≥0.80 for each of temperature, water and soil. **All gates passed.**

- counterfactual exact process-set recovery: **30/35 = 85.7%**;
- predecessor stable core: **23/35 = 65.7%**;
- AUC-selected winner: **25/35 = 71.4%**;
- exact counterfactual recovery when ecological fitted models disagreed: **15/18 = 83.3%**.

Counterfactual process classification:

- temperature: sensitivity **1.00**, specificity **0.933**;
- water: sensitivity **1.00**, specificity **0.800**;
- soil: sensitivity **1.00**, specificity **0.933**.

Paired exact-set outcomes against AUC were: both exact 24; counterfactual only exact 6; AUC only exact 1; both wrong 4.

Authoritative validation: workflow `34015684015`, artifact `9983844728`, digest `sha256:9a53abc38c45e93eb8696f1de7af5051776881c59ec5079f45b4ecc029068554`.

## 5. Independent 70-case replication

After the 35-case validation, the estimator and all three thresholds were kept unchanged. A separate pre-outcome replication contract froze new seeds `4401`–`4410` across the same seven process sets (`n=70`). No method change after the 35-case validation was allowed.

**All replication support gates passed.**

### Primary process-set result

- counterfactual exact process-set recovery: **65/70 = 92.9%**;
- AUC-selected winner: **56/70 = 80.0%**;
- predecessor stable core: **49/70 = 70.0%**.

Approximate 95% Wilson intervals for the descriptive exact-set proportions are:

- counterfactual: **0.843–0.969**;
- AUC winner: **0.692–0.877**;
- predecessor stable core: **0.585–0.795**.

These intervals are reporting summaries, not a replacement for the prospectively frozen support gate.

### Model-disagreement result

The canonical and robust ecological selectors chose different fitted models in **30/70** replication cases. The counterfactual process estimator nevertheless recovered the complete true process set in **27/30 = 90.0%** of these cases.

### Process-specific identification

Temperature (`40` true, `30` false):

- TP=40, FN=0, TN=28, FP=2;
- sensitivity **1.000**;
- specificity **0.933**.

Water (`40` true, `30` false):

- TP=40, FN=0, TN=28, FP=2;
- sensitivity **1.000**;
- specificity **0.933**.

Soil (`40` true, `30` false):

- TP=39, FN=1, TN=30, FP=0;
- sensitivity **0.975**;
- specificity **1.000**.

### Paired comparison with the AUC-selected process set

Across the same 70 cases:

- both exact: **51**;
- counterfactual only exact: **14**;
- AUC only exact: **5**;
- both wrong: **0**.

Thus every case was exactly recovered by at least one of the two procedures, while the counterfactual estimator uniquely recovered 14 cases versus 5 unique AUC recoveries. This paired comparison is descriptive; a universal-superiority claim was not the predeclared replication endpoint.

### By generating process set

Counterfactual exact recovery:

- `{T}`: **8/10**;
- `{W}`: **8/10**;
- `{S}`: **10/10**;
- `{T,W}`: **10/10**;
- `{T,S}`: **10/10**;
- `{W,S}`: **10/10**;
- `{T,W,S}`: **9/10**.

The five counterfactual errors were fully localized: two extra-water calls in `{T}`, two extra-temperature calls in `{W}`, and one missed-soil call in `{T,W,S}`.

Authoritative replication: workflow `34015900603`, artifact `9983940439`, digest `sha256:af72b78f64e5160dbc96a1147769e83a0b21b461d9b7111ca2e663e8f786d3eb`.

## 6. What has now been solved

The new positive Product-A result is no longer merely that model identity and process identity can differ.

Under a frozen declared process registry, Product A now provides a process-specific estimator with a direct counterfactual meaning:

> **How much ecological niche recovery becomes unattainable when every declared representation of this environmental process is forbidden?**

With independently varying temperature, water and soil truth, frozen thresholds generalized to fresh validation and a second independent replication. The 70-case replication recovered complete generating-process sets in 92.9% of cases and achieved sensitivity 0.975–1.000 and specificity 0.933–1.000 across the three independently varying processes.

## 7. Claim boundary

This result supports **process membership identification under the declared candidate/process registry and controlled truth**. It does not establish physiological causation, fundamental-niche necessity, or complete real-world proxy closure.

The earlier v2.6 exclusion certificate remains a distinct false-necessity safety result. The earlier v2.7.2 stable core remains a predecessor proof-of-concept and an observation-confounding result, but its `55/60` performance is no longer the primary process-identification headline.

The frozen fresh empirical v2.8.4 endpoint also remains unchanged: `empirical_confirmation_not_supported`, `not_promoted`, and ecological/AUC selector identity `108/108`. New controlled-truth success does not retroactively convert the empirical endpoint into support.
