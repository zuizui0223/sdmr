# v5: uncertainty and replaceability are different bottlenecks

**Post-outcome development diagnosis only. No new run, tuning, prospective
claim or Product A reopening.** This is a readout of the original 60 cases and
300 process cells, not a change to their statuses.

Source: PR #202 head `f3b95c7aa5ea0f559b54dc797ec46fda141582c8`, development
run `34037107229`, artifact `9990648093`. The pinned ZIP and all original
settings are unchanged. The source interval classifier is
`src/sdmr/interval_evidence_process_challenge.py` at that head.

## Process-specific recovery

The overall true challenge recall of 49/130 (37.69%) conceals different
process-level limits. Counts below are raw process-challenge statuses; in this
particular artifact, the final attribution statuses coincide.

| True generating process | Cells | Contributory | Replaceable | Unresolved | Required | Challenge recall |
|---|---:|---:|---:|---:|---:|---:|
| temperature | 60 | 14 | 23 | 23 | 0 | 23.33% |
| water | 60 | 32 | 8 | 20 | 0 | 53.33% |
| soil (omitted_driver family only) | 10 | 3 | 7 | 0 | 0 | 30.00% |
| Total | 130 | 49 | 38 | 43 | 0 | 37.69% |

The seven missed true soil cells are **all replaceable**, not unresolved.
For these observations and this contract, a process-exclusion route survives
with established noninferiority. This is not evidence that soil was absent from
the generating mechanism; soil is explicitly a true driver in that family.
Nor does it prove structural nonidentifiability for all future data or models.

Among false-process cells, noise is replaceable in all 60; seasonality is
replaceable in 48 and unresolved in 12; soil outside omitted_driver is
replaceable in 49 and unresolved in 1. All 13 raw v4 false contributory cells
are now unresolved (12 seasonality and 1 soil), not proven absent processes.

Case-level coverage is also different from process-cell recall: all true
processes are challenged in 10/60 cases, some but not all in 28/60, and none in
22/60. The six families and all ten seeds remain in these denominators.

## What the abstentions contain

All 56 unresolved cells have reported complete routes. Their exported counters
separate into two situations:

| Truth | At least one inferior viable route AND at least one indeterminate viable route | All viable routes indeterminate | Total unresolved |
|---|---:|---:|---:|
| True process | 41 | 2 | 43 |
| False process | 2 | 11 | 13 |

Thus 41/43 true abstentions already contain some route-level inferiority
evidence. The process claim is withheld because *other viable alternatives*
remain indeterminate. Thirty true cells have exactly six adequate routes,
three inferior and three indeterminate. This is a mixed-evidence bottleneck,
not missing jobs, and not absence of any challenge evidence.

The aggregate does not identify which model labels or which of the four
rank/density metrics supply these states. In particular, the 3-versus-3 pattern
must NOT be attributed to linear versus quadratic models without route-level
evidence. No such route/fold table or interval endpoints are in this archive.

## Proposition: nested refinement preserves decided raw challenge states

This is a conditional statement about the existing rule, **not** a new
scientific threshold, an intervention, or a performance forecast.

Fix the cases, processes, expected route labels, baseline comparisons,
completeness and absolute-adequacy decisions. For each route and relative
metric, let its complete uncertainty band be I = [L, U]. Suppose a hypothetical
refinement replaces it by a nonempty subinterval I' contained in I. All margins,
SEM settings and comparison conventions remain fixed. No such refinement is
performed by this diagnostic.

For the code's fixed comparator t = -margin - 1e-12:

- noninferior means L >= t;
- inferior means U < t;
- otherwise the complete band is indeterminate.

**Proof.** A contained interval has L' >= L and U' <= U. Therefore a
noninferior metric remains noninferior and an inferior metric remains inferior.
A route with all required metrics noninferior retains that property; a route
with at least one inferior metric retains an inferior metric. With the viable
route set fixed, a replaceable process retains its noninferior witness, a
contributory process retains inferiority in every viable route, and a required
process retains its empty viable route set. Only previously unresolved raw
process statuses can change. This proves the claimed preservation.

Consequently, for a fixed truth stratum with D already challenged cells,
U unresolved cells and N total cells, any such refinement obeys

    D <= refined raw challenge count <= D + U.

The upper value is a counting bound, not a guarantee that all unresolved cells
can jointly resolve to contributory. The original aggregate lacks the interval
endpoints and joint constraints needed to assess attainability.

| True process | Current challenged | Unresolved | Conditional upper count | Conditional upper recall |
|---|---:|---:|---:|---:|
| temperature | 14 | 23 | 37/60 | 61.67% |
| water | 32 | 20 | 52/60 | 86.67% |
| soil | 3 | 0 | 3/10 | 30.00% |
| Total | 49 | 43 | 92/130 | 70.77% |

Even the optimistic conditional envelope leaves the 38 established replaceable
true cells outside the challenged set. Simply resolving today's abstentions,
while preserving their already decided witnesses, cannot recover those cells.
For the false-process stratum, the same bookkeeping allows between 0 and
13/170 (7.65%) challenged cells. Thus zero observed false challenges is not a
logical safety guarantee for resolving the remaining uncertainty.

**Scope is essential.** New data need not produce nested intervals, and may
change baseline adequacy or the identity of viable routes. The 70.77% value is
not an upper bound on future validation, ecological identifiability, or a
redesigned learner. It is not a newly adopted acceptance criterion. The proof
concerns raw challenge states, not stability of unique attribution: unchanged
shared-carrier logic may respond differently when other challenges resolve.
The one-SEM bands are not asserted to be calibrated confidence intervals; no
coverage or population false-positive guarantee is derived here.

## Reproduction and claim boundary

From the repository root:

```bash
python scripts/diagnose_interval_evidence_v5_resolution.py --output /tmp/v5-resolution.json
python -m pytest -q tests/test_interval_evidence_v5_readout_audit.py tests/test_interval_evidence_v5_resolution_diagnosis.py
```

The new stdlib-only script first runs the existing pinned-artifact validation,
then reproduces `resolution_diagnosis.json` without mutating inputs. Fourteen
additional diagnostic tests plus the original 36 artifact tests pass locally
on Python 3.13 (50 total); this is separate from the GitHub full-suite matrix.

These results support a narrow conclusion: on this burned development set,
v5 distinguishes detectable contribution, observational replacement and
unresolved alternatives, and these are process-specific rather than a single
uniform lack of power. They do not establish universal process recovery,
necessity, real-world causal mechanisms, or prospective performance.
