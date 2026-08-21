# Product-A v2.7.1 development result — 2026-08-21

## Frozen result

The exact development workflow run `32455011154` completed successfully from implementation `e93e93cc97551df3fa32a8dfb17bc813dd2cdf39` on frozen ref `frozen/product-a-v2-7-1-evidence-balanced-e93e93cc`.

The authoritative summary artifact is `9437018612`, `product-a-v2-7-1-evidence-balanced-folds-development-summary`, with digest `sha256:6c12ff53f8a10887ed1c70f06b24d9c15300cb27db4736574d4b9ed0a595c7f5`.

Across the predeclared 72 taxon × part diagnostics:

- legacy v2.7 audit support was available in **39/72** cells;
- v2.7.1 evidence-balanced audit support was available in **70/72** cells (**97.2%**);
- **31** cells improved from unavailable to available;
- **0** cells regressed from available to unavailable;
- evidence-balanced partition construction itself was available in **70/72** cells.

No sealed environmental values were read and no candidate model was fitted in this diagnostic. The result is development-only and does not promote Product A or unblock Product B.

## Explicit structural abstentions

Two cells remain unavailable under the frozen row-count support constraints:

1. `Dryopteris filix-mas`, seed `2026081903`, part `0.20`;
2. `Quercus robur`, seed `2026081903`, part `0.30`.

For both cells, the 32 predeclared assignment attempts reached only `best_supported_folds=3/4`. Both cells were already unavailable under legacy v2.7, so they are support-boundary abstentions rather than regressions introduced by v2.7.1.

## Development stop rule

The current 2026-08-01 empirical snapshot and the six already-used split parts must not be used to retune v2.7.1 merely to convert 70/72 into 72/72. Doing so would optimize the method against evidence already inspected during development.

The two abstentions therefore remain explicit evidence of the structural support boundary. Any later method change must have an independently motivated reason and must be evaluated on unseen evidence rather than justified by these two cells.

## Next empirical lane

Independent empirical confirmation now requires genuinely fresh evidence: a new independently untouched occurrence snapshot created after this development endpoint and/or a predeclared taxon panel that excludes the current pilot taxa.

Before any fresh sealed outcome is opened, the repository must pin the new source identity, fingerprints, taxon panel, process registry, exact implementation SHA/ref, split design and decision contract. Until those fields exist, `configs/product_a_v2_7_1_fresh_empirical_source_gate.json` remains fail-closed with `execution_allowed=false`.

The ecological target remains realized environmental niche recovery and stability. Ordinary prediction metrics remain guardrails rather than the tuning target, and the four ecological recovery dimensions remain separate rather than being collapsed into a weighted score.
