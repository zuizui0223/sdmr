"""Consensus-first ecological inference output for Product-A v2.

Product-A v2 has two deliberately different ecological selectors:

- canonical niche recovery, which asks which adequate model best reconstructs the
  held-out environmental niche under the canonical analysis;
- perturbation-robust niche recovery, which asks which adequate model preserves
  ecological recovery under predeclared sampling/background/domain changes.

Known-truth development shows that neither should be collapsed into the other or
combined by an arbitrary weighted score.  This module therefore externalizes the
*agreement structure* between them.

The certificate promotes only ecological process groups supported by both
selectors as the stable process core.  Processes supported by only one selector
are retained as sensitivity/contested claims.  Observation-process predictors
are never promoted as ecological processes.

This object contains no hidden truth and no prediction metric.  It is suitable for
real-data interpretation after candidate selection.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass

from .niche_recovery_cv import RecoveryCandidate


@dataclass(frozen=True)
class EcologicalInferenceCertificate:
    status: str
    canonical_candidate: str | None
    robust_candidate: str | None
    model_consensus: bool
    process_set_consensus: bool
    canonical_processes: tuple[str, ...]
    robust_processes: tuple[str, ...]
    stable_process_core: tuple[str, ...]
    contested_processes: tuple[str, ...]
    canonical_only_processes: tuple[str, ...]
    robust_only_processes: tuple[str, ...]
    process_union: tuple[str, ...]
    canonical_observation_predictors: tuple[str, ...]
    robust_observation_predictors: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _ecological_processes(
    candidate: RecoveryCandidate,
    process_groups: Mapping[str, str],
) -> tuple[str, ...]:
    observation = set(candidate.observation_predictors)
    processes = {
        str(process_groups.get(str(predictor), str(predictor)))
        for predictor in candidate.predictors
        if predictor not in observation
    }
    return tuple(sorted(processes))


def build_ecological_inference_certificate(
    canonical_candidate: str | None,
    robust_candidate: str | None,
    candidates: Mapping[str, RecoveryCandidate],
    *,
    process_groups: Mapping[str, str] | None = None,
) -> EcologicalInferenceCertificate:
    """Describe what ecological interpretation is stable across two selectors.

    ``process_groups`` may collapse correlated or mechanistically equivalent
    predictors (for example, a temperature proxy and temperature itself) into a
    predeclared ecological process.  The mapping is interpretation metadata, not a
    fitted score.  Any predictor absent from the mapping is treated as its own
    process group.

    Status values are intentionally descriptive rather than ordinal:

    - ``model_consensus``: both selectors chose the same model;
    - ``process_consensus_model_uncertainty``: model specifications differ but the
      ecological process set is identical;
    - ``partial_process_consensus``: at least one ecological process is shared but
      at least one process is selector-specific;
    - ``process_contested``: selectors share no ecological process;
    - ``abstain_missing_selector``: one or both ecological selectors abstained.

    No status is converted into a scalar confidence score.
    """

    groups = dict(process_groups or {})
    if canonical_candidate is None or robust_candidate is None:
        return EcologicalInferenceCertificate(
            status="abstain_missing_selector",
            canonical_candidate=canonical_candidate,
            robust_candidate=robust_candidate,
            model_consensus=False,
            process_set_consensus=False,
            canonical_processes=(),
            robust_processes=(),
            stable_process_core=(),
            contested_processes=(),
            canonical_only_processes=(),
            robust_only_processes=(),
            process_union=(),
            canonical_observation_predictors=(),
            robust_observation_predictors=(),
        )

    missing = [
        name for name in (canonical_candidate, robust_candidate)
        if name not in candidates
    ]
    if missing:
        raise KeyError(f"unknown ecological candidate(s): {sorted(set(missing))}")

    canonical = candidates[canonical_candidate]
    robust = candidates[robust_candidate]
    canonical_processes = set(_ecological_processes(canonical, groups))
    robust_processes = set(_ecological_processes(robust, groups))
    stable = canonical_processes & robust_processes
    canonical_only = canonical_processes - robust_processes
    robust_only = robust_processes - canonical_processes
    contested = canonical_only | robust_only
    union = canonical_processes | robust_processes
    model_consensus = canonical_candidate == robust_candidate
    process_consensus = canonical_processes == robust_processes

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
        canonical_candidate=str(canonical_candidate),
        robust_candidate=str(robust_candidate),
        model_consensus=model_consensus,
        process_set_consensus=process_consensus,
        canonical_processes=tuple(sorted(canonical_processes)),
        robust_processes=tuple(sorted(robust_processes)),
        stable_process_core=tuple(sorted(stable)),
        contested_processes=tuple(sorted(contested)),
        canonical_only_processes=tuple(sorted(canonical_only)),
        robust_only_processes=tuple(sorted(robust_only)),
        process_union=tuple(sorted(union)),
        canonical_observation_predictors=tuple(sorted(canonical.observation_predictors)),
        robust_observation_predictors=tuple(sorted(robust.observation_predictors)),
    )
