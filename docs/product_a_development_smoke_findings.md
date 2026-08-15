# Product-A development smoke findings

Status: **development-only / non-citable**. These numbers are used to diagnose the method and must not be substituted for the DOI-backed fixed-source Product-A result.

Source workflow run: `real-api-smoke` run `31857665614` (head `c3d019803961f2817eba8f53ef9146e72c93b4cf`).

The smoke benchmark intentionally used only the custom two-predictor universe `bio1,bio12`, six discovery species and two unseen validation species. It therefore cannot establish the final 43-variable method winner.

## Strategy pattern

Discovery-taxon mean sealed presence-rank (numerically presence-background AUC-equivalent):

- `all`: 0.581085
- `vif`: 0.581085
- `predictive`: 0.559602

Unseen-taxon mean sealed presence-rank:

- `all`: 0.685435
- `vif`: 0.685435
- `predictive`: 0.649609

With only two predictors, `all` and `vif` are effectively the same candidate set, so their tie is expected and is not evidence that VIF is generally optimal.

## Why local AUC/CBI is not the Product-A claim

Across the 18 discovery species × strategy rows, the correlation between model-pool inner spatial-CV `presence_rank` and the final outer sealed `presence_rank` was approximately **0.049**. In contrast, outer sealed `presence_rank` and the binned Boyce-style score were strongly aligned among finite pairs (**r ≈ 0.934**).

Two concrete failures of inner-CV performance to transfer were:

- `Poa annua`: mean inner presence-rank ≈ 0.625, mean outer sealed presence-rank ≈ 0.067 (gap ≈ -0.558).
- `Quercus robur`: mean inner presence-rank ≈ 0.710, mean outer sealed presence-rank ≈ 0.370 (gap ≈ -0.340).

The unseen-species rows also provide a first deliberately strong conventional baseline. Choosing the strategy **separately for each unseen species** by its own model-pool nested spatial-CV AUC-equivalent score gives:

- `Plantago major`: inner-CV tie resolves to `all`; outer sealed presence-rank = 0.840.
- `Taraxacum officinale`: inner-CV selects `predictive` (0.510 vs 0.430 for `all`), but outer sealed presence-rank falls to 0.459 versus 0.531 for `all`.
- mean outer sealed presence-rank of this local nested-AUC selection = **0.649609**.
- mean outer sealed presence-rank of the discovery-frozen `all` strategy = **0.685435**.

Thus even ordinary per-species nested spatial-CV tuning can choose a model that transfers worse to a genuinely outer sealed block. This is still only a two-predictor/two-validation-species diagnostic, not confirmatory evidence.

This development run therefore suggests that, at least in this small test, changing from AUC-like discrimination to Boyce-style evaluation does much less than changing the **information boundary / transfer test**. The final Product-A experiment is designed to test that suggestion rather than assume it.

## Confirmatory contrast now implemented

The fixed-source Product-A run compares four selectors:

1. `canonical_m_auc`: universe × strategy with the highest mean AUC-equivalent `presence_rank` on discovery taxa in the predeclared canonical 300-km M;
2. `canonical_m_boyce`: universe × strategy with the highest mean Boyce score on discovery taxa in that same M;
3. `sdmr_m_robust`: universe × strategy selected by within-species×M ranks aggregated equally across the 150/300/500-km M sensitivity set;
4. `local_nested_auc`: for each unseen species × M case, choose universe × strategy only from that species' **model-pool inner spatial CV AUC-equivalent score**, then open the same preassigned outer sealed rows used for every other selector.

The fourth comparator deliberately gives ordinary local tuning substantial flexibility. It can adapt to each unseen species and each M, while SDMR must transfer its discovery-frozen universe × strategy. None of the four selectors may use outer sealed scores to choose itself.

The output reports paired SDMR-minus-conventional transfer deltas, worst-M performance and repeated-run stability. No new weighted super-score is introduced.

If the selectors converge on the same method or SDMR has no repeated unseen-taxon/M advantage—especially versus `local_nested_auc`—the correct conclusion is that Product A adds no empirical selection advantage over conventional spatial-CV/AUC/Boyce-based selection for this corpus.
