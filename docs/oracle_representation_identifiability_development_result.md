# Oracle representation-identifiability development result

Status: **development-only diagnostic; not prospective evidence**.

Product A remains closed. The development seeds `13001–13010` are already exposed and may not be reused for any future prospective performance claim.

## Question

The oracle asks a different question from the occurrence learner:

> Given the complete simulated true-suitability surface and the frozen predictor/process representation, does removing all declared information for process P irreversibly reduce reconstruction of the truth surface?

It does not use occurrence outcomes, v3 learner outputs, or generating-process membership to assign oracle statuses. Generating membership is opened only after oracle classification to audit the benchmark.

This is therefore a **truth-surface, representation-conditioned oracle**, not an occurrence-data oracle and not a causal or physiological truth claim.

## Frozen development contract

- config: `configs/oracle_process_identifiability_development.json`
- families: six frozen known-truth families
- seeds: `13001–13010`
- cases: 60
- process cells: 300
- spatial CV over complete environment-cell coordinates
- full predictor truth-reconstruction floor: R² `0.80`
- process loss margin: `0.02`
- required ceiling for process-free reconstruction: R² `0.0`
- all thresholds are development heuristics, not prospectively validated thresholds.

## Oracle result

Workflow run: `34022478135`

Aggregate artifact:
- ID: `9986006226`
- SHA-256: `59caa5482bd5ae3dc695e53a7dc7dcde0ffb980d061c7d155cefe8b6ce7584bb`

Across 300 process cells:

| quantity | result |
| --- | ---: |
| generating processes | 130 |
| generating oracle-identifiable | 130 / 130 = **1.000** |
| nongenerating processes | 170 |
| nongenerating oracle-identifiable | 0 / 170 = **0.000** |
| oracle contributory | 118 |
| oracle required | 12 |
| oracle replaceable | 170 |
| oracle contested | 0 |
| oracle unavailable | 0 |

Thus, within this simulator, predictor registry, oracle function class and development thresholds, generating-process membership and truth-surface representation identifiability happened to align perfectly.

This means the incomplete recovery of v3.2 cannot be explained solely by the generating processes being redundant in the frozen predictor representation.

## Occurrence identification gap

The fixed crosswalk uses two completed artifacts and performs no refitting:

1. v3.2 learner: run `34015456711`, artifact `9983793398`, SHA-256 `9bc217f2b9fd0f1b1995e76e466befa05ff7f13f62400f5bff05e537544ee1d3`;
2. truth-surface oracle: run `34022478135`, artifact `9986006226`, SHA-256 above.

Crosswalk workflow:
- run: `34022908116`
- artifact: `9986104467`
- SHA-256: `b8a34c3f2cfb8d5ed439cbb3c4dcc3cdede50eeff2cfdb2eabefbd9b0b581d9a`
- receipt: `ca5de840a5cb334c6dce3557f76f0573234a5d0bfb5bfbbf90e95d173d34cab8`

Overall:

| quantity | result |
| --- | ---: |
| oracle-identifiable process cells | 130 |
| v3.2 challenge recovered | 86 / 130 = **0.661538** |
| challenge identification gap | 44 / 130 = **0.338462** |
| unique attribution recovered | 82 / 130 = **0.630769** |
| unique identification gap | 48 / 130 = **0.369231** |
| challenge overcall among oracle-replaceable | 4 / 170 = **0.023529** |
| unique overattribution | 1 / 170 = **0.005882** |

### Gap by process

| process | oracle-identifiable | challenge recovered | gap |
| --- | ---: | ---: | ---: |
| temperature | 60 | 32 | **28** |
| water | 60 | 51 | **9** |
| soil | 10 | 3 | **7** |
| seasonality | 0 | 0 | 0; four challenge overcalls |
| noise | 0 | 0 | 0 |

The omitted-driver family is the hardest: 16 of its 30 oracle-identifiable process cells are missed by the occurrence challenge.

## Interpretation

The current hierarchy is:

```text
generating-process membership
        !=
truth-surface representation identifiability
        !=
identification from occurrence-only evidence
        !=
unique process attribution
```

In this development simulator the first two align, while a substantial gap remains between truth-surface identifiability and what the occurrence learner can identify.

The current v3 learner evaluates inner-fold process knockouts using held-out `presence_rank` and observation-corrected `ecological_presence_rank`. These are rank-based criteria. A knockout can preserve ordering of held-out occurrences versus background while substantially distorting the complete suitability surface.

This motivates the next **separate** development line: add a cross-fitted balanced presence/background density-ratio log score (a proper scoring criterion) rather than tuning the existing rank threshold against the exposed development results.

Any performance claim for that successor requires a completely new prospective denominator after its design is frozen.
