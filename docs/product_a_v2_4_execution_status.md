# Product-A v2.4 execution status

## Frozen discovery

The sealed-blind knockout discovery stage is complete and immutable.

- source run: `32096477308`
- source head: `3c222249109ac2c15f6258ebc79bb1c957dd42a4`
- panels D1–D3: all successful
- discovery generating truth read: no
- validation taxa or validation truth read: no
- complete knockout routes: D1 `33/40`, D2 `30/40`, D3 `30/40`
- admitted knockout routes: D1 `20/40`, D2 `30/40`, D3 `29/40`
- every predeclared process has at least one frozen exclusion witness in every panel

The exact candidate sets, artifact IDs and digests are recorded in `evidence/product_a_v2_4/discovery/freeze.json`.

## Frozen model-only refits

The stage-2 source run `32098266084` produced all 54 expected model-only worker artifacts from head `72ee499f808fb8eefb054bfaac95c5f086aacdb1`.

Each worker used only a frozen discovery candidate group and generated:

- one full fit per candidate × M;
- five frozen spatial refits per candidate × M;
- ecological response estimates on the model-only environment;
- no generating truth, validation taxon, validation truth, empirical data or old external-sealed outcome.

The source workflow's superseded aggregation job failed because its truth-audit merge declared one truth row per product envelope as `one_to_one`. The 54 worker jobs themselves were successful and their artifacts remain immutable. The source code now uses the correct `many_to_one` cardinality; no scientific threshold, candidate, seed, process alias, M, fold or response quantity changed.

## Current gate

The registered Product-A v2.4 workflow now reconstructs raw discovery envelopes from those exact 54 artifacts, opens discovery truth only after all raw envelopes are frozen, and derives the predeclared maximum-miss calibration radii. Reserved validation seeds 401–423 remain unopened.

PR #1 remains blocked from `main`.
