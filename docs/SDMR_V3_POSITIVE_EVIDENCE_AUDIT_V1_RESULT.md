# SDMR v3 positive-evidence audit v1 — terminal diagnostic

Status: **diagnostic-only terminal result / occurrence-information boundary identified / no prospective freeze**

## Frozen execution

- workflow run: `35487834296`
- workflow head: `79a7e153a97f7da6e899fb194769295ccc02e546`
- artifact: `sdmr-v3-positive-evidence-audit-v1`
- artifact id: `10597578439`
- artifact digest: `sha256:b2cdbf9a6e12e1cda55bbd9ef0ee4c8f32f48d7074b753c9c90aa62d6f3dc592`
- config SHA-256: `71fec5c5c2f6cfa45afb98008e19b2a35a06d4c4851a8734d078f2b2cd8946d3`
- seeds: **23001–23008**, already-burned development evidence
- worlds: `unique_process`, `interaction`, `geographic_shift`
- learners: linear and quadratic
- target-positive process cells: **30**
- learner × target-positive summary rows: **60**
- Product-A: **closed_not_reopened**
- prospective seeds opened: **none**
- fresh empirical data opened: **false**

No scientific state or threshold was changed by this audit.

## Main result

The positive-recovery gap is not explained by one simple learner-capacity defect.

### Linear learner

Among 30 target-positive cells:

- `process_free_noninferior_witness`: **16 / 30**
- `interval_indeterminate`: **12 / 30**
- `positive_contribution_evidence`: **2 / 30**
- `full_inadequate`: **0 / 30**

The only two cells with established positive contribution evidence were:

- geographic-shift seed 23006, thermal: delta = **0.03324**, SEM = **0.01150**
- geographic-shift seed 23008, thermal: delta = **0.02303**, SEM = **0.00618**

### Quadratic learner

Among 30 target-positive cells:

- `process_free_noninferior_witness`: **12 / 30**
- `interval_indeterminate`: **13 / 30**
- `full_inadequate`: **5 / 30**
- positive contribution/required evidence: **0 / 30**

Thus adding quadratic capacity changes the failure mode but does not expose a stable positive process-information gap.

## World-specific diagnosis

### W1 unique_process

Linear:
- 7/8 interval-indeterminate
- 1/8 process-free noninferior

Quadratic:
- 3/8 interval-indeterminate
- 5/8 process-free noninferior

The average linear delta is approximately **0.00948**, essentially the same scale as the fixed 0.01 margin, with mean SEM approximately **0.00958**.

### W5 interaction

Linear:
- **14/14 process-free noninferior**

Quadratic:
- 4/14 process-free noninferior
- 8/14 interval-indeterminate
- 2/14 full-inadequate

Quadratic capacity removes the pure main-effect misspecification explanation, but it still does not create established positive contribution evidence.

### W8 geographic_shift

Linear:
- 2/8 positive contribution evidence
- 5/8 interval-indeterminate
- 1/8 process-free noninferior

Quadratic:
- 3/8 full-inadequate
- 2/8 interval-indeterminate
- 3/8 process-free noninferior

This is the only development world where the occurrence learner establishes positive process evidence at all, and only under the linear route.

## Interpretation

The next issue is not justified threshold tuning and is not justified by another blind learner substitution.

The current benchmark uses a **truth-surface representation oracle** as the positive target. That oracle asks whether the complete true suitability surface loses reconstructable information when a process closure is removed.

The occurrence learner asks a different question: whether the finite occurrence-vs-background observation distribution contains enough process-specific information for the same removal to create a detectable held-out density-ratio score loss.

The audit shows that these two targets can be materially different:

```text
truth-surface process identifiability
        !=
occurrence-distribution process identifiability
        !=
finite-sample learner recovery
```

For many truth-surface-positive cells, the observed occurrence score contains either no positive gap beyond the fixed margin or an uncertainty interval that crosses it.

## Decision

**Do not freeze the current method prospectively. Do not tune the 0.01 margin or -0.75 adequacy floor against this audit.**

The next development step must add an **occurrence-distribution identifiability oracle** aligned to the balanced occurrence/background score. Its job is to ask, using the complete simulated observation distributions rather than finite occurrence samples:

> What is the maximum process-information gap that is observable from occurrence-vs-background evidence after the declared process closure is removed?

The resulting hierarchy must distinguish:

1. generating-process membership;
2. truth-surface representation identifiability;
3. occurrence-distribution identifiability under the declared observation system;
4. finite-sample learner recovery;
5. unique process attribution.

Only after this second oracle is available can the positive-recovery denominator be defined fairly. Cells that are truth-surface-positive but occurrence-distribution-replaceable must not count as learner false negatives.

The audit artifact remains diagnostic-only and can never become prospective performance evidence.
