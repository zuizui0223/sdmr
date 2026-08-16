"""Ecological inference certificates for dynamically selected procedure outputs.

Unlike fixed ``RecoveryCandidate`` libraries, a recovery procedure can select a
different raster subset after it is frozen and rerun on the complete model pool.
This helper applies the same consensus-first Product-A interpretation to those
final predictor sets without inventing a pseudo candidate object.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence

from .ecological_inference_certificate import EcologicalInferenceCertificate


def _processes(
    predictors: Sequence[str],
    observation_predictors: Sequence[str],
    process_groups: Mapping[str, str],
) -> tuple[str, ...]:
    observation = set(str(x) for x in observation_predictors)
    return tuple(
        sorted(
            {
                str(process_groups.get(str(p), str(p)))
                for p in predictors
                if str(p) not in observation
            }
        )
    )


def build_procedure_ecological_certificate(
    canonical_predictors: Sequence[str] | None,
    robust_predictors: Sequence[str] | None,
    *,
    canonical_observation_predictors: Sequence[str] = (),
    robust_observation_predictors: Sequence[str] = (),
    process_groups: Mapping[str, str] | None = None,
    canonical_label: str | None = None,
    robust_label: str | None = None,
) -> EcologicalInferenceCertificate:
    """Build the standard certificate from final procedure-selected predictors."""

    if canonical_predictors is None or robust_predictors is None:
        return EcologicalInferenceCertificate(
            status="abstain_missing_selector",
            canonical_candidate=canonical_label,
            robust_candidate=robust_label,
            model_consensus=False,
            process_set_consensus=False,
            canonical_processes=(),
            robust_processes=(),
            stable_process_core=(),
            contested_processes=(),
            canonical_only_processes=(),
            robust_only_processes=(),
            process_union=(),
            canonical_observation_predictors=tuple(sorted(set(canonical_observation_predictors))),
            robust_observation_predictors=tuple(sorted(set(robust_observation_predictors))),
        )

    groups = dict(process_groups or {})
    canonical = set(
        _processes(canonical_predictors, canonical_observation_predictors, groups)
    )
    robust = set(_processes(robust_predictors, robust_observation_predictors, groups))
    stable = canonical & robust
    canonical_only = canonical - robust
    robust_only = robust - canonical
    contested = canonical_only | robust_only
    union = canonical | robust
    model_consensus = (
        canonical_label is not None
        and robust_label is not None
        and str(canonical_label) == str(robust_label)
        and tuple(canonical_predictors) == tuple(robust_predictors)
    )
    process_consensus = canonical == robust
    if model_consensus:
        status = "model_consensus"
    elif process_consensus:
        status = "process_consensus_model_uncertainty"
    elif stable:
        status = "partial_process_consensus"
    else:
        status = "process_contested"

    return EcologicalInferenceCertificate(
        status=status,
        canonical_candidate=canonical_label,
        robust_candidate=robust_label,
        model_consensus=model_consensus,
        process_set_consensus=process_consensus,
        canonical_processes=tuple(sorted(canonical)),
        robust_processes=tuple(sorted(robust)),
        stable_process_core=tuple(sorted(stable)),
        contested_processes=tuple(sorted(contested)),
        canonical_only_processes=tuple(sorted(canonical_only)),
        robust_only_processes=tuple(sorted(robust_only)),
        process_union=tuple(sorted(union)),
        canonical_observation_predictors=tuple(sorted(set(canonical_observation_predictors))),
        robust_observation_predictors=tuple(sorted(set(robust_observation_predictors))),
    )
