"""Known-truth exogenous perturbations for Product-A v2 robustness development.

The same hidden ecological niche is observed through predeclared changes in:

- shared sampling-effort bias;
- accessible/background extent constructed from *outer model-pool occurrences
  only*; and
- fixed source -> shifted or shifted -> source domain transfer.

The perturbation selector never sees generating suitability. Hidden truth can be
opened later for post-selection evaluation, but this module's tuning evidence is
made only from record-prediction and held-out ecological-recovery diagnostics.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

from .known_truth_scenarios import simulate_known_truth_plant_niche
from .metrics import continuous_boyce_index, presence_rank_score
from .model import (
    fit_relative_suitability_model,
    score_ecological_suitability,
    score_relative_suitability,
)
from .model_criteria import or10
from .niche_recovery_cv import (
    RecoveryCandidate,
    cross_validated_niche_recovery,
    heldout_niche_recovery_profile,
)
from .niche_recovery_perturbation import (
    PerturbationRobustNicheRecoverySelection,
    select_perturbation_robust_niche_recovery_protocol,
)
from .validation import assign_spatial_blocks, make_presence_spatial_partition


@dataclass(frozen=True)
class KnownTruthPerturbationSpec:
    name: str
    sampling_bias_strength: float = 1.15
    access_radius: float | None = 0.35
    domain_train: str | None = None
    domain_test: str | None = None

    def __post_init__(self) -> None:
        if self.sampling_bias_strength < 0:
            raise ValueError("sampling_bias_strength must be >= 0")
        if self.access_radius is not None and self.access_radius <= 0:
            raise ValueError("access_radius must be > 0 when supplied")
        domain_pair = self.domain_train is not None or self.domain_test is not None
        if domain_pair and (self.domain_train is None or self.domain_test is None):
            raise ValueError("domain_train and domain_test must be supplied together")
        if self.domain_train is not None and self.access_radius is not None:
            raise ValueError("domain-transfer perturbations do not use access_radius")

    @property
    def is_domain_transfer(self) -> bool:
        return self.domain_train is not None


DEFAULT_KNOWN_TRUTH_PERTURBATIONS = (
    KnownTruthPerturbationSpec("sampling_low", sampling_bias_strength=0.50, access_radius=0.35),
    KnownTruthPerturbationSpec("sampling_standard", sampling_bias_strength=1.15, access_radius=0.35),
    KnownTruthPerturbationSpec("sampling_high", sampling_bias_strength=2.00, access_radius=0.35),
    KnownTruthPerturbationSpec("background_tight", sampling_bias_strength=1.15, access_radius=0.20),
    KnownTruthPerturbationSpec("background_broad", sampling_bias_strength=1.15, access_radius=0.80),
    KnownTruthPerturbationSpec(
        "source_to_shifted",
        sampling_bias_strength=1.15,
        access_radius=None,
        domain_train="source",
        domain_test="shifted",
    ),
    KnownTruthPerturbationSpec(
        "shifted_to_source",
        sampling_bias_strength=1.15,
        access_radius=None,
        domain_train="shifted",
        domain_test="source",
    ),
)


@dataclass(frozen=True)
class KnownTruthPerturbationResult:
    fold_metrics: pd.DataFrame
    selection: PerturbationRobustNicheRecoverySelection | None
    selection_error: str | None


def _nearest_planar_distance(
    query: pd.DataFrame,
    reference: pd.DataFrame,
    *,
    chunk_size: int = 512,
) -> np.ndarray:
    """Minimum distance in the simulation's synthetic coordinate units."""

    q = query[["longitude", "latitude"]].to_numpy(float)
    r = reference[["longitude", "latitude"]].to_numpy(float)
    if not len(q) or not len(r):
        return np.full(len(q), np.inf, dtype=float)
    out = np.full(len(q), np.inf, dtype=float)
    for start in range(0, len(q), int(chunk_size)):
        stop = min(len(q), start + int(chunk_size))
        delta = q[start:stop, None, :] - r[None, :, :]
        out[start:stop] = np.sqrt(np.min(np.sum(delta * delta, axis=2), axis=1))
    return out


