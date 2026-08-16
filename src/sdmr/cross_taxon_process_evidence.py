"""Cross-taxon evidence tables for Product-B ecological process discovery.

Product B asks which environmental processes recur across taxa after Product A
has separated record prediction, observation bias, ecological recovery and
robustness.  This module intentionally stops at an evidence table: it does not
turn an arbitrary support fraction into a claim of "universal importance".

For each taxon and ecological process, support is classified as one of:

- ``stable_core``: canonical and robust ecological selectors both support it;
- ``contested``: supported by only one ecological selector;
- ``not_supported``: neither ecological selector supports it in an informative
  certificate;
- ``unresolved_abstention``: the certificate cannot make an ecological claim.

The process summary reports counts and fractions transparently.  Downstream
biome/growth-form stratification or a future promotion threshold can be applied
without changing the underlying Product-A evidence.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import pandas as pd

from .ecological_inference_certificate import EcologicalInferenceCertificate


SUPPORT_STATES = (
    "stable_core",
    "contested",
    "not_supported",
    "unresolved_abstention",
)


@dataclass(frozen=True)
class CrossTaxonProcessEvidence:
    taxon_process_evidence: pd.DataFrame
    process_summary: pd.DataFrame
    process_universe: tuple[str, ...]


def _resolved_process_universe(
    certificates: Mapping[str, EcologicalInferenceCertificate],
    process_universe: Sequence[str] | None,
) -> tuple[str, ...]:
    if process_universe is not None:
        return tuple(sorted(dict.fromkeys(str(x) for x in process_universe)))
    processes: set[str] = set()
    for certificate in certificates.values():
        processes.update(certificate.process_union)
        processes.update(certificate.stable_process_core)
        processes.update(certificate.contested_processes)
    return tuple(sorted(processes))


def aggregate_cross_taxon_process_evidence(
    certificates: Mapping[str, EcologicalInferenceCertificate],
    *,
    process_universe: Sequence[str] | None = None,
) -> CrossTaxonProcessEvidence:
    """Aggregate Product-A ecological certificates without declaring universality.

    Fractions use *informative taxa* as their denominator.  Abstaining taxa are
    retained explicitly in counts rather than silently treated as negative
    ecological evidence.
    """

    if not certificates:
        raise ValueError("at least one taxon certificate is required")
    normalized = {str(taxon): certificate for taxon, certificate in certificates.items()}
    if len(normalized) != len(certificates):
        raise ValueError("taxon identifiers must be unique after string conversion")
    universe = _resolved_process_universe(normalized, process_universe)
    if not universe:
        raise ValueError("process universe is empty")

    rows: list[dict[str, object]] = []
    for taxon in sorted(normalized):
        certificate = normalized[taxon]
        unresolved = certificate.status == "abstain_missing_selector"
        stable = set(certificate.stable_process_core)
        contested = set(certificate.contested_processes)
        canonical = set(certificate.canonical_processes)
        robust = set(certificate.robust_processes)
        for process in universe:
            if unresolved:
                state = "unresolved_abstention"
            elif process in stable:
                state = "stable_core"
            elif process in contested:
                state = "contested"
            else:
                state = "not_supported"
            rows.append(
                {
                    "taxon": taxon,
                    "process": process,
                    "support_state": state,
                    "informative_certificate": not unresolved,
                    "canonical_support": process in canonical,
                    "robust_support": process in robust,
                    "model_consensus": bool(certificate.model_consensus),
                    "process_set_consensus": bool(certificate.process_set_consensus),
                    "certificate_status": certificate.status,
                }
            )

    evidence = pd.DataFrame(rows)
    summary_rows: list[dict[str, object]] = []
    n_taxa_total = len(normalized)
    for process in universe:
        group = evidence.loc[evidence["process"].eq(process)].copy()
        informative = group.loc[group["informative_certificate"]].copy()
        n_informative = len(informative)
        n_abstained = n_taxa_total - n_informative
        counts = informative["support_state"].value_counts()
        n_stable = int(counts.get("stable_core", 0))
        n_contested = int(counts.get("contested", 0))
        n_not_supported = int(counts.get("not_supported", 0))
        n_canonical = int(informative["canonical_support"].sum())
        n_robust = int(informative["robust_support"].sum())

        def fraction(value: int) -> float:
            return float(value / n_informative) if n_informative else float("nan")

        summary_rows.append(
            {
                "process": process,
                "n_taxa_total": n_taxa_total,
                "n_informative_taxa": n_informative,
                "n_abstained_taxa": n_abstained,
                "n_stable_core": n_stable,
                "n_contested": n_contested,
                "n_not_supported": n_not_supported,
                "n_canonical_support": n_canonical,
                "n_robust_support": n_robust,
                "strong_support_fraction": fraction(n_stable),
                "any_support_fraction": fraction(n_stable + n_contested),
                "contested_fraction": fraction(n_contested),
                "not_supported_fraction": fraction(n_not_supported),
                "canonical_support_fraction": fraction(n_canonical),
                "robust_support_fraction": fraction(n_robust),
            }
        )

    summary = pd.DataFrame(summary_rows).sort_values(
        ["strong_support_fraction", "any_support_fraction", "process"],
        ascending=[False, False, True],
        na_position="last",
        kind="mergesort",
    ).reset_index(drop=True)
    evidence = evidence.sort_values(["taxon", "process"]).reset_index(drop=True)
    return CrossTaxonProcessEvidence(
        taxon_process_evidence=evidence,
        process_summary=summary,
        process_universe=universe,
    )
