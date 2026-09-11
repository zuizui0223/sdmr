# Alignment transport v15 consumed-development endpoint

## Status

Development-only. Consumed seeds 15001–15010 only. Not eligible for prospective performance claims.

Authoritative family run: GitHub Actions `34549319931` on scientific head `328cff031976083a9fe9948d831b0fa6a1957df9`.

All six family jobs completed successfully. The original aggregate failed only because a header-only zero-focus family promoted the concatenated `seed` dtype to object and `DataFrame.equals()` treated the value-identical manifest as unequal. The family artifacts themselves contained the complete frozen 9-cell denominator. A type-stable aggregate repair was added without modifying scientific calculations or thresholds.

## Frozen cell results

| family | seed | process | evaluable source-target pairs | reproduced pairs | v15 class |
|---|---:|---|---:|---:|---|
| asymmetric | 15003 | water | 56 | 24 | heterogeneous |
| gaussian | 15001 | water | 56 | 21 | heterogeneous |
| gaussian | 15004 | temperature | 56 | 2 | heterogeneous |
| interaction | 15008 | water | 56 | 15 | heterogeneous |
| observation_confounded | 15004 | temperature | 51 | 13 | heterogeneous |
| observation_confounded | 15005 | water | 50 | 18 | heterogeneous |
| soft_threshold | 15002 | water | 56 | 26 | heterogeneous |
| soft_threshold | 15007 | water | 52 | 10 | heterogeneous |
| soft_threshold | 15009 | water | 46 | 8 | heterogeneous |

Endpoint: **9/9 heterogeneous; 0 transported; 0 local-alignment-only; 0 insufficient.**

## Mechanistic readout

The heterogeneity is strongly target-context structured rather than source-map structured. Across the 9 cells, source-block reproduction rates are comparatively narrow, while target-block rates frequently span 0 to 1. For 8/9 cells, target-block standard deviation of reproduction exceeds source-block standard deviation; in many cells the seven alternative source maps agree unanimously within a target block.

This means the v8 state transition is not a globally transportable property of one learned conditional map, but neither is it purely local to the map-training environment. The same intervention family can succeed or fail depending mainly on the held-out evaluation environment.

## Consequence

Do not promote a global process status from v15. The next development target is **context-indexed process attribution**: identify the environmental contexts in which a process is distinguishable, replaceable, or unresolved, and explicitly report context dependence instead of forcing one global label.

Fresh known-truth and fresh empirical validation remain unauthorized.
