"""Consensus-first ecological interpretation bundle for Product-A v2.

This is the final interpretation layer after ecological candidate selection and
observation-process marginalization.  It deliberately avoids choosing yet another
winner or averaging canonical and robust models into a synthetic score.

The bundle combines:

- an ecological inference certificate (stable process core versus contested
  processes);
- selector-specific response profiles;
- a selector *range* for niche centre, breadth, limits and optimum on literal
  environmental axes shared by both models.

A selector range is not a confidence interval.  It is an explicit sensitivity
range between two predeclared ecological procedures.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .ecological_inference_certificate import (
    EcologicalInferenceCertificate,
    build_ecological_inference_certificate,
)
from .ecological_response_profile import (
    EcologicalResponseProfile,
    ecological_response_profile,
)
from .niche_recovery_cv import RecoveryCandidate


@dataclass(frozen=True)
class EcologicalInterpretationBundle:
    certificate: EcologicalInferenceCertificate
    shared_response_axes: tuple[str, ...]
    canonical_only_response_axes: tuple[str, ...]
    robust_only_response_axes: tuple[str, ...]
    response_selector_ranges: pd.DataFrame
    canonical_response: EcologicalResponseProfile
    robust_response: EcologicalResponseProfile


def _literal_ecological_axes(candidate: RecoveryCandidate) -> tuple[str, ...]:
    observation = set(candidate.observation_predictors)
    return tuple(sorted(p for p in candidate.predictors if p not in observation))


def _selector_ranges(
    canonical_summary: pd.DataFrame,
    robust_summary: pd.DataFrame,
    shared_axes: Sequence[str],
) -> pd.DataFrame:
    shared_axes = tuple(shared_axes)
    if not shared_axes:
        return pd.DataFrame(
            columns=[
                "predictor",
                "direction_sign_agreement",
                "turning_point_agreement",
            ]
        )

    left = canonical_summary.loc[
        canonical_summary["predictor"].isin(shared_axes)
    ].copy()
    right = robust_summary.loc[
        robust_summary["predictor"].isin(shared_axes)
    ].copy()
    merged = left.merge(
        right,
        on="predictor",
        how="inner",
        validate="one_to_one",
        suffixes=("__canonical", "__robust"),
    )

    range_fields = (
        "niche_center",
        "niche_breadth_sd",
        "lower_limit",
        "upper_limit",
        "marginal_optimum",
    )
    for field in range_fields:
        c = pd.to_numeric(merged[f"{field}__canonical"], errors="coerce")
        r = pd.to_numeric(merged[f"{field}__robust"], errors="coerce")
        merged[f"{field}__selector_min"] = np.fmin(c, r)
        merged[f"{field}__selector_max"] = np.fmax(c, r)
        merged[f"{field}__selector_span"] = np.abs(c - r)

    canonical_direction = np.sign(
        pd.to_numeric(
            merged["marginal_rank_correlation__canonical"], errors="coerce"
        ).to_numpy(float)
    )
    robust_direction = np.sign(
        pd.to_numeric(
            merged["marginal_rank_correlation__robust"], errors="coerce"
        ).to_numpy(float)
    )
    merged["direction_sign_agreement"] = canonical_direction == robust_direction
    merged["turning_point_agreement"] = (
        pd.to_numeric(
            merged["marginal_direction_changes__canonical"], errors="coerce"
        ).to_numpy(float)
        == pd.to_numeric(
            merged["marginal_direction_changes__robust"], errors="coerce"
        ).to_numpy(float)
    )
    return merged.sort_values("predictor").reset_index(drop=True)


def build_ecological_interpretation_bundle(
    canonical_candidate: str,
    robust_candidate: str,
    candidates: Mapping[str, RecoveryCandidate],
    audit_environment: pd.DataFrame,
    canonical_ecological_suitability: Sequence[float] | np.ndarray,
    robust_ecological_suitability: Sequence[float] | np.ndarray,
    *,
    process_groups: Mapping[str, str] | None = None,
    n_bins: int = 20,
    lower_mass: float = 0.05,
    upper_mass: float = 0.95,
) -> EcologicalInterpretationBundle:
    """Build a non-averaged ecological interpretation from two procedures.

    Process aliases may establish a stable process claim even when the literal
    environmental variables differ (e.g. temperature versus a temperature proxy).
    Numeric optima/limits are compared only for literal shared axes because values
    on different proxy scales are not commensurable.
    """

    certificate = build_ecological_inference_certificate(
        canonical_candidate,
        robust_candidate,
        candidates,
        process_groups=process_groups,
    )
    canonical = candidates[canonical_candidate]
    robust = candidates[robust_candidate]
    canonical_axes = set(_literal_ecological_axes(canonical))
    robust_axes = set(_literal_ecological_axes(robust))
    shared_axes = tuple(sorted(canonical_axes & robust_axes))
    canonical_only = tuple(sorted(canonical_axes - robust_axes))
    robust_only = tuple(sorted(robust_axes - canonical_axes))

    canonical_response = ecological_response_profile(
        audit_environment,
        canonical_ecological_suitability,
        tuple(sorted(canonical_axes)),
        n_bins=n_bins,
        lower_mass=lower_mass,
        upper_mass=upper_mass,
    )
    robust_response = ecological_response_profile(
        audit_environment,
        robust_ecological_suitability,
        tuple(sorted(robust_axes)),
        n_bins=n_bins,
        lower_mass=lower_mass,
        upper_mass=upper_mass,
    )
    ranges = _selector_ranges(
        canonical_response.summary,
        robust_response.summary,
        shared_axes,
    )
    return EcologicalInterpretationBundle(
        certificate=certificate,
        shared_response_axes=shared_axes,
        canonical_only_response_axes=canonical_only,
        robust_only_response_axes=robust_only,
        response_selector_ranges=ranges,
        canonical_response=canonical_response,
        robust_response=robust_response,
    )
