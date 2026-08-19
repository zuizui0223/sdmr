# Product-A v2.5 calibration result

## Status

**Calibration availability failed; fresh validation was not opened.**

The model-only calibration run `32232483982` produced all 90 predeclared worker artifacts from contract SHA `5ec53b200a2c5d53df56cc496d8c0dcca36908eba0de7836ad606c070c3ba8f7`. No worker used generating truth, reselected candidates, or tuned scientific thresholds.

The original aggregate incorrectly inherited the stricter v2.4 all-calibration-taxa rule. That implementation error was corrected to the v2.5 rule frozen before outcomes: the expansion radius is the maximum normalized outside-envelope miss over **complete calibration taxa**, with at least two complete taxa required per panel × predictor × response quantity.

Recovery run `32248664571` then verified the corrected semantics tests, the source run/head, all 90 immutable worker contracts, and all 90 worker artifacts before recomputing calibration. The corrected aggregate still failed the frozen availability gate:

- `panel_D1 / soil / lower_limit`: 1 complete calibration taxon, minimum 2;
- `panel_D1 / soil / optimum`: 1 complete calibration taxon, minimum 2;
- `panel_D1 / soil / upper_limit`: 1 complete calibration taxon, minimum 2.

Therefore v2.5 cannot freeze a complete 27-key calibration artifact. The minimum support is **not** relaxed after seeing this outcome.

## Scientific interpretation

This is an availability failure, not evidence that the Product-A ecological claim is supported or refuted. It shows that two predeclared soil-capable calibration taxa per panel were not operationally redundant enough to guarantee two complete soil-response envelopes under the frozen candidate × M × spatial-refit denominator.

## Information barrier

Fresh confirmation taxa/seeds `501–503`, `511–513`, and `521–523` were not simulated or read by the calibration workers or calibration aggregate and remain reserved for an independently predeclared successor calibration design.

## Successor constraint

A successor may increase *pre-validation calibration redundancy* using new calibration-only seeds, but must not:

- lower the minimum of two complete calibration taxa per required key;
- change candidate selection based on v2.5 outcomes;
- tune scientific support thresholds;
- use fresh-validation truth for calibration;
- consume seeds 501–523 before a complete calibration artifact is frozen.
