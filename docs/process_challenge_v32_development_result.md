# Process challenge v3.2 development-only result

Status: **development evidence only; not eligible for prospective performance claims**.

## Fixed denominator

- workflow run: `34015456711`
- branch head evaluated: `042e11a07ff94ee282df9592e2f3ca9de09a9ba7`
- six known-truth families
- seeds `13001–13010`
- 60 cases total
- Product A reopened: **no**
- answer-check occurrences used in fit: **no**
- proxy audit used ecological outcomes/truth: **no**
- proxy audit modified the process registry: **no**

Aggregate artifact:

- artifact ID: `9983793398`
- artifact digest: `sha256:9bc217f2b9fd0f1b1995e76e466befa05ff7f13f62400f5bff05e537544ee1d3`

## v3.2 development metrics

The underlying v3 challenge signal was unchanged from the earlier v3 development run:

- true-process challenge recall: **0.6615384615** (`86/130`)
- false-process challenge rate: **0.0235294118** (`4/170`)
- false-required rate: **0.0**

v3.2 then required a statistically shared process to have its own `contributory|required` challenge signal before that sharing could contest unique attribution.

Result:

- true-process unique-attribution recall: **0.6307692308** (`82/130`)
- false-process unique-attribution rate: **0.0058823529** (`1/170`)
- contested shared-information statuses: **7**
  - true-process contested: **4**
  - false-process contested: **3**
- final status counts:
  - `replaceable_under_evidence_contract`: **210**
  - `contributory_under_evidence_contract`: **83**
  - `required_by_evidence_contract`: **0**
  - `contested_shared_information`: **7**
  - `unresolved`: **0**

## Interpretation

v3.2 is materially less over-conservative than v3.1 while preserving its reduction in false unique attribution:

- v3.1 true unique-attribution recall: **0.30**
- v3.2 true unique-attribution recall: **0.6308**
- both left **1/170** false processes as unique attribution under this development denominator.

This does **not** establish prospective performance. The 13001–13010 denominator was used during method development and is retired from any future validation claim.

The result also shows why raw generating-process membership is not a sufficient final benchmark for this framework. A generating process may be present in the data-generating equation yet remain observationally replaceable under the declared predictor system. The next validation target should therefore distinguish:

1. generating-process membership;
2. oracle observational identifiability under the declared predictor/process closure;
3. learner challenge signal;
4. unique process attribution.

No threshold, family, seed or denominator in the closed Product-A study is changed by this development result.
