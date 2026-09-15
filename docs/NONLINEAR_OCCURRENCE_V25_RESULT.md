# v25: precision improved, coverage screen failed

All 152 consumed pairs completed at frozen implementation
`788d38d5d9a07bfd1de9baef710b0bbe0b6a8bdc`. All 152 states replayed, and
all 1,064 source/target omission identities matched v23; every row was complete.

| Fixed development measure | v23 | v25 | Required |
| --- | ---: | ---: | ---: |
| Precision among specific calls | 3/4 | 5/5 | >=95% |
| Correct specificity among mixed pairs | 1/43 | 4/43 | >=20% |
| False inclusion among mixed pairs | 4/43 | 1/43 | <=5% |

v25 passes precision and false-inclusion screens but fails coverage:
4/43 = 9.30%, below 20%. Therefore `development_screen_passed=false` and
fresh validation remains unauthorized. Five correct calls alone are limited
development evidence, not a prospective precision claim.

## Full denominator

- A-specific: 5
- Joint-required: 14
- Full inadequate: 1
- Joint contribution not established: 87
- Joint supported, attribution uncertain: 45

Of the 87 joint-contribution failures, 79 pass rank but fail density, 3 pass
density but fail rank, and 5 fail both. This localizes the dominant gate.

The probability-versus-odds standardization identity was documented before
this outcome in commit `0858e7b`. A successor may investigate that calibration
issue with the v25 learner and unchanged decision margins. It must not simply
lower the density threshold or reclassify the v25 endpoint.

## Evidence

Receipts and all pair identities: `evidence/nonlinear_occurrence_v25_2026-09-15/`.
The verification receipt's purpose names the reused v23 verifier; its recorded
implementation commit and model-evidence hashes bind this v25 execution.
Full local archive: `../artifacts/sdmr-v25-nonlinear-occurrence-788d38d.zip`.
SHA-256: `45994c1e61c29e7aec73df59a7d8f32a1a8a1707f8b000f38b7010c57b11cdd6`.
This archive has not been uploaded to a GitHub Actions artifact store.

Product A remains closed and not promoted. Product B remains blocked.
