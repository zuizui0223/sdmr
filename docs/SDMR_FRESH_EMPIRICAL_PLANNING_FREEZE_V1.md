# SDMR fresh empirical planning freeze v1

Status: **planning frozen / fresh empirical answer-check unopened / source and taxon manifests not yet frozen**

## Decision now frozen

- exact fresh denominator: **50 vascular-plant taxa**
- primary ecological reconstruction metric: **balanced presence/background log score**
- primary flat comparator: **matched-learner flat predictive selector**
- learner/design panel: **penalized logistic + shallow3 HGB**
- learner disagreement: **unresolved, never averaged away**
- prediction safety guardrail: **answer-check AUC noninferiority, margin 0.02**
- EMP-A minimum mean paired reconstruction gain: **0.01**
- EMP-B 95% taxon-level bootstrap lower bound: **>= 0.00**
- EMP-C AUC noninferiority margin: **0.02**
- EMP-D minimum stable-process fraction: **0.80 (40/50 taxa)**
- EMP-E abstention-integrity violations: **0**
- EMP-F declared-denominator integrity: **required**

Fresh empirical outcomes remain unopened. Historical Product-A taxa remain excluded and Product-A remains closed.

## Why N = 50

The denominator is selected from the already-declared planning range 30-50 without reading any future empirical answer-check.

The planning alternative is deliberately modest: true taxon-level mean paired balanced-log-score gain = 0.02. The conservative planning SD is 0.05. The joint EMP-A/EMP-B planning calculation uses a two-sided 95% interval and requires both mean gain >= 0.01 and lower confidence bound >= 0.

Under that planning model:

- N=49 power = **0.79956**, below the frozen 0.80 target.
- N=50 power = **0.80743**, the first denominator in the allowed range that reaches the target.
- the N=50 critical observed mean gain for the interval gate is **0.01386**.

For EMP-D, if the true stable-process fraction is 0.90, observing at least 40/50 stable taxa has exact binomial power **0.99065**.

These calculations are sample-size planning only. The empirical EMP-B interval is frozen separately as a taxon-level 95% percentile bootstrap with 20,000 replicates and seed 20260926.

## Metric separation

AUC is deliberately retained only as a predictive safety guardrail. It is not the optimization target and it is not the primary ecological claim.

The primary scientific comparison is whether process-first SDMR improves sealed ecological niche reconstruction, measured by paired balanced presence/background log score, relative to the predeclared flat selector.

## What remains unopened

The following are still intentionally unresolved and must be fixed before final freeze:

1. cohort eligibility rule and exact 50-taxon identity manifest;
2. provider/source manifest and temporal window;
3. occurrence QC and accessible-area rule;
4. process-registry manifest;
5. outer split materialization and sealed answer-check receipt.

The next admissible step is deterministic manifest construction using only taxon/source metadata and coordinates permitted by the pre-freeze boundary. Environmental answer-check features and performance outcomes must remain unopened.
