# SDMR v6 implementation plan

1. Extend permutation gate with `minimum_gain_over_null`, default 0.0 for v5 reproducibility.
2. Add tests proving v5 default unchanged and v6 requires gain >=0.01.
3. Freeze v6 validation contract on 71001–71100.
4. Run full-model-only validation.
5. If PASS, freeze confirmation 72001–72050 with identical rule.
6. If PASS, run full-pipeline integration 73001–73020.
7. Keep 74001–74020 unopened until integration passes.
