# Product-A v2.4 sealed-blind discovery freeze

## Source

- workflow run: `32096477308`
- source head: `3c222249109ac2c15f6258ebc79bb1c957dd42a4`
- all three panel jobs: success
- discovery generating truth read: `false`
- validation taxa simulated or read: `false`
- validation truth read: `false`
- real empirical data read: `false`
- old external-sealed outcomes read: `false`

The full candidate ledgers and fold metrics remain in the immutable GitHub Actions artifacts listed below. The repository file records their identities, digests and frozen discovery products; it does not reopen or reinterpret any validation result.

## Panel results

| panel | discovery seeds | reserved unopened validation seeds | complete knockout routes / 40 | admitted knockout routes / 40 | canonical AUC point | complete-adequate base set | v2.3 Pareto base set | artifact |
|---|---|---|---:|---:|---|---|---|---|
| D1 | 371, 381, 391 | 401, 411, 421 | 33 | 20 | `niche_forward\|logit_l2_C1_degree2` | 4 candidates | 3 candidates | `9310256239`, `sha256:aace53635728c8a2edf4a92de8136e127a21d9552679cad0f30048195e25e7db` |
| D2 | 372, 382, 392 | 402, 412, 422 | 30 | 30 | `all\|logit_l2_C1_degree2` | 6 candidates | 2 candidates | `9310224903`, `sha256:b47f660cab44e2c8e7a29131c163447a39d7aa6332a4c83a3ea0f7aebdd0936b` |
| D3 | 373, 383, 393 | 403, 413, 423 | 30 | 29 | `predictive_forward\|logit_l2_C1_degree2` | 6 candidates | 2 candidates | `9310181352`, `sha256:5f325c22cffd3048ba99aecf24bf94dc6e95c9264aae6953e7ae0a9b473dc85e` |

## Frozen process-exclusion witnesses

Every process has at least one complete knockout candidate that passed the absolute discovery prediction gate in every panel.

| panel | noise | seasonality | soil | temperature | water |
|---|---:|---:|---:|---:|---:|
| D1 admitted routes | 4 | 4 | 4 | 5 | 3 |
| D2 admitted routes | 6 | 6 | 6 | 6 | 6 |
| D3 admitted routes | 6 | 5 | 6 | 6 | 6 |

This means discovery evidence did **not** establish any process as `required_by_frozen_discovery_contract`. It only freezes candidate exclusion witnesses. Biological necessity is not yet refuted for a validation taxon until at least one frozen witness transfers successfully across every required M; failed or incomplete transfer remains `unresolved`.

## Base products

### D1

- canonical AUC point: `niche_forward|logit_l2_C1_degree2`
- complete adequate: `all|logit_l2_C1_degree2`, `niche_forward|logit_l2_C1_degree2`, `predictive_forward|logit_l2_C1_degree2`, `vif|logit_l2_C1_degree2`
- v2.3 ecological Pareto comparator: `all|logit_l2_C1_degree2`, `niche_forward|logit_l2_C1_degree2`, `predictive_forward|logit_l2_C1_degree2`

### D2

- canonical AUC point: `all|logit_l2_C1_degree2`
- complete adequate: both frozen L2 settings for `all`, `predictive_forward` and `vif`
- v2.3 ecological Pareto comparator: `all|logit_l2_C1_degree2`, `predictive_forward|logit_l2_C1_degree2`

### D3

- canonical AUC point: `predictive_forward|logit_l2_C1_degree2`
- complete adequate: both frozen L2 settings for `all`, `predictive_forward` and `vif`
- v2.3 ecological Pareto comparator: `all|logit_l2_C1_degree2`, `predictive_forward|logit_l2_C1_degree2`

## Next information barrier

The next stage may use only these frozen candidate sets and artifacts. It must:

1. refit every retained base and admitted knockout procedure under every required M and five frozen spatial refits;
2. freeze raw discovery response envelopes before opening discovery generating truth;
3. derive interval-expansion radii from discovery truth only;
4. freeze those radii before any reserved validation taxon is simulated or read.

No discovery threshold, process alias, procedure, M, fold, seed or candidate denominator may be changed after this freeze. PR #1 remains blocked from `main`.
