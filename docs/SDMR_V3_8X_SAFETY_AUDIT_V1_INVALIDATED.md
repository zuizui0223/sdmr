# SDMR v3 8x safety audit v1 — invalidated execution record

Status: **development-only / execution completed / NOT AUTHORITATIVE because sharded resampling seeds drifted**

## Execution

- workflow run: `35987109202`
- head: `690be530d03a68234c29f25c7f7bc46929ade09c`
- aggregate artifact: `10802923720`
- aggregate digest: `sha256:2fa5e2b3661ce395a4a2523a62ca30d38b51170f3a5390dfa727d7b893138418`
- aggregate rows: **2304**
- Product-A: **closed_not_reopened**
- prospective seeds opened: **none**
- fresh empirical data opened: **false**

## Apparent aggregate result

The completed aggregate returned:

- random_cell positive recovery: 0.9167
- spatial positive recovery: 0.7292
- false-positive rate: 0 in both splits
- ODO-unresolved over-resolution: 0 in both splits
- structural-refusal violation rate: 0 in both splits
- ODO-unavailable favorable-call rate: 0 in both splits

These values are **not used as the authoritative 8x safety result**.

## Invalidating implementation issue

The safety audit was sharded by world.  The common resampling seed function is

```text
sampling_seed =
    ecological_seed * 100000
  + (world_index + 1) * 1000
  + multiplier * 100
  + replicate
```

The positive-power v1/v2 executions computed `world_index` from the full frozen W1–W8 order.

In safety v1 each workflow shard called the audit with only one world.  The audit then enumerated that single-world tuple and assigned `world_index = 0` to every shard.  Consequently W2–W8 used different resampling seeds from the already-frozen 8x positive-power evidence.

A direct keyed comparison of ODO-positive safety rows with the 8x positive-power tail showed state disagreement:

- random_cell agreement: **0.875**
- spatial agreement: **0.8333**

and nonzero paired-delta differences.

This is an execution/sharding bug, not a scientific failure and not a justification to change any model, margin, threshold, process definition, ODO target, or learner profile.

## Decision

**Safety v1 is invalidated as the candidate-8x safety evidence.**

A corrected v2 must:

1. keep every scientific input unchanged;
2. retain the 16-shard execution structure;
3. pass the frozen global W1–W8 index into each shard's resampling seed calculation;
4. reproduce the existing 8x positive-power states exactly for ODO-positive cells;
5. only then aggregate false-positive, over-resolution, unavailable and structural-refusal safety metrics.

The v1 artifact remains permanently recorded for provenance.
