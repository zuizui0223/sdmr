# Prospective ecological-identification known-truth run 1 terminal

Status: **closed / determinism gate not supported / process truth not opened**

Workflow run: `33972810926`
Trigger commit: `dbaa08d77e3c9909f5fe13546150e421b530a2b9`
Frozen denominator: six families × seeds 4101–4120 = 120 cases, two independent process replicates.

All 12 pretruth family jobs completed successfully and uploaded their frozen model/process artifacts. The terminal evaluator then compared replicate-1 and replicate-2 artifacts before opening any generating-process labels.

The deterministic floating-point gate failed on the first compared family artifact. For the asymmetric family, `learner_presence_rank` differed between independent runs:

- replicate 1: `0.6754000000000001`
- replicate 2: `0.6754083333333334`
- absolute difference: `8.333333333276904e-06`
- frozen allowed tolerance: `rtol=1e-10`, `atol=1e-12`

The terminal evaluator raised before the code section that constructs true-process labels. Therefore run 1 contains **no opened process-truth evaluation** and cannot support or refute the learner's process-recovery performance.

Audit of the downloaded asymmetric artifacts showed:

- selection receipts identical across replicates;
- process-status rows identical across replicates;
- discrete admitted/model/process identities unchanged;
- only floating prediction/recovery summaries differed at approximately 1e-5 to 1e-4 scale.

Interpretation: run 1 is a valid failure of the predeclared numerical-reproducibility gate, not a process-performance result. Seeds 4101–4120 are retired from any modified successor validation and will not be reused to obtain promotion.

Any successor must:

1. preserve the same scientific process criteria and prediction guardrails;
2. make only a predeclared numerical-execution repair;
3. demonstrate that repair on noncontract diagnostic seeds before a new scientific run;
4. use a fresh, previously unused seed denominator;
5. retain this run-1 terminal without reclassification.
