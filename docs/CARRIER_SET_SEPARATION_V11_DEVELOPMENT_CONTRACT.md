# Carrier-set separation v11 — development contract

Status: **development only**. No fresh known-truth or empirical validation is authorized by this document.

## Why v10 did not execute its intended contrast

The frozen v10 head correctly found `shared_candidate` cells, but its final implementation restricted competitor Q to processes that were themselves `v5_status == contributory`. On completed authoritative family artifacts this can leave a shared candidate P with **zero pair audits**: e.g. interaction seeds 15002 and 15008 and soft-threshold seeds 15002/15007/15009 have shared candidates but `n_pair_audits = 0`.

This is a structural mismatch. A process can carry information shared with P without itself being a total-contribution winner. Therefore the carrier of shared information must be defined from the background representation, not from the ecological outcome classification.

## v11 carrier set

For a v9 `shared_candidate` target process P, candidate carriers Q are selected **before any separator outcome comparison** using background environments only.

A Q is eligible when:

1. Q != P;
2. P and Q process-information closures are structurally disjoint under the frozen registry;
3. leave-one-block-out background prediction of P-closure from Q-closure is finite in at least 3 pre-existing spatial blocks;
4. the median held-out multivariate R2 is > 0 (Q carries reproducible information about P somewhere in the sampled environment).

No occurrence labels, suitability scores, v5/v8 status of Q, external biological labels, or generating-process truth may enter carrier selection.

## Separator and contrast

For each eligible P-Q carrier pair, retain the frozen v10 separator rule and contrast unchanged:

- separator: held-out P<-Q R2 at least 0.10 below the median of the other blocks plus 1 SEM;
- train outside each preselected separator block;
- evaluate baseline, P<-E[P|Q], and Q<-E[Q|P];
- candidate-independent observation correction remains active;
- ModelSpecs are averaged within block; blocks are the uncertainty units;
- target-favored only if target-minus-competitor loss exceeds rank 0.02 and density 0.01 by 1 SEM; symmetric for competitor-favored; otherwise unresolved.

No numerical threshold is changed from v10.

## Denominator and governance

- development denominator remains consumed seeds 15001–15010;
- v10 results are not reclassified as prospective evidence;
- v11 may diagnose whether background-defined carrier sets make shared candidates contrastable;
- no fresh known-truth seeds are opened until this development diagnosis is frozen;
- no empirical validation is authorized.
