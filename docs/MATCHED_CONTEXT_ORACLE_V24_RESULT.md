# v24: a matched-context occurrence-to-oracle gap

Frozen implementation: `ebaa51f` (local consumed diagnostic).
All 152 pairs and all 1,064 target/source omission rows completed. The omission
identity set equals v23's exactly, and all 152 oracle states reproduce from
saved scores. Pair selection and classification did not use generating labels.

## Result

- All 43 mixed generating/nongenerating pairs: oracle A-specific, selecting
  the generating process under the fixed manifest order.
- All 109 generating/generating pairs: oracle joint-required.
- Oracle-unavailable pairs: 0.

Every oracle full route passed the declared mean R2 floor .80. These are
representation-conditioned truth-surface results under the fixed regressor
and heuristic bands, not causal identifiability or prospective performance.

| v23 occurrence state | Oracle specific | Oracle joint-required |
| --- | ---: | ---: |
| A-specific | 1 | 1 |
| B-specific | 1 | 1 |
| Full inadequate | 5 | 10 |
| Joint contribution not established | 29 | 58 |
| Joint required | 3 | 7 |
| Joint attribution uncertain | 4 | 32 |
| Total | 43 | 109 |

The 43/43 correct oracle mixed-pair decisions contrast with 1/43 correct
specific occurrence decisions in v23. The four-route structure can distinguish
these pairs with privileged truth-surface targets; the observed v23 failure is
not evidence that the declared representation intrinsically lacks the signal.

This contrast changes both target data and model family. It does not identify
which of occurrence sampling, observation correction, estimator capacity or
score choice caused the gap. It does not authorize fresh validation or overturn
v23's failed advancement screen.

## Next development experiment

Hold the v23 occurrence data, pair membership, spatial splits, observation
correction, four routes, margins and classifier fixed. Change only the fitted
learner to a separately frozen nonlinear probability model, and apply the same
development screen. This tests one plausible contributor to the gap while
continuing to use occurrence data alone. It must be specified before evaluation;
the oracle never supplies training targets to that candidate.

## Evidence

Committed receipts and pair states: `evidence/matched_context_oracle_v24_2026-09-15/`.
Full local archive: `../artifacts/sdmr-v24-matched-oracle-ebaa51f.zip`.
Archive SHA-256: `8b810aff2979ef39e94a1e1f1c667289a7713e86901e9d3f3c02df41f1c9f666`.
Raw evidence hashes are in the verification receipt. The archive is local and
has not been uploaded as a GitHub Actions artifact.

Reproduce state verification without fitting with `python -m
sdmr.matched_context_oracle_v24 --pair-manifest PATH --output-dir RUN_DIR
--verify-only`.
