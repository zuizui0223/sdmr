# biodiv-data-core

`biodiv-data-core` is a neutral biodiversity-data substrate for ecological repositories that repeatedly need reproducible occurrence QA, spatial partitioning, and source provenance.

Current public contracts:

- occurrence records and explicit admission/rejection decisions;
- deterministic coordinate deduplication;
- deterministic geographic block assignment;
- whole-block model/holdout assignment;
- occurrence manifests and SHA-256 fingerprints;
- raster provenance manifests.

## Scientific ownership boundary

This package does **not** own research-specific inference. It intentionally excludes:

- SDMR niche-tuning, predictor selection, universal-driver inference, or sealed-score semantics;
- ACSP robust-support candidate-patch rules;
- island exact-island composition models and pollination-regime inference;
- FCP flower-colour evidence classification and comparative niche models;
- hotarubukuro flower-colour, Bombus-boundary, isolation, or spatial-null models.

Those remain in their scientific repositories.

## Install from this staging directory

```bash
python -m pip install ./packages/biodiv-data-core
```

For development:

```bash
python -m pip install -e './packages/biodiv-data-core[dev]'
pytest packages/biodiv-data-core/tests
```

## Migration rule

Move only functions whose scientific meaning is invariant across at least two repositories. A function that encodes a paper-specific threshold, target definition, predictor universe, sampling frame, or inferential gate stays local.

This directory is self-contained so it can later be extracted unchanged into a dedicated `biodiv-data-core` repository.
