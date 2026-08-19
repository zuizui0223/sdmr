# PR #1 merge-readiness record

Recorded: 2026-08-19

This record separates **repository integration** from **scientific promotion**. The
same decision must not be used for both.

## Integration decision

PR #1 may be merged when its latest head satisfies the ordinary repository gate:

1. the branch is conflict-free and not behind `main`;
2. the latest-head required checks pass;
3. the package builds and the core and geospatial test suites pass;
4. no unresolved review thread remains;
5. the claim boundary below remains explicit.

Merging the PR means that the implementation, validation contracts, tests,
provenance records, and immutable negative/abstention evidence become the main
repository baseline. It does **not** promote a Product-A method, claim superiority
over AUC/CBI/OR10/AICc-based selectors, or authorize Product-B ecological
inference.

## Scientific decision

The final Product-A v2.4 decision is:

- `decision = exclusion_certificate_unavailable`;
- `scientific_promotion_allowed = false`;
- `all_panels_available = false`;
- `process_support = false`;
- `boundary_support = false`.

The process certificates were frozen before validation truth was read, but the
predeclared boundary product was unavailable because each panel contained only 18
complete calibrated intervals for 21 required response keys. The missing keys
were the lower limit, optimum, and upper limit for the omitted-driver soil
response. This is an abstention under the frozen rule, not a successful exclusion
certificate and not a negative proof about niche recovery.

Product B therefore remains scientifically blocked until a separately versioned
Product-A procedure is independently promoted.

## Evidence audited before this record

Initial audited head: `7d58b259f2d15aeb48882373b3d8752184c8bfb1`.

- The PR was conflict-free, mergeable, and zero commits behind `main`.
- No review, review thread, or unresolved inline comment was present.
- All 28 pull-request workflow runs associated with that head concluded
  successfully.
- The core suite passed on Python 3.10, 3.11, 3.12, and 3.13.
- On Python 3.12 the core run completed with 299 passed and 2 skipped tests after
  editable-package installation and `compileall`.
- The Python 3.12 rasterio job completed with 306 passed tests.
- The v2.4 validation decision and its pre-truth fingerprints are retained under
  `evidence/product_a_v2_4/validation/`.

This documentation commit requires the same latest-head CI check before the PR is
marked ready for review.

## Guard against adaptive validation

No additional validation seed may be consumed in this PR merely to obtain a
positive decision. A further attempt must be a new, explicitly versioned
scientific lane that:

1. redesigns and freezes calibration using discovery/calibration evidence only;
2. declares availability and scientific thresholds before validation truth is
   read;
3. uses previously unused validation seeds or an independent empirical panel;
4. records unavailable and negative outcomes without retuning toward a desired
   answer.

## Non-blocking maintenance note

GitHub Actions currently reports a Node-runtime deprecation warning for
`actions/checkout@v4` and `actions/setup-python@v5`, which are forced onto Node 24
by the runner. The actions completed successfully and this warning does not alter
the test result. Workflow-action upgrades should be handled as routine maintenance
rather than used to reopen the scientific validation result.
