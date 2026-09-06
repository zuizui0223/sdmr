# The six route counters cannot separate every true and false abstention

**Retrospective information audit only. No reclassification, new fit, seed,
threshold, workflow, prospective gate, or Product A change.** Original v5
results remain 49 contributory / 195 replaceable / 56 unresolved / 0 required;
true challenge is 49/130 and false challenge is 0/170.

Source: PR #202 scientific head `f3b95c7aa5ea0f559b54dc797ec46fda141582c8`,
run `34037107229`, artifact `9990648093`, SHA256
`1135dde2260a22e54d963b0cad6fd7210b98a362b983eddf2a6750e5d542b3b1`.
This follows `resolution_diagnosis.md` and `certificate_burden.md`, without
changing their results or the original archive.

## Question and exact scope

The earlier readout found inferiority evidence in some viable routes for
41/43 true abstentions. Could a generic rule based only on the numbers of
inferior and indeterminate routes turn those abstentions into true challenges
without introducing false challenges?

We examine an explicitly restricted projection of the existing summary: all
six exported route counters, in this order:

    expected routes, absolutely adequate routes, noninferior routes,
    inferior viable routes, indeterminate viable routes, incomplete routes.

A deterministic signature-only postprocessor must give the same promotion
choice to every currently unresolved cell with the same six integers. Already
decided statuses are held fixed. Family, seed, process name, generating truth,
historical v3/v4 status, proxy details, continuous scores, individual route
labels and row order are not inputs to that hypothetical postprocessor.

This is a deliberately limited rule class, NOT all recorded information or
all possible ecological inference. In particular, the known-truth simulator
makes process/family identity informative; a rule allowed to use that identity
is outside this proposition. No such identity-aware or signature-only rule is
trained, selected, exported or applied here. Truth labels score the diagnostic
only. The feature projection is retrospective, not prospectively validated.

## Actual collisions in the frozen artifact

The 56 unresolved cells occupy nine distinct six-counter signatures. Three
signatures contain both true and false generating processes:

| Expected | Adequate | Noninferior | Inferior | Indeterminate | Incomplete | True cells | False cells |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 3 | 3 | 0 | 0 | 3 | 0 | 2 | 7 |
| 6 | 3 | 0 | 1 | 2 | 0 | 2 | 1 |
| 6 | 6 | 0 | 1 | 5 | 0 | 2 | 1 |

Thus six true and nine false abstentions cannot be separated by this projection.
The other signatures contain 37 true cells only or four false cells only.
A concrete same-case collision occurs in `omitted_driver`, seed `13009`:
temperature and water are true, seasonality is false, and all three have
signature `(3,3,0,0,3,0)`. The diagnostic JSON includes traceable true/false
examples for every mixed signature and the complete nine-bucket table.

Expected routes must be retained in the signature: the inherited baseline
adequacy filter can produce different expected counts even when the number
of viable routes is the same. We do not change that filter or drop cases.

## Proposition: sharp in-sample bounds for this compressed rule class

Let signature bucket s contain t_s true cells and f_s false cells. For a
hypothetical deterministic promotion indicator g(s) in {0,1}, define the
ADDITIONAL counts, relative to the unmodified v5 output:

    T(g) = sum_s t_s g(s),       F(g) = sum_s f_s g(s).

**Zero-false bound.** If F(g)=0, then every bucket with f_s>0 must have g(s)=0.
Consequently T(g) is at most the sum of t_s over buckets with f_s=0. Selecting
all those buckets realizes the bound in this finite, oracle-scored rule class.
In the artifact this sum is **37**, not all 43 true abstentions.

**Full-true lower bound.** To promote all true abstentions, every bucket with
t_s>0 must have g(s)=1. This incurs at least the sum of f_s over those buckets.
Selecting those buckets and no false-only bucket realizes the minimum in the
same finite rule class. In the artifact that minimum is **nine false cells**.

These proofs are finite partition arguments, not statistical tests or claims
about population error. Their oracle attainability means that a mapping exists
on this labeled artifact, NOT that it can be learned without truth or will
generalize. Such promotions would also lack the additional interval evidence
required by the unchanged v5 contract. They are NOT authorized v5 decisions.

## Exact complete count frontier, without selecting a policy

Dynamic programming enumerates the attainable `(additional true, additional
false)` count pairs from including/excluding whole signature buckets. It stores
no selected bucket IDs or learned mapping. The 2^9 = 512 subsets produce 216
distinct count pairs. The complete nondominated frontier is:

| Additional true | Additional false | Total true / 130 | Hypothetical recall | Total false / 170 |
|---:|---:|---:|---:|---:|
| 37 | 0 | 86/130 | 66.15% | 0/170 |
| 39 | 1 | 88/130 | 67.69% | 1/170 |
| 41 | 2 | 90/130 | 69.23% | 2/170 |
| 43 | 9 | 92/130 | 70.77% | 9/170 |

Every frontier point is reported; no budget or error threshold is adopted.
**Observed performance remains 37.69% recall and zero false challenges.** The
66.15% and other table values are hypothetical upper-envelope calculations,
not improved measured performance. Merely renaming unresolved cells does not
supply evidence of contribution or a uniquely identified ecological cause.

The previous 70.77% bound concerns acquiring additional nested interval
evidence while holding viable routes fixed. This new 66.15% zero-false bound
concerns relabeling from the six CURRENT counters WITHOUT new evidence. These
are different operations and different assumptions, not conflicting estimates.
The new nine-false lower bound must not be applied to genuine evidence updates,
process-aware models, future data or shared-carrier attribution.

## Reproduction and tests

```bash
python scripts/audit_interval_evidence_v5_summary_collisions.py --output /tmp/v5-collisions.json
python -m pytest -q tests/test_interval_evidence_v5_readout_audit.py tests/test_interval_evidence_v5_resolution_diagnosis.py tests/test_interval_evidence_v5_certificates.py tests/test_interval_evidence_v5_summary_collisions.py
```

The stdlib-only script pins the existing readout-audit source, verifies the
original ZIP and all original table invariants, then regenerates
`summary_collision_audit.json`. It neither imports the learner nor changes
the input tables. The 38 added tests verify the partition formulas, exhaustive
agreement over all 512 actual subsets, toy-domain frontiers, traceable collision
examples, exact feature projection, order invariance, original-result identity,
CLI reproduction, and rejection of malformed counts or corrupted artifacts.
These join the previous 76 tests; local test scope remains these four audit
files, separate from the repository-wide GitHub CI matrix.

## What this does and does not establish

The positive result is a checkable collision certificate and an exact bound on
what this particular compression can support. The existing 41 mixed-route true
abstentions cannot justify automatically promoting all mixed-route summaries:
some true and false cells share the same complete route-count signature.

The limitation is specific to these six counters and this burned denominator.
It is not a proof of ecological nonidentifiability from all observations, nor
that route-level scores alone would be sufficient to resolve the ambiguity.
Raw interval endpoints and per-route/fold labels remain absent. No refit,
new evidence acquisition, receipt recomputation, leakage proof, threshold
relaxation, prospective claim, or Product A reopening is performed.
