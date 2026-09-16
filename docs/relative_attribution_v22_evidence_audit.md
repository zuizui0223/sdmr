# v22 consumed-evidence audit — 2026-09-15

The 74 unresolved pairs are explained by failure of the single-knockout
baseline adequacy gate, not missing fits. All 304 directional states across
152 pairs reproduce from saved model evidence with the inherited thresholds.
No model fitting or fresh validation was performed.

## Source

- Run: https://github.com/zuizui0223/sdmr/actions/runs/34921157441
- PR head: `dc842a03d34468eb3783fd1314da2df8a449a54f`
- Artifact suffix (PR merge execution identity): `e87d0f4a819664dfd02db01d9b91ce5e9fa7c7d2`
- Aggregate artifact: `10378537060`
- Aggregate ZIP SHA-256: `e1ae4ba5355634d31c22cfc0ca2f4636a2953540febe7077727ff4d26379e0e8`
- Frozen pair-manifest file SHA-256: `f69c3d88df53f09c2fb3c385ca5945ccd797e04287fc5c188e5263c33f7c1283`

## Replayed directional gates

| Mutually exclusive reason | Directions |
| --- | ---: |
| Prediction and ecological adequacy failed | 56 |
| Ecological adequacy alone failed | 29 |
| Prediction adequacy alone failed | 11 |
| Rank and density contribution not revealed | 86 |
| Density contribution alone not revealed | 48 |
| Rank contribution alone not revealed | 11 |
| Conditional contribution revealed | 63 |
| Total | 304 |

All 96 unresolved directions fail baseline adequacy. The 145 directions
without revealed contribution fail one or both contribution margins; absence
of revealed contribution does not establish ecological equivalence. In
particular, the historical `exchangeable` label is a classifier state, not a
demonstration that two processes are interchangeable.

The knockout baseline already removes the competing process. Its adequacy
failure therefore limits interpretation of the remaining process. This is a
measurement limitation to resolve in a separately declared successor design;
the consumed result does not justify weakening adequacy or tuning margins.

## Reproduction

Download all eight artifacts from the source run to an empty directory, then:

```sh
python -m sdmr.relative_attribution_v22_audit --input-dir inputs --output-dir audit
```

The audit rejects missing, extra, duplicate, or incorrectly mirrored evidence,
checks ModelSpec membership, and fails if any replayed directional state differs.
It emits a directional reason table and a JSON receipt with SHA-256 hashes of
all consumed input files. No generating truth is needed for these explanations.

Product A remains closed at `not_promoted`, Product B remains blocked, and this
audit does not authorize a new prospective or empirical endpoint.
