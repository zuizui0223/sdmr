# M5 empirical applicability — frozen v5 receipts for anonymous review

**Purpose.** Four compact JSON files are verbatim snapshots of the terminal real-plant v5 evidence. They document a **failed and closed** empirical promotion and are not a new cohort, re-analysis, or positive validation of M5.

**Source identity.** Copied without editing from archived branch `archive/sdmr-fresh-v5-sealed-postterminal` at source head `30032637a6661242330aa564185dc53fa4ebfa59`. Git blob SHA-1 values below describe original file bytes; byte-for-byte copying can be checked using the Git blob hash (`sha1(b"blob " + length + b"\\0" + bytes)`). The included regression test checks all four hashes.

| Snapshot in this folder | Original path on archived branch | Original Git blob SHA-1 |
|---|---|---|
| `sdmr_fresh_empirical_v5_model_pool_diagnostic.json` | `results/sdmr_fresh_empirical_v5_model_pool_diagnostic.json` | `fb6b140f49bf3bc9f28ac5601d108f95d1952fa7` |
| `sdmr_fresh_empirical_v5_model_pool_terminal_decision.json` | `results/sdmr_fresh_empirical_v5_model_pool_terminal_decision.json` | `d6b7ca10d8238a91a45efe036d26728406c62ccc` |
| `sdmr_fresh_empirical_v5_sealed_promotion_result.json` | `results/sdmr_fresh_empirical_v5_sealed_promotion_result.json` | `29c7b777d4f38ef47516cb293821ca98e5e8b643` |
| `sdmr_fresh_empirical_v5_sealed_postterminal_receipt.json` | `configs/sdmr_fresh_empirical_v5_sealed_postterminal_receipt.json` | `88f52b4df1c205b59fcadb9d6fe8ef0e886c6dfa` |

**Sequence.** The model-pool-only terminal decision fixed the failure of EMP-D (16/300 stable-sharp cells against the prespecified 80% requirement) **before** any sealed answer-check was opened. The sealed scores and run identities in the post-terminal receipt are supplied for audit only; they cannot change that decision. No model refit, learner removal, taxon exclusion, threshold revision, or re-promotion is authorized by this evidence copy.

**Diagnostic decomposition.** The nonlinear HGB learner authorized 32/50 taxa; penalized logistic regression authorized 10/50; both authorized the same 10 taxa. Only 16/60 process cells among these jointly authorized taxa had an identical sharp state. HGB alone yielded 125/300 sharp cells across the full cohort, also below the original 80% requirement. The decomposition demonstrates an operational learner/identifiability bottleneck, **not** a unique ecological causal explanation.

**Boundary of reproducibility.** These compact receipts verify the published summary metrics and decision order. The underlying GBIF occurrence records, environmental rasters, fitted models, and the earlier v2–v4 cohorts are not in this anonymous bundle; this is **not** a standalone rerunnable real-plant analysis. The separately versioned primary known-truth M5 validation has its own contract and metrics receipt.
