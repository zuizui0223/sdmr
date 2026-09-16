# Set-valued process attribution v23 — development result

## Status

**Development-only readout on the already-consumed prospective v21 known-truth endpoint.**

This result does not create a fresh empirical claim, does not reopen Product A, and does not authorize a new performance claim from the v21 denominator. Its purpose is to diagnose what remains identifiable after the prospectively supported v21 activity tier and the negative v22 forced-ranking endpoint.

Authoritative development run:

- workflow run: `35059209887`
- head: `687b31f32e5f79c4897d90939d51dbbcf1cb4913`
- output artifact: `10431279663`
- artifact digest: `sha256:4cb7c3f17348eaaed29c416830903668e14e23107421ea813b9e3739ddbd9315`
- source v21 workflow run: `34671264361`
- source v21 terminal artifact: `10291023518`
- source v21 head: `96c317c1ab40e3c0a2619b8412f5c8021f083814`

The set representation was built before known-truth scoring and from support columns only. The CI then scored the already-written sets against known truth in a separate step.

## Truth-blind set geometry

Across the frozen `480` v21 contexts:

| state | count | fraction of all contexts |
| --- | ---: | ---: |
| empty supported set | 150 | 0.3125 |
| singleton supported set | 208 | 0.4333 |
| multi-member supported set | 122 | 0.2542 |

Among the `330` non-empty contexts, `63.0%` were singleton and `37.0%` were multi-member.

Supported-set sizes were:

- size 0: `150`
- size 1: `208`
- size 2: `107`
- size 3: `15`

The dominant co-support pattern was `temperature + water` (`109` pair instances). Temperature and water were supported in `200` and `224` contexts respectively; seasonality was supported in `41`, and noise in `2`.

These quantities are **truth-free ambiguity diagnostics**. They describe how often occurrence evidence returns no supported process, one supported process, or a co-supported set before any generating-process labels are opened.

## Known-truth development score after set freeze

Known truth was opened only after the set representation had been written.

At the member level:

| quantity | result |
| --- | ---: |
| true-process membership recall | 424 / 960 = **0.4417** |
| false-process positive rate | 43 / 960 = **0.0448** |
| positive-member precision | 424 / 467 = **0.9079** |
| singleton precision | **0.9279** |

At the context/set level:

| quantity | result |
| --- | ---: |
| all true processes covered, all 480 contexts | **0.2271** |
| exact truth set, all 480 contexts | **0.1958** |
| non-empty sets containing no false member | **0.8697** |
| multi-member contexts | **122** |
| all true processes covered within multi-member contexts | **0.8934** |
| exact truth set within multi-member contexts | **0.7705** |
| multi-member contexts containing at least one false member | **0.2295** |

The important contrast is therefore not “set-valued attribution solves process identification.” It does not. Empty and singleton outputs remain common, and the overall exhaustive-coverage rate is low because the evidence often supports fewer processes than are truly active.

The useful result is narrower: **when v21 occurrence evidence supports multiple processes, preserving that co-supported set retains substantially more correct joint-process information than forcing the same evidence through the failed v22 single-winner ranking.**

## Claim boundary

The v23 output should be called a **co-supported process set** or **set-valued attribution**.

It is **not** currently justified to call it:

- a formal confidence set;
- a guaranteed-exhaustive identified set;
- a causal process set;
- proof that every omitted process is inactive;
- a unique mechanistic explanation.

A singleton means one process is supported under the frozen v21 evidence contract; it does not prove that no second process is active. A multi-member set means multiple processes are simultaneously supported; it does not by itself authorize deletion of any member or guarantee that no additional process is active.

## What v22 taught us

The v22 ranking line attempted to convert simultaneous support into a single process winner using the same occurrence-derived evidence. That route failed: the pairwise comparisons were frequently unresolved and proxy/co-active cases could not be reliably ordered.

v23 therefore changes the estimand rather than tuning the failed ranking rule. The estimand is now:

> Which processes are individually supported by the prospectively validated v21 evidence contract in this context?

not:

> Which one process must be the winner?

## Next bottleneck

The remaining bottleneck is **set sharpening with genuinely new separating evidence**.

The next successor must not reuse v22 ranking, tune process-specific penalties, or delete members after truth inspection. It should ask what additional observation would reduce the co-supported set while preserving the already-supported members when the extra evidence is uninformative.

Candidate separating evidence classes include, depending on the ecological process:

1. repeated or temporally resolved occurrence evidence that breaks static process equivalence;
2. intervention or natural-experiment contrasts that alter one candidate process more than another;
3. independent physiological or demographic measurements tied to a declared process;
4. observation-process calibration that distinguishes ecological absence from nondetection;
5. external environmental perturbations or transfer settings in which candidate processes make different predeclared predictions.

The successor target should be **set contraction**, not top-1 accuracy:

`S_v23 -> S_new`, with `S_new` required to be a subset of `S_v23` only when the new evidence supplies a predeclared separating contrast.

A successful successor must be frozen before fresh outcomes and evaluated on a new unused denominator. The primary performance question is whether new evidence reduces set size without increasing false deletion of truly active processes.
