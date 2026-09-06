# Density-ratio process challenge v4 — development result

## Status

Post-outcome development only. This result is **not** prospective performance evidence and does not reopen Product A.

The development algorithm and thresholds were fixed before this run:

- burned development seeds `13001–13010` across six known-truth families (`60` cases);
- rank relative non-inferiority margin `0.02`;
- balanced presence/background density-ratio log-score non-inferiority margin `0.01` nats;
- density SEM multiplier `1.0`;
- probability clipping epsilon `1e-6`;
- v3.2 shared-carrier attribution unchanged.

The density score is an equal-prior presence/background discrimination score. It is **not** interpreted as absolute occurrence probability.

## Authoritative development run

- Workflow: `density-ratio-process-challenge-v4-development`
- Run: `34024183605`
- Aggregate artifact: `9986631789`
- Artifact digest: `sha256:71934efa1f7676bce7c463c8ad95a29e994f1811db1d2c6d07ef4e15dc7c0721`
- Cases: `60`
- Process cells: `300`

All six family jobs and the aggregate completed successfully after the fail-closed `model_label × route × fold` evidence-key checks passed.

## Result

Compared with v3.2 on the same burned development denominator:

| metric | v3.2 | v4 |
|---|---:|---:|
| true-process challenge recall | 86/130 = 0.661538 | 92/130 = 0.707692 |
| false-process challenge rate | 4/170 = 0.023529 | 13/170 = 0.076471 |
| true unique-attribution recall | 82/130 = 0.630769 | 81/130 = 0.623077 |
| false unique-attribution rate | 1/170 = 0.005882 | 5/170 = 0.029412 |
| false-required rate | 0 | 0 |

The v4 status changed from v3 in `15` process cells.

### Fifteen v4 status changes

True generating processes newly changed from `replaceable` to `contributory` (`6`):

- temperature: `5`
  - gaussian seed `13005`
  - observation_confounded seeds `13001`, `13002`, `13004`, `13007`
- water: `1`
  - omitted_driver seed `13010`

Non-generating processes newly changed from `replaceable` to `contributory` (`9`):

- seasonality: `8`
  - asymmetric `13008`
  - gaussian `13001`
  - observation_confounded `13003`, `13008`
  - omitted_driver `13006`, `13009`
  - soft_threshold `13005`, `13010`
- soil: `1`
  - soft_threshold `13005`

The new false seasonality challenge signals also altered shared-carrier attribution. Seven previously uniquely attributed true water signals became `contested_shared_information`:

- asymmetric `13008`
- gaussian `13001`
- observation_confounded `13003`, `13008`
- omitted_driver `13009`
- soft_threshold `13005`, `13010`

This explains why raw challenge recall improved while unique-attribution recall slightly declined.

## Decision

**v4 is not promoted as an improvement over v3.2.**

The proper density-ratio score recovered six additional true process challenges but introduced nine additional false challenges, mostly seasonality, and propagated several of those false challenge signals into the shared-carrier attribution layer.

Do **not** tune the `0.01`-nat density margin against these same outcomes to rescue the method.

The next development question is structural rather than threshold-based:

> Does a density-score challenge become reliable only when the rank evidence also shows a directionally concordant loss?

The next diagnostic therefore inspects paired rank and density deltas for the 15 changed process cells. A successor rule, if justified, should require independent/concordant evidence rather than accepting a density-only process challenge. Any eventual performance claim requires a new unused prospective denominator after development is frozen.