def _candidate_spatial_metrics(
    simulation,
    candidates: Mapping[str, RecoveryCandidate],
    *,
    perturbation: str,
    access_radius: float,
    n_spatial_blocks: int,
    inner_folds: int,
    random_state: int,
    outer_holdout_fraction: float,
    min_background: int,
) -> pd.DataFrame:
    occurrence = simulation.occurrences.reset_index(drop=True)
    target = simulation.target_group.reset_index(drop=True)

    # Freeze outer occurrence blocks BEFORE M/background construction. Only the
    # model-pool side is allowed to define the simulated accessible/background
    # radius, matching Product-A's sealed-before-M information barrier.
    partition = make_presence_spatial_partition(
        occurrence["longitude"].to_numpy(float),
        occurrence["latitude"].to_numpy(float),
        n_blocks=n_spatial_blocks,
        holdout_fraction=outer_holdout_fraction,
        random_state=random_state,
    )
    model_mask = np.isin(partition.presence_blocks, partition.train_blocks)
    model_occurrence = occurrence.loc[model_mask].reset_index(drop=True)
    model_groups = partition.presence_blocks[model_mask]
    if len(model_occurrence) < 20 or len(np.unique(model_groups)) < 2:
        raise ValueError("outer model-pool occurrences are insufficient for perturbation CV")

    distance = _nearest_planar_distance(target, model_occurrence)
    background = target.loc[distance <= float(access_radius)].reset_index(drop=True)
    if len(background) < int(min_background):
        raise ValueError(
            f"perturbation {perturbation!r} produced only {len(background)} background rows"
        )
    background_groups = assign_spatial_blocks(
        background["longitude"].to_numpy(float),
        background["latitude"].to_numpy(float),
        partition.centers_xyz,
    )

    frames = []
    for name in sorted(candidates):
        candidate = candidates[name]
        frame = cross_validated_niche_recovery(
            model_occurrence,
            background,
            model_groups,
            background_groups,
            candidate.predictors,
            simulation.audit_predictors,
            observation_predictors=candidate.observation_predictors,
            n_splits=inner_folds,
            model_spec=candidate.model_spec,
        )
        if frame.empty:
            continue
        frame["candidate"] = str(name)
        frame["perturbation"] = str(perturbation)
        frame["perturbation_type"] = "sampling_or_background"
        frame["access_radius"] = float(access_radius)
        frame["n_predictors"] = len(candidate.predictors)
        frame["n_outer_model_presence"] = len(model_occurrence)
        frame["n_accessible_background"] = len(background)
        frames.append(frame)
    if not frames:
        raise ValueError(f"no candidate produced metrics for perturbation {perturbation!r}")
    return pd.concat(frames, ignore_index=True)


