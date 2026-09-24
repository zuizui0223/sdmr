# SDMR v5 permutation-gate implementation plan

**Goal:** Replace the unreliable 3-fold SEM authorization rule with a held-out conditional permutation test.

### Task 1 — OOF full-system prediction object

Create `src/sdmr/process_id/known_truth/permutation_gate.py`.

Return:
- fold id;
- test labels;
- fixed held-out predictions;
- observed fold balanced log scores;
- mean full score and mean gain.

Reuse the existing frozen shallow3 fit and random_cell split helpers.

### Task 2 — permutation p-value

Implement deterministic:
- 999 within-fold label permutations;
- preserved class counts;
- RNG seed 0;
- p=(1+#null>=observed)/1000.

Tests:
- deterministic;
- labels are permuted only inside fold;
- class counts preserved;
- constant/no-signal predictions do not authorize;
- strong synthetic signal authorizes;
- p-value resolution is 0.001.

### Task 3 — authorization rule

Authorize iff:
- mean score >= -0.75;
- mean gain > 0;
- p <= 0.001.

No SEM multiplier.

### Task 4 — frozen v5 validation contract

Seeds 51001–51100.
PASS:
- W7 0/100;
- W1/W2/W3/W4/W5/W8 each >=95/100;
- W6 report-only.

### Task 5 — independent confirmation

Only after validation PASS:
- seeds 52001–52050;
- W7 0/50;
- each informative control >=48/50;
- no rule changes.

### Task 6 — reserve future prospective seeds

Record 53001–53020 as unopened.
Do not create prospective activation until full-pipeline v5 integration passes.
