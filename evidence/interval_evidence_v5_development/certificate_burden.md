# v5 decision certificates: process recall is not full-case recovery

**Retrospective diagnosis only. No new scientific run, seed, fit, tuning,
prospective gate, or Product A reopening.** This continues the pinned readout
of PR #202 source `f3b95c7aa5ea0f559b54dc797ec46fda141582c8`, run
`34037107229`, aggregate artifact `9990648093`. Original outputs and all
scientific settings remain unchanged. The aggregate ZIP SHA256 remains
`1135dde2260a22e54d963b0cad6fd7210b98a362b983eddf2a6750e5d542b3b1`.

## The existing quantifiers, not a new decision rule

On complete evidence and a fixed viable (absolutely adequate) route set V,
write N(r,m) for metric m establishing noninferiority and I(r,m) for it
establishing inferiority, using the existing margins and comparator.

    replaceable:  exists r in V, for every required metric m, N(r,m)
    contributory: V is nonempty and for every r in V, exists m, I(r,m)
    required:     V is empty, with the expected absolute evidence complete
    unresolved:   otherwise, or expected route/absolute evidence is incomplete

The order matters. One noninferior viable route is a sufficient replacement
witness, even if another viable route is relatively indeterminate/incomplete.
An incomplete *absolute* route, or a missing expected route, instead forces
abstention before relative evidence is considered. These are the existing
source-code precedences; the scientific contract is not changed here.

Contribution does not require the SAME inferior metric across all routes.
A rank-inferior/density-noninferior route and a rank-noninferior/density-inferior
route can jointly establish contribution. Swapping `for every route, exists
metric` to `exists metric, for every route` would change the rule.

## Proposition: route-cell certificate burden

Use the prior nested-refinement assumptions: the cases, routes, reference
comparisons, absolute adequacy and completeness remain fixed; each complete
relative band becomes a nonempty subset of its old band; margins, SEM settings
and the numerical comparator remain unchanged. Previously decided noninferior
and inferior metric states then persist.

For an unresolved process cell, let u be the number of indeterminate viable
routes. In this artifact every such cell is complete, u >= 1, and it has no
noninferior viable route. Its other viable routes are inferior.

**Claim.** Making this cell contributory requires all u currently indeterminate
routes to acquire an inferior certificate. If all u do so, that is sufficient
for contribution under the fixed rule. By contrast, one currently indeterminate
route acquiring noninferiority on every required metric suffices for
replaceability; no other route needs to resolve. Necessity cannot be created
while its nonempty viable set is fixed.

**Proof.** Existing inferior routes remain inferior. The universal route
quantifier for contribution therefore reduces exactly to the remaining u
routes. If any remains indeterminate, contribution is not established; if any
becomes noninferior, it supplies a replacement witness. If all become inferior,
every viable route is inferior. The existential replacement condition requires
only one all-metric noninferior route. This proves the claim.

A certificate unit here is **one route-cell attaining an inferior state**, not
one measurement, observation, independent experiment, model fit or CI job.
Shared data can resolve many route-cells together, or couple their outcomes.
No certificate described below has actually been acquired.

## Recomputed burden on the same 56 abstentions

| Truth stratum | Unresolved process cells | Histogram: u -> cells | Inferior route-cell certificates needed to make all contributory |
|---|---:|---|---:|
| True process | 43 | 1 -> 2; 2 -> 7; 3 -> 32; 5 -> 2 | 122 |
| False process | 13 | 2 -> 1; 3 -> 11; 5 -> 1 | 40 |

In a relaxed algebra allowing each route-cell's indeterminate state to resolve
independently, let sorted costs be u_(1) <= ... <= u_(k). The minimum certificate
count for q additional challenged process cells is the prefix sum

    C(q) = sum of u_(j), j = 1,...,q.

**Proof.** Any q cells require the sum of their own u values. Replacing a chosen
larger cost by an unchosen smaller one cannot increase that sum. The q smallest
values minimize it. Independent resolution makes that state-level minimum
attainable in the relaxation, not necessarily in the underlying fitted system.
The script reports every prefix, not a selected favorable budget.

For the true-process stratum, 10/20/30/40/43 additional challenges respectively
require at least 19/49/79/109/122 newly inferior route-cell certificates under
these assumptions. Truth labels are used only for retrospective reporting;
these oracle-counted prefixes must not become a truth-informed acquisition
policy, seed choice, tuning rule or prospective performance claim.

## New case-level bound: at most 30/60 fully recovered cases

Process-cell recall and recovering every true process in a case are different
quantities. The previous development readout found all true processes challenged
in 10/60 cases, partially challenged in 28/60, and none challenged in 22/60.

Exactly **30 cases contain at least one true process currently classified as
replaceable**. Its noninferior replacement witness persists under the same
nested-refinement assumptions. Such a case cannot attain all-true-process
challenge coverage merely by resolving its other abstentions.

Thus, writing R_c for the set of true replaceable process cells in case c,

    refined all-true coverage <= sum_c 1[R_c is empty] = 30 / 60 cases.

The other 30 cases comprise 10 already fully covered and 20 potentially fully
covered in the independent-state relaxation. Those 20 require 78 newly inferior
route-cell certificates in total. The script reports their complete prefix
frontier as well, without ranking or selecting real cases.

This **50% case-level conditional ceiling** complements the earlier
**92/130 = 70.77% process-cell conditional ceiling**. Neither is a ceiling on
future data, redesigned models, ecological identifiability or real-world causal
recovery. Nested bands and fixed viable sets are essential assumptions.
There is no guarantee that resolving uncertainty keeps false challenges zero
or preserves the shared-carrier unique-attribution output.

## Executable check against the unchanged decision source

The audit checks the original source Git blob
`969e335e10595f2cd818553e1be290bce530360c` before executing anything. It extracts
three unmodified function ASTs (`interval_evidence_state`, `_enrich_routes`,
`_classify_processes`), rather than importing model-fitting or simulation code.
The original module is not edited or replaced.

The deterministic audit checks 256 four-metric state patterns, 923 route-state
multisets for one through six expected routes, their 923 reversed orders,
923 nested state-refinement transitions, 420 nested numeric interval pairs,
six strict boundary cases, and missing/extra/duplicate route handling. It also
checks the crossed-metric quantifier example. The multiset domain includes
absolute incompleteness and relative incompleteness as distinct states.

This is exhaustive over those declared reduced state domains, not over all
floating-point values or all upstream model behavior. The algebraic proof above
and in `resolution_diagnosis.md` supplies the general conditional argument;
finite checks guard against an implementation/quantifier mismatch.

## Reproduction

From the repository root, with NumPy, pandas and pytest installed:

```bash
python scripts/audit_interval_evidence_v5_certificates.py --output /tmp/v5-certificates.json
python -m pytest -q tests/test_interval_evidence_v5_readout_audit.py tests/test_interval_evidence_v5_resolution_diagnosis.py tests/test_interval_evidence_v5_certificates.py
```

`certificate_audit.json` is the deterministic output. The 26 added regression
tests plus the original 50 pass locally on Python 3.13.5: **76 passed**. This
local result is limited to these three files, not the full repository suite.

The original artifact lacks route labels paired to interval states, raw interval
endpoints and fold tables. This audit therefore does not identify a particular
model degree or metric as the cause, independently refit the results, recompute
selection receipts, or prove absence of leakage. No previously reported status,
scientific threshold, seed, model grid, process closure, observation correction,
proxy/shared-carrier setting, sealed boundary or Product A setting is changed.
