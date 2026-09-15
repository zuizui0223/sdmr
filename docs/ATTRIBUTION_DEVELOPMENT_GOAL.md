# Attribution development goal

Develop and evaluate a method that distinguishes individual, joint, and
unidentifiable predictive contributions among co-supported environmental
processes. Complete a prospectively frozen, unused-simulation evaluation once
consumed-development evidence warrants it, and preserve its terminal result.

## Gates

1. Completed: replay v22's 304 directions and explain all 74 unresolved pairs.
2. Completed: implement v23 four-route attribution and evaluate all 152 consumed
   pairs with a fixed classifier, including unresolved pairs in the denominator.
3. Completed, screen failed: specific precision 3/4, correct mixed-pair
   specificity 1/43, false inclusion 4/43. All 152 states replayed successfully.
4. Not authorized by v23: if a subsequent development result warrants validation, freeze implementation, unused
   seed cohort, pair-selection rule, denominator and success criteria before
   executing the new simulation endpoint.
5. Pending: record the prospective terminal result, including failure, without
   reclassifying it after tuning.

Product A's completed non-promotion remains fixed. Product B stays blocked.
This goal authorizes neither empirical data acquisition nor a Product A rerun.

## Current next gate

The large goal remains active. Diagnose the occurrence-to-representation gap
on the exact consumed v23 contexts before proposing another classifier.
Earlier truth-surface oracle work (PR #200, seeds 13001–13010) showed that
generating processes could be recovered with complete truth surfaces; v23
therefore does not establish intrinsic non-identifiability of this simulator.
A matched-context oracle comparison should distinguish limitations of the
occurrence scores/model fits from limitations of the four-route estimand.
Any such diagnostic must be separately specified and must not promote v23.

## Working hypothesis for v23

v22 asks whether a process contributes after its competitor has already been
removed, and gates that damaged baseline on absolute adequacy. v23 instead
requires adequacy of the full route and measures losses from that route when
removing A, B, or both. Inadequacy of a knockout route can then be evidence of
lost predictive information rather than a reason to discard the contrast.

This is a change of estimand in a new development version. It neither repairs
nor replaces the frozen v22 endpoint. Predictive necessity under the model
library does not establish biological causation or observational identifiability.
