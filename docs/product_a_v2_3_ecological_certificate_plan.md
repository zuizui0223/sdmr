# Product-A v2.3: set-valued ecological niche certificate

## Decision from prior lines

Product-A v2.1 and v2.2 both rejected a single-winner ecological selector. The
failure mode is structural: a procedure can recover held-out occurrence
environments or produce a stable response surface while still attributing the
niche to the wrong environmental processes.

v2.3 therefore stops asking which single procedure wins. It asks which ecological
claims are identified across the complete, predictively adequate, ecologically
non-dominated procedure set.

## Candidate-set construction

Candidate procedures enter the certificate only in this order:

1. complete finite evidence in every predeclared discovery taxon × M × outer-fold
   cell;
2. absolute prediction adequacy (`mean AUC-equivalent >= 0.51` and
   `mean - 1 SEM >= 0.50`), never relative-to-best AUC;
3. ecological recovery Pareto filtering across overlap, centroid, breadth and
   quantile-tail recovery.

The output of step 2 is the `complete_adequate_certificate` comparator. The output
of step 3 is the `ecological_pareto_certificate`. No candidate is selected from
either set by a weighted score, minimax winner, alphabetical order or fallback.

## Certificate semantics

For every validation taxon, each retained procedure is refit independently under
every predeclared M. Across all successful procedure × M fits, report:

- `necessary_process_core`: exact intersection of selected ecological process
  groups;
- `possible_processes`: exact union;
- `contested_processes`: union minus intersection;
- `unsupported_processes`: predeclared process universe minus union;
- identified min–max intervals for response optimum, lower 5% niche limit and
  upper 95% niche limit on every true response axis;
- explicit fit/evaluation abstention counts.

No process-support frequency threshold is used. Empty core means no process is
necessary under the available evidence; it is not silently converted into a
majority vote.

## Known-truth audit

The generating truth is opened only after the discovery sets and canonical AUC
point comparator are frozen. The audit records:

- whether every necessary-core process is true (false-core count);
- whether every true process is contained in the possible set;
- possible-set precision and size;
- coverage of true optimum/lower/upper response quantities by identified
  intervals;
- normalized interval width;
- canonical AUC point errors for the same response quantities;
- sharpness relative to the complete-adequate certificate.

## Predeclared panels

Known-truth seeds through 223 are opened and excluded.

- panel C1 discovery: gaussian 271, asymmetric 281, interaction 291;
  validation: soft-threshold 301, omitted-driver 311,
  observation-confounded 321.
- panel C2 discovery: gaussian 272, asymmetric 282, interaction 292;
  validation: soft-threshold 302, omitted-driver 312,
  observation-confounded 322.
- panel C3 discovery: gaussian 273, asymmetric 283, interaction 293;
  validation: soft-threshold 303, omitted-driver 313,
  observation-confounded 323.

## Decision states

- `identified_set_supported`: all Pareto certificates are available; every true
  process and response boundary is covered; no false necessary-core process is
  asserted; coverage is no worse than the complete-adequate certificate; the
  Pareto certificate is no broader in both process and boundary dimensions and
  is strictly sharper somewhere.
- `identified_set_trivial`: truth coverage is retained but the Pareto certificate
  is not sharper than the complete-adequate certificate.
- `identified_set_not_supported`: a fully evaluated Pareto certificate excludes a
  true process/boundary, asserts a false necessary process, or loses coverage
  relative to the complete-adequate certificate.
- `identified_set_unavailable`: one or more panels cannot produce a non-empty
  complete and adequate certificate.

All outcomes are development evidence only. No result directly authorizes
empirical promotion or merging PR #1 to `main`.
