# Nature logic consistency audit — Product A

Status: **reporting-only logic audit / no scientific endpoint change / no new Product-A experiment**.

## Audit question

Does the Nature-track manuscript consistently distinguish the two positive process-level estimands developed after the v2.3 false-necessity result?

## Finding

A real reporting conflation was identified and corrected.

The v2.4–v2.6 process-exclusion certificate and the v2.7.2 stable-process-core certificate are **not the same estimator** and answer different questions.

### Estimand A — exclusion-based process necessity

Question:

> Does an adequate ecological explanation survive when all declared information assigned to process `p` is excluded?

Implementation lineage:

- v2.3 showed that intersection among retained ecologically good models could create false necessity;
- v2.4 replaced intersection-as-necessity with explicit process knockouts;
- v2.4/v2.5 retained `unresolved/unavailable` states when calibration evidence was incomplete;
- v2.6 prospectively supplied adequate calibration support.

Frozen positive result at v2.6:

- complete process certificates: 9/9 validation taxa;
- complete boundary certificates: 9/9 validation taxa;
- false-required processes: 0 in every panel;
- possible-process recall: 1.0 in every panel;
- possible-process precision: 0.467 in every panel;
- boundary coverage improved under the frozen criterion, at the cost of wider intervals.

Interpretation:

> Falsification-first exclusion controlled false-required claims and retained generating processes under known truth, but the safe identified set remained broad.

This branch supports process-information necessity **relative to the frozen evidence/representation contract**. It does not establish physiological or causal necessity.

### Estimand B — consensus-first process stability

Question:

> Do canonical ecological recovery and perturbation-robust ecological recovery support the same process information even when they choose different fitted models?

Implementation:

`stable_process_core = canonical_process_set ∩ robust_process_set`

Hidden truth was opened only after selector choices and the consensus certificate were constructed.

Frozen positive result at v2.7.2 across 60 unused known-truth cases:

- stable-process-core precision: 0.9889;
- stable-process-core recall: 0.9833;
- stable-process-core F1: 0.9833;
- process-set consensus: 50/60;
- exact fitted-model consensus: 38/60;
- independent-process maximum absolute/relative numerical difference: 0.0;
- observation correction: 10/10 activation in observation-confounded cases and 0/50 elsewhere.

Interpretation:

> Process information can be stable and accurately aligned with generating truth even when exact fitted-model identity is not unique.

This branch supports **process-information stability**, not exclusion-based necessity.

## Correct integrated logic

The manuscript should use the following structure:

1. predictive adequacy does not imply process truth;
2. ecological-recovery filtering and retained-model agreement do not imply necessity;
3. necessity should be challenged by exclusion of declared process information, with broad/unresolved outcomes preserved when evidence does not identify a narrower claim;
4. independently, process information can be evaluated for stability across defensible ecological selectors, and this stability can exceed exact-model stability;
5. fresh empirical data may still fail to distinguish selection rules, as shown by the v2.8.4 108/108 selector collapse.

The synthesis is therefore:

> **Ecological identification is not one scalar score or one certificate. It decomposes ecological interpretation into at least predictive adequacy, exclusion-based necessity, process-information stability, and unresolved evidence.**

## Forbidden conflations

Do not state or imply:

- `falsification-first exclusion achieved precision 0.9889 and recall 0.9833`;
- `v2.7.2 proves the necessary-process set`;
- `stable_process_core` is the process-knockout necessary set;
- v2.6 and v2.7.2 are successive measurements of one identical estimator whose precision simply improved from 0.467 to 0.9889.

The `0.467` v2.6 value and the `0.9889` v2.7.2 value belong to different sets and different scientific questions and must not be compared as if they were the same precision measure.

## Correct claims

Allowed:

- exclusion-based certificates achieved zero false-required processes and complete true-process recall under the frozen known-truth criterion, while remaining broad;
- the separate consensus-first stable process core achieved precision 0.9889 and recall 0.9833 across 60 unused controlled-truth cases;
- process-set consensus exceeded exact-model consensus (50/60 versus 38/60);
- these complementary results motivate an ecological-identification framework that separates necessity from stability;
- the fresh v2.8.4 strict empirical advantage over AUC was tested and not supported, with candidate/predictor identity in 108/108 matched cells.

## Files aligned by this audit

- `docs/product_a_nature_ecology_evolution_article_draft.md`
- `docs/product_a_nature_ecology_evolution_cover_letter.md`
- `docs/product_a_nature_ecology_evolution_online_methods.md`
- `docs/product_a_nature_figure_legends.md`
- `docs/product_a_manuscript_spine.md`
- `docs/product_a_manuscript_closure_2026-08-31.md`
- `scripts/check_nature_manuscript_format.py`

Any future manuscript edit should preserve this estimand separation.