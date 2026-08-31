# Product-A v2.8.4 sealed implementation boundary

This implementation remains non-dispatchable. The reusable workflow is callable only through a separate caller and refuses to proceed unless that caller originates from an exact manually dispatched `main` authorization commit whose canonical authorization receipt, caller workflow hash, reusable workflow hash, implementation surface hashes, and three reviewed presealed receipt identities all match.

The implementation does not change Product-A v2.8.3 scientific semantics. It inherits the same 0.25 sealed fraction, three split seeds, 150/300/500 km M sensitivity set, 12-taxon denominator, model random state 0, selection-process NumPy seed 0, prediction guardrail -0.01, ecological two-of-three requirements, process two-thirds requirement, and fixed primary denominator of three.

Each sealed-part runner must reproduce the frozen scientific environment before downloading the v2.8.3 part artifact that contains sealed raw rows. Receipt and artifact metadata may be checked before this point because they contain provenance rather than sealed ecological values. The part then verifies exactly 15 receipt-pinned inputs: one v2.8.3 model-pool part, one v2.8.3 structural part, one v2.8.4 pretruth artifact, and 12 v2.8.4 final-fit artifacts.

Immediately before entering the inherited sealed audit core, the runtime writes a state receipt with `sealed_read_entered=true` and `retry_without_new_explicit_contract_allowed=false`. Therefore a failure after that boundary is not automatically retryable. Scientific null, negative, or unavailable outcomes are never retry targets.

Three successful finalized sealed parts are required before the unchanged v2.8.3 fixed-denominator aggregate decision is applied. Scientific promotion and Product-B unblocking remain false throughout this implementation and require separate decisions after a valid Product-A terminal result.

## Final no-value-read recovery implementation (2026-08-31)

The second sealed workflow dispatch reached the conservative `sealed_read_entered=true` marker, but all three parts failed on the first `rasterio` import before any raster dataset was opened or any environmental value was extracted. That failure is technical and is not a scientific null, adverse result, or terminal unavailability decision.

The final recovery implementation adds only the truth-blind, hash-locked geospatial environment frozen from run `33359562108`. Each sealed-part runner must install that lock and import/version-check `rasterio` before downloading any input artifact. The resulting geo receipt is validated again before the sealed-read marker and its digest is written into the sealed state.

This implementation does not authorize execution. A separate frozen authorization must prove that the next run is exactly the third total workflow dispatch, must forbid a fourth dispatch and any same-run job retry, and must retain every scientific identity and receipt. Product B and scientific promotion remain blocked.
