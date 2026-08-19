# Product-A v2.6 fresh validation result — 2026-08-19

## Frozen decision

Fresh-validation workflow run `32251711573` completed successfully from head `715f62ef453636e0e60a4a04d3fa71fdbfdf57a9` after the v2.6 calibration source gate passed. The final decision artifact is `9364873176` (`sha256:78cda9c4c1e8a0ddab8371bf324d214cc9b8a76d1ebd65ad562da6de5913e3ba`).

The predeclared decision is **`v2_6_supported`**:

- all 3 panels were available;
- all 9 validation taxa had complete process certificates;
- all 9 validation taxa had complete boundary certificates;
- all calibrated response intervals were complete;
- false-required processes = 0 in every panel;
- minimum possible-process recall = 1.0 in every panel;
- calibrated boundary coverage was no worse than the complete-adequate comparator in every panel;
- no validation truth was used for calibration;
- no candidate reselection or scientific-threshold tuning was performed after validation truth was opened.

The calibration provenance remained fixed to run `32249349433`, artifact `9364460724`, digest `sha256:838954febe3024fbfeaa26b3c3b8f349321ac32704a0b9be0d31fc4231389185`.

## Panel-level evidence

| panel | adequate coverage | v2.6 calibrated coverage | adequate mean normalized width | v2.6 calibrated mean normalized width | possible-process recall | possible-process precision |
|---|---:|---:|---:|---:|---:|---:|
| D1 | 0.381 | 0.762 | 0.111 | 0.340 | 1.000 | 0.467 |
| D2 | 0.333 | 0.762 | 0.243 | 0.349 | 1.000 | 0.467 |
| D3 | 0.381 | 0.857 | 0.266 | 0.359 | 1.000 | 0.467 |

The coverage gain is therefore real under the frozen criterion, but it is accompanied by wider calibrated intervals. The width ratio relative to `complete_adequate_certificate` is approximately 3.05 in D1, 1.44 in D2 and 1.35 in D3.

## Interpretation boundary

`v2_6_supported` means that Product A passed the **predeclared known-truth coverage and process-safety criteria**. It does **not** mean that the method has already demonstrated maximally sharp or uniquely identified fundamental niches.

Two limits must remain explicit:

1. Process safety is strong on recall and false-requirement control, but the possible-process set is still broad (mean precision 0.467). The result supports not falsely declaring a true process impossible/required under the frozen contract; it is not yet a claim of narrow process identification.
2. Boundary coverage improves substantially, but especially in D1 part of that gain comes from interval expansion. Because validation truth 501–523 is now opened, a new sharpness/efficiency threshold must **not** be retrofitted to v2.6 using these outcomes.

Accordingly, v2.6 is frozen as supported under its original contract, while interval sharpness and process-set informativeness become a separately predeclared successor question on new unseen evidence. Product B remains blocked until independent empirical confirmation.
