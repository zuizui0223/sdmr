# SDMR v4 full-system gate confirmation v1 — terminal result

Status: **development confirmation FAIL / multiplier 1.0 rejected / no reselection / future prospective panel remains unopened**

## Frozen execution

- workflow run: `36018251680`
- workflow head: `80e9c77ed11010bf85801705ab204dc3477d3117`
- terminal artifact: `sdmr-v4-full-system-gate-confirmation-v1`
- artifact id: `10815239881`
- artifact digest: `sha256:99355939b6d308ad68a8e653a557c7b54131930583a08c0c0cbe068ee2ede1c4`
- selected multiplier: **1.0**
- confirmation seeds: **42001–42050**
- reserved future prospective seeds 43001–43020 opened: **false**
- fresh empirical data opened: **false**
- Product-A: **closed_not_reopened**

Multiplier 1.0 was frozen by calibration before confirmation opened. Reselection was forbidden.

## Frozen confirmation rule

PASS required:

- W7 omitted_driver: **0 / 50 authorized**
- each informative control W1/W2/W3/W4/W5/W8: **>= 48 / 50 authorized**
- W6 observation_confounded: report-only
- strict conjunction
- no reselection after opening confirmation

## Result

| world | authorized |
|---|---:|
| unique_process | **50 / 50** |
| redundant_representation | **50 / 50** |
| shared_carrier | **50 / 50** |
| null_correlated | **50 / 50** |
| interaction | **50 / 50** |
| geographic_shift | **50 / 50** |
| observation_confounded | 45 / 50 — report-only |
| omitted_driver | **2 / 50** |

Therefore:

```text
confirmation PASS = FALSE
```

The informative-control side passed perfectly. The null-control side failed.

## Exact conclusion

The 1×SEM gate does not provide stable false-authorization control.

Across sequential independent panels:

- prospective v3 W7: **1 / 20 authorized**
- v4 calibration W7: **0 / 100**
- v4 confirmation W7: **2 / 50**

The zero in the 100-seed calibration panel was therefore not sufficient evidence that the fold-SEM rule had controlled the finite-sample Type-I error.

This is a failure of the **authorization uncertainty model**, not of process recovery, ODO v2, shallow3 probability quality, or the process-state margin.

## Why multiplier retuning stops here

Increasing c to 1.645, 1.96, 2.326, etc. after seeing confirmation would turn the confirmation panel into a second calibration panel.

That is prohibited.

Seeds 42001–42050 are burned and may be used only for postmortem/development diagnostics.

Reserved seeds 43001–43020 remain unopened but are not activated for v4.

## Next admissible design

Replace the 3-fold SEM authorization approximation with a conditional held-out randomization test.

For each fitted full-system model:

1. obtain out-of-fold predictions under the frozen random_cell split;
2. keep those predictions fixed;
3. permute held-out class labels **within each fold**, preserving each fold's class counts;
4. recompute the same mean balanced log-score gain over -log(2);
5. use the permutation distribution as the finite-data null for full-system information.

Because held-out labels were not used to fit their fold's model, the null comparison directly targets whether the fitted full system contains held-out occurrence/background information, without treating three fold means as an approximately Gaussian sample.

A new version must freeze permutation count and alpha before new development seeds are opened.

Fresh empirical validation remains closed.
