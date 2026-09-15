# v23 consumed development: advancement screen failed

All six families and all 152 fixed pairs completed locally at implementation
`511e8478cfc6d523cf35761e926f0b55af14578d`. Saved model evidence reproduced
all 152 pair states. Runtime and config fingerprints are in
`evidence/coalition_attribution_v23_2026-09-15/`.

## Predeclared screen

| Measure | Observed | Required | Result |
| --- | ---: | ---: | --- |
| Precision among specific calls | 3/4 = 75% | >=95% | Fail |
| Correct specific attribution among mixed-truth pairs | 1/43 = 2.33% | >=20% | Fail |
| False inclusion among mixed-truth pairs | 4/43 = 9.30% | <=5% | Fail |

The four specific calls include two true-vs-true pairs, one correctly resolved
water-vs-seasonality pair, and one incorrectly resolved temperature-vs-seasonality
pair in the observation-confounded family. False inclusion includes that wrong
specific call and three joint-required calls including a nongenerating process.

## All-pair denominator

| State | Pairs |
| --- | ---: |
| Joint contribution not established | 87 |
| Joint supported, attribution uncertain | 36 |
| Full model inadequate | 15 |
| Joint required | 10 |
| A specific | 2 |
| B specific | 2 |
| Total | 152 |

Of the 74 formerly unresolved v22 pairs, 15 fail full-model adequacy in v23,
39 lack established joint contribution, 16 retain uncertain attribution,
3 become joint-required and 1 becomes A-specific. This is a changed estimand,
not a rescue of the old endpoint. Reducing inadequacy alone did not supply
accurate singleton attribution.

## Claim boundary and next step

`development_screen_passed = false`. No fresh simulation or empirical endpoint
is authorized by this result. Thresholds, margins, targets and seeds were not
retuned after the outcome. Product A remains not promoted and Product B blocked.

The result diagnoses limited discrimination by these occurrence-based model
contrasts. It does not prove intrinsic non-identifiability: the earlier
representation-conditioned truth-surface oracle in PR #200 recovered generating
processes on a different consumed denominator. The next question is where the
matched-context occurrence-to-truth-surface gap arises, not whether a looser
threshold would yield more calls.

## Evidence and reproduction

The committed evidence includes the development decision, execution receipt,
all 152 state identities and hashes for every family score/result file.
The full saved evidence archive is available locally as
`../artifacts/sdmr-v23-consumed-development-511e847.zip` with SHA-256
`d209fb0ad896513feebea5de4e5abb63fac7a0d0f4138afbc9a0bfc9d441f018`.
The archive retains all raw model scores; it has not been uploaded to a GitHub
Actions artifact store. This was a local consumed-development run, not the CI
test run and not prospective evidence.

Run `python -m sdmr.coalition_attribution_v23_verification --pair-manifest PATH
--output-dir EXTRACTED_RUN_DIR` to verify saved states without fitting.
Use the exact source manifest hash and runtime versions recorded in the receipt.