def _candidate_domain_transfer_metrics(
    simulation,
    candidates: Mapping[str, RecoveryCandidate],
    *,
    perturbation: str,
    train_domain: str,
    test_domain: str,
) -> pd.DataFrame:
    occurrence = simulation.occurrences.reset_index(drop=True)
    background = simulation.target_group.reset_index(drop=True)
    if "domain" not in occurrence.columns or "domain" not in background.columns:
        raise KeyError("domain-transfer perturbation requires a domain column")

    p_train = occurrence.loc[occurrence["domain"].astype(str).eq(str(train_domain))].reset_index(drop=True)
    p_test = occurrence.loc[occurrence["domain"].astype(str).eq(str(test_domain))].reset_index(drop=True)
    b_train = background.loc[background["domain"].astype(str).eq(str(train_domain))].reset_index(drop=True)
    b_test = background.loc[background["domain"].astype(str).eq(str(test_domain))].reset_index(drop=True)
    if min(len(p_train), len(p_test)) < 10 or min(len(b_train), len(b_test)) < 20:
        raise ValueError(
            f"domain perturbation {perturbation!r} has insufficient source/target rows"
        )

    rows = []
    for name in sorted(candidates):
        candidate = candidates[name]
        try:
            model = fit_relative_suitability_model(
                p_train,
                b_train,
                candidate.predictors,
                model_spec=candidate.model_spec,
            )
            train_p_scores = score_relative_suitability(model, p_train, candidate.predictors)
            test_p_scores = score_relative_suitability(model, p_test, candidate.predictors)
            test_b_scores = score_relative_suitability(model, b_test, candidate.predictors)
            ecological_b_scores = score_ecological_suitability(
                model,
                b_test,
                candidate.predictors,
                observation_predictors=candidate.observation_predictors,
                observation_reference=b_train,
            )
            profile = heldout_niche_recovery_profile(
                b_train,
                b_test,
                p_test,
                ecological_b_scores,
                simulation.audit_predictors,
            )
        except (ValueError, KeyError, np.linalg.LinAlgError):
            continue
        rows.append(
            {
                "candidate": str(name),
                "perturbation": str(perturbation),
                "perturbation_type": "domain_transfer",
                "fold": 0,
                "presence_rank": presence_rank_score(test_p_scores, test_b_scores),
                "continuous_boyce": continuous_boyce_index(test_p_scores, test_b_scores),
                "or10": or10(train_p_scores, test_p_scores),
                "n_predictors": len(candidate.predictors),
                "domain_train": str(train_domain),
                "domain_test": str(test_domain),
                "n_model_presence": len(p_train),
                "n_heldout_presence": len(p_test),
                "n_model_background": len(b_train),
                "n_heldout_background": len(b_test),
                **profile.as_dict(),
            }
        )
    if not rows:
        raise ValueError(f"no candidate produced domain-transfer metrics for {perturbation!r}")
    return pd.DataFrame(rows)


def evaluate_known_truth_perturbations(
    family: str,
    seed: int,
    candidates: Mapping[str, RecoveryCandidate],
    *,
    perturbations: Sequence[KnownTruthPerturbationSpec] = DEFAULT_KNOWN_TRUTH_PERTURBATIONS,
    n_cells: int = 3500,
    n_occurrences: int = 280,
    n_target_group: int = 1000,
    n_spatial_blocks: int = 6,
    inner_folds: int = 3,
    outer_holdout_fraction: float = 0.20,
    focal_recording_bias_strength: float = 4.0,
    min_background: int = 80,
    chance_auc: float = 0.50,
    minimum_auc_margin: float = 0.01,
    auc_sem_multiplier: float = 1.0,
) -> KnownTruthPerturbationResult:
    """Evaluate one fixed candidate library across predeclared perturbations."""

    frames = []
    for spec in perturbations:
        simulation = simulate_known_truth_plant_niche(
            family,
            seed=int(seed),
            n_cells=n_cells,
            n_occurrences=n_occurrences,
            n_target_group=n_target_group,
            sampling_bias_strength=float(spec.sampling_bias_strength),
            focal_recording_bias_strength=(
                float(focal_recording_bias_strength)
                if str(family) == "observation_confounded"
                else 0.0
            ),
        )
        if spec.is_domain_transfer:
            frame = _candidate_domain_transfer_metrics(
                simulation,
                candidates,
                perturbation=spec.name,
                train_domain=str(spec.domain_train),
                test_domain=str(spec.domain_test),
            )
        else:
            frame = _candidate_spatial_metrics(
                simulation,
                candidates,
                perturbation=spec.name,
                access_radius=float(spec.access_radius),
                n_spatial_blocks=n_spatial_blocks,
                inner_folds=inner_folds,
                random_state=int(seed),
                outer_holdout_fraction=outer_holdout_fraction,
                min_background=min_background,
            )
        frame["family"] = str(family)
        frame["seed"] = int(seed)
        frame["sampling_bias_strength"] = float(spec.sampling_bias_strength)
        frames.append(frame)
    metrics = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    try:
        selection = select_perturbation_robust_niche_recovery_protocol(
            metrics,
            chance_auc=chance_auc,
            minimum_auc_margin=minimum_auc_margin,
            auc_sem_multiplier=auc_sem_multiplier,
        )
        error = None
    except ValueError as exc:
        selection = None
        error = str(exc)
    return KnownTruthPerturbationResult(
        fold_metrics=metrics,
        selection=selection,
        selection_error=error,
    )
