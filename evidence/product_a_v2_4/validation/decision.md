# Product-A v2.4 validation decision

## Final decision

`exclusion_certificate_unavailable`

This is the contract-abiding final result of the predeclared D1–D3 unseen known-truth validation. It is a valid negative/abstention outcome and does not authorize Product-A promotion or PR #1 merging to `main`.

## Immutable source

- source head: `b84742ef01e95e956c1f530a62b44f78352284a9`
- run: `32103035210`
- artifact: `9312286681`
- artifact digest: `sha256:3c8b23ffb1a78c4538076cfe1ca23f85060b3ef578f5be1d08cdd43604c80ee9`
- model-only validation workers: `54/54`
- validation truth used for fitting or calibration: `false`
- all process/boundary products frozen before truth opening: `true`

## Why the result is unavailable

Process transfer itself was complete: all nine validation taxa had complete process certificates, there were zero false required processes, and minimum possible-process recall was `1.0` in every panel. The process certificate was deliberately broad rather than sharp: mean possible-process precision was `0.4667`.

The boundary product did **not** satisfy the frozen completeness contract. Each panel had `21` validation response keys but only `18` complete discovery-calibrated intervals. The three missing keys were always the omitted-driver taxon's soil response:

- `soil / optimum`
- `soil / lower_limit`
- `soil / upper_limit`

The discovery calibration set contained no soil calibration radius. Because validation truth was already reserved to answer-check and the contract requires discovery-only calibration, those three intervals cannot be rescued or calibrated after seeing the validation outcome. Missing calibration therefore remains explicit evidence unavailability.

| panel | complete calibrated intervals | response keys | complete-adequate coverage | v2.4 reported coverage* |
|---|---:|---:|---:|---:|
| D1 | 18 | 21 | 0.3333 | 0.4762 |
| D2 | 18 | 21 | 0.3333 | 0.7143 |
| D3 | 18 | 21 | 0.3333 | 0.6667 |

`*` Coverage includes unavailable keys as uncovered and is descriptive only; the product is not admissible because completeness failed.

## Decision-rule correction

The first validation run (`32102526506`, artifact `9312119021`) incorrectly reported `exclusion_certificate_supported`. That was an implementation error in the decision availability check, not a scientific result: it checked raw-product completeness but failed to require complete **calibrated** v2.4 intervals.

The implementation was corrected to enforce the already-frozen rule

`n_complete_calibrated_intervals == n_calibrated_response_keys`

for every panel. No scientific threshold, seed, taxon, M, process alias, fitting rule, calibration source, or candidate set was changed. The corrected run above reproduced the same evidence and correctly returned `exclusion_certificate_unavailable`.

## Scientific consequence

v2.4 supports the value of falsification-first process exclusion as a conservative process diagnostic, but the complete v2.4 process+boundary certificate is not validated. Seeds 401–423 are now opened and cannot serve as fresh confirmation for a successor method.

Any successor must be separately predeclared on new unseen seeds and must guarantee, before validation opening, that the discovery calibration support covers every response process that its validation contract may require. The current validation data cannot be used to manufacture the missing soil calibration.
