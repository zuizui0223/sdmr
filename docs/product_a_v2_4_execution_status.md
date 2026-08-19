# Product-A v2.4 execution status

## Final status

Product-A v2.4 completed its predeclared unseen known-truth development path with the final decision:

> **`exclusion_certificate_unavailable`**

This is a valid negative/abstention outcome. No v2.4 method is promoted to empirical confirmation and PR #1 remains blocked from `main`.

## Frozen discovery

The sealed-blind knockout discovery stage is immutable.

- source run: `32096477308`
- source head: `3c222249109ac2c15f6258ebc79bb1c957dd42a4`
- panels D1–D3: all successful
- discovery generating truth read during selection: no
- validation taxa or validation truth read: no
- complete knockout routes: D1 `33/40`, D2 `30/40`, D3 `30/40`
- admitted knockout routes: D1 `20/40`, D2 `30/40`, D3 `29/40`
- every predeclared process has at least one frozen exclusion witness in every panel

The exact candidate sets, artifact IDs and digests are recorded in `evidence/product_a_v2_4/discovery/freeze.json`.

## Frozen discovery-only refits and calibration

The stage-2 source run `32098266084` produced all 54 expected model-only discovery worker artifacts from head `72ee499f808fb8eefb054bfaac95c5f086aacdb1`.

Across the frozen discovery products:

- expected members: `5130`
- successful members: `5130`
- raw discovery intervals: `216/216` complete
- discovery calibration keys: `18/18` complete
- validation truth used for calibration: no

The frozen calibration artifact is:

- run: `32099494627`
- artifact: `9311087568`
- digest: `sha256:2fad05bc40af18292ff1fb24c2580ef5c603338da302f168cb130299a126363b`

## Frozen validation

The reserved validation panels were opened only after 54 model-only validation workers and all pretruth process/boundary products were frozen.

- corrected source run: `32103035210`
- source head: `b84742ef01e95e956c1f530a62b44f78352284a9`
- artifact: `9312286681`
- digest: `sha256:3c8b23ffb1a78c4538076cfe1ca23f85060b3ef578f5be1d08cdd43604c80ee9`
- model-only validation workers: `54/54`
- validation truth used for fitting: no
- validation truth used for calibration: no
- all process and boundary products frozen before truth opening: yes

### Process result

All nine validation taxa had complete process certificates.

- false required processes: `0`
- minimum possible-process recall: `1.0` in every panel
- mean possible-process precision: `0.4667`

The exclusion certificate therefore behaved conservatively: it avoided false claims of biological necessity but retained a broad possible-process set.

### Boundary result and stopping reason

Each panel contained `21` validation response keys, but only `18` had complete discovery-calibrated intervals. The unavailable keys are the omitted-driver taxon's `soil` optimum, lower limit and upper limit in every panel.

The discovery calibration set contains no soil calibration radius. Under the predeclared rule that calibration is discovery-only and every expected v2.4 interval must be complete, these validation intervals cannot be filled after opening the validation evidence.

The correct final decision is therefore `exclusion_certificate_unavailable`.

## Corrected availability rule

The first validation aggregation run (`32102526506`) reported `exclusion_certificate_supported` because its implementation checked raw boundary-product completeness but did not enforce complete calibrated-v2.4 response keys. This contradicted the already-frozen contract.

The decision implementation now requires, for every panel:

`n_complete_calibrated_intervals == n_calibrated_response_keys`.

No scientific threshold, taxon, seed, process alias, M, procedure, candidate set or calibration source changed. The corrected run reproduced the evidence and returned the contract-abiding unavailable state.

The immutable final record is in:

- `evidence/product_a_v2_4/validation/decision.json`
- `evidence/product_a_v2_4/validation/decision.md`

## Next-method boundary

Seeds 401–423 are opened and cannot be reused as fresh validation. A successor line must be separately predeclared on unused seeds and must establish complete discovery-side calibration support for every response process allowed by its validation contract before any new validation truth is opened.

PR #1 remains blocked from `main`.
