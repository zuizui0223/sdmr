# SDMR fresh empirical v5 — sealed post-terminal characterization

**Status:** archived supplementary characterization; fresh-v5 empirical promotion is **failed and closed**.

## Temporal / decision boundary

- The frozen model-pool-only terminal decision was committed on **2026-10-07**, before sealed scores became available.
- At that point, EMP-D had already failed: **16 stable-sharp process cells / 300 = 0.053333**, versus the predeclared **0.80** requirement.
- The model-pool SDMR primary route was unavailable for **40/50** taxa.
- A strictly conjunctive EMP-A–F promotion was therefore impossible before opening any sealed answer-check.
- A superseded run **37642883197** and the authoritative re-wired one-shot run **37643074571** later completed. Their **result JSON files and 50-taxon score CSV files are byte-identical**. The source artifact hashes are recorded in the receipt.

This archive does not reverse the terminal decision, introduce a new promotion route, or authorize post-outcome model changes.

## Sealed predictive results (50-taxon frozen denominator)

| Outcome | Value | Interpretation |
|---|---:|---|
| Primary SDMR versus matched-learner flat selector: mean paired balanced-log-score gain | **−0.00385763** | Not superior; negative on the declared denominator |
| Primary paired taxon bootstrap 95% interval | **[−0.01116851, 0.00288823]** | Contains zero |
| Primary evaluable taxa | **10 / 50** | Other 40 count as zero gain by frozen scoring rule, not as biological negatives |
| AUC noninferiority | **not established** | EMP-C requires all 50 evaluable; aggregate paired AUC is null |
| Stable-sharp process cells | **16 / 300 = 5.33%** | EMP-D fails; this was known before answer-check opening |
| Abstention-integrity violations | **0** | EMP-E passes |
| Declared taxon denominator | **50 / 50** | EMP-F passes |

**Promotion vector:** EMP-A fail, EMP-B fail, EMP-C fail, EMP-D fail, EMP-E pass, EMP-F pass. Overall **fail**.

### Capacity-control comparison

The pre-frozen full-46 flat HGB capacity control is *not* a promotion gate:

- Mean SDMR-minus-full46 balanced log-score gain: **+0.00406973** on the declared 50-taxon denominator.
- Paired bootstrap 95% interval: **[−0.00056440, +0.00995594]**; crosses zero.
- Evaluable taxa **10/50**; no supported claim that process-aware filtering beats simply fitting the complete 46-variable HGB.

Both sealed executions report **no model refit and no post-opening reselection**.

## Scientific interpretation and limits

Known-truth M5 shows what the procedure can distinguish under controlled truth. The frozen real-plant v5 experiment demonstrates a separate result: **availability of environmental features is not equivalent to identifiable ecological process information**.

The bottleneck is not the inability to sample rasters: 50/50 taxa passed the prior 46-layer complete-case gate. It is the frozen evidence and cross-learner stability requirement, with only 10/50 taxa authorizing the primary process-first route and 16/300 cells having a stable sharp state.

Do **not** reinterpret unavailable/unresolved process cells as absence of ecological processes. Do **not** claim broad empirical superiority, retrofit EMP-D, remove taxa, delete predictors, change the learner panel, or treat this supplementary sealed result as a new confirmatory experiment.

## Immutable evidence

- [Authoritative sealed run](https://github.com/zuizui0223/sdmr/actions/runs/37643074571) and [artifact](https://github.com/zuizui0223/sdmr/actions/runs/37643074571/artifacts/11501124012)
- [Superseded run](https://github.com/zuizui0223/sdmr/actions/runs/37642883197) and [artifact](https://github.com/zuizui0223/sdmr/actions/runs/37642883197/artifacts/11499467126)
- `results/sdmr_fresh_empirical_v5_sealed_promotion_result.json`: exact authoritative result bytes, SHA-256 `67452d2147c890b3ea47ca33ae15ed39b32d637904ea06a32adaf3ab100219c6`
- The frozen taxon-level score CSV is retained in both workflow artifacts; its SHA-256 is `cce79d443f133bb1d8f9a943be0f8e3573ae93a9b71c55230adecd61283b1ce1`.
- `configs/sdmr_fresh_empirical_v5_sealed_postterminal_receipt.json`: run provenance and promotion prohibition.
- `results/sdmr_fresh_empirical_v5_model_pool_terminal_decision.json`: original pre-answer-check failure, which remains authoritative.

Next scientific task: investigate the gap between known-truth recovery and real-world process-identifiability in a **new, independently specified development/validation route**, not as retroactive rescue of v5.
