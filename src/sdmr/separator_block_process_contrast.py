"""Evidence extraction inside preselected environmental separator blocks.

This module does not select separator blocks and does not declare a process
winner. It receives separator blocks selected independently from background
environmental decorrelation, fits the same SDM specification outside those
blocks, and reports observation-corrected held-out loss from pairwise
conditional knockouts.
"""
from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from .conditional_shared_information_knockout import fit_conditional_shared_information_knockout
from .density_ratio_process_challenge import balanced_density_ratio_log_score
from .model import ModelSpec, fit_relative_suitability_model, score_ecological_suitability
from .observation_aware_identification import _prepare_observation_corrections, _weighted_presence_rank


def _indices(labels: np.ndarray, block: int) -> tuple[np.ndarray, np.ndarray]:
    test = np.flatnonzero(labels == block)
    train = np.flatnonzero(labels != block)
    return train, test


def separator_block_process_contrast(
    presence: pd.DataFrame,
    background: pd.DataFrame,
    presence_blocks: Sequence[int],
    background_blocks: Sequence[int],
    *,
    separator_blocks: Sequence[int],
    target_process: str,
    competitor_process: str,
    target_predictors: Sequence[str],
    competitor_predictors: Sequence[str],
    ecological_predictors: Sequence[str],
    observation_predictors: Sequence[str] = (),
    model_spec: ModelSpec,
    knockout_degree: int = 2,
    knockout_ridge_alpha: float = 1.0,
    density_probability_epsilon: float = 1e-6,
    observation_signal_chance: float = 0.50,
    observation_signal_margin: float = 0.01,
    observation_signal_sem_multiplier: float = 1.0,
    observation_weight_truncation_quantile: float = 0.99,
    observation_weight_probability_epsilon: float = 1e-4,
    minimum_test_presence: int = 3,
    minimum_test_background: int = 10,
) -> pd.DataFrame:
    """Return block-wise baseline and pairwise-knockout ecological evidence."""
    pblocks = np.asarray(presence_blocks)
    bblocks = np.asarray(background_blocks)
    if pblocks.shape != (len(presence),) or bblocks.shape != (len(background),):
        raise ValueError("block labels must align with data rows")
    target = tuple(str(x) for x in target_predictors)
    competitor = tuple(str(x) for x in competitor_predictors)
    if not target or not competitor:
        raise ValueError("target and competitor predictor sets must be non-empty")
    if set(target) & set(competitor):
        raise ValueError("pairwise contrast requires structurally disjoint closures")
    eco = tuple(str(x) for x in ecological_predictors)
    obs = tuple(str(x) for x in observation_predictors)
    predictors = eco + obs
    blocks = tuple(sorted(set(int(x) for x in separator_blocks)))
    folds = tuple(
        (*_indices(pblocks, block), *_indices(bblocks, block))
        for block in blocks
    )
    # Reorder from (p_train,p_test,b_train,b_test) to the learner's
    # (p_train,b_train,p_test,b_test) convention.
    folds = tuple((pt, bt, pe, be) for pt, pe, bt, be in folds)
    corrections = _prepare_observation_corrections(
        presence,
        background,
        pblocks,
        bblocks,
        obs,
        folds,
        observation_signal_chance=float(observation_signal_chance),
        observation_signal_margin=float(observation_signal_margin),
        observation_signal_sem_multiplier=float(observation_signal_sem_multiplier),
        observation_weight_truncation_quantile=float(observation_weight_truncation_quantile),
        observation_weight_probability_epsilon=float(observation_weight_probability_epsilon),
    )
    rows: list[dict[str, object]] = []

    for block, (p_train_idx, b_train_idx, p_test_idx, b_test_idx), correction in zip(blocks, folds, corrections, strict=True):
        row = {
            "target_process": str(target_process),
            "competitor_process": str(competitor_process),
            "block": block,
            "complete": False,
            "observation_correction_active": bool(correction.active),
            "observation_signal_auc": float(correction.signal_auc),
            "observation_weight_ess": float(correction.effective_sample_size),
            "n_train_presence": int(len(p_train_idx)),
            "n_train_background": int(len(b_train_idx)),
            "n_test_presence": int(len(p_test_idx)),
            "n_test_background": int(len(b_test_idx)),
            "baseline_presence_rank": np.nan,
            "target_knockout_presence_rank": np.nan,
            "competitor_knockout_presence_rank": np.nan,
            "target_rank_loss": np.nan,
            "competitor_rank_loss": np.nan,
            "baseline_density_log_score": np.nan,
            "target_knockout_density_log_score": np.nan,
            "competitor_knockout_density_log_score": np.nan,
            "target_density_loss": np.nan,
            "competitor_density_loss": np.nan,
        }
        try:
            if not correction.complete:
                raise ValueError("candidate-independent observation correction unavailable")
            if len(p_test_idx) < int(minimum_test_presence) or len(b_test_idx) < int(minimum_test_background):
                raise ValueError("separator block lacks held-out evaluation rows")
            p_train = presence.iloc[p_train_idx].reset_index(drop=True)
            b_train = background.iloc[b_train_idx].reset_index(drop=True)
            p_test = presence.iloc[p_test_idx].reset_index(drop=True)
            b_test = background.iloc[b_test_idx].reset_index(drop=True)

            baseline = fit_relative_suitability_model(p_train, b_train, predictors, model_spec=model_spec)
            p_base = score_ecological_suitability(baseline, p_test, predictors, observation_predictors=obs, observation_reference=b_train)
            b_base = score_ecological_suitability(baseline, b_test, predictors, observation_predictors=obs, observation_reference=b_train)

            pk = fit_conditional_shared_information_knockout(
                b_train, process=str(target_process), process_predictors=target, conditioning_predictors=competitor,
                degree=int(knockout_degree), ridge_alpha=float(knockout_ridge_alpha), minimum_complete_rows=10,
            )
            qk = fit_conditional_shared_information_knockout(
                b_train, process=str(competitor_process), process_predictors=competitor, conditioning_predictors=target,
                degree=int(knockout_degree), ridge_alpha=float(knockout_ridge_alpha), minimum_complete_rows=10,
            )
            p_train_pk, b_train_pk, p_test_pk, b_test_pk = pk.transform(p_train), pk.transform(b_train), pk.transform(p_test), pk.transform(b_test)
            p_train_qk, b_train_qk, p_test_qk, b_test_qk = qk.transform(p_train), qk.transform(b_train), qk.transform(p_test), qk.transform(b_test)

            model_pk = fit_relative_suitability_model(p_train_pk, b_train_pk, predictors, model_spec=model_spec)
            model_qk = fit_relative_suitability_model(p_train_qk, b_train_qk, predictors, model_spec=model_spec)
            p_pk = score_ecological_suitability(model_pk, p_test_pk, predictors, observation_predictors=obs, observation_reference=b_train_pk)
            b_pk = score_ecological_suitability(model_pk, b_test_pk, predictors, observation_predictors=obs, observation_reference=b_train_pk)
            p_qk = score_ecological_suitability(model_qk, p_test_qk, predictors, observation_predictors=obs, observation_reference=b_train_qk)
            b_qk = score_ecological_suitability(model_qk, b_test_qk, predictors, observation_predictors=obs, observation_reference=b_train_qk)

            base_rank = _weighted_presence_rank(p_base, b_base, correction.weights)
            p_rank = _weighted_presence_rank(p_pk, b_pk, correction.weights)
            q_rank = _weighted_presence_rank(p_qk, b_qk, correction.weights)
            base_den = balanced_density_ratio_log_score(p_base, b_base, presence_weights=correction.weights, probability_epsilon=float(density_probability_epsilon))
            p_den = balanced_density_ratio_log_score(p_pk, b_pk, presence_weights=correction.weights, probability_epsilon=float(density_probability_epsilon))
            q_den = balanced_density_ratio_log_score(p_qk, b_qk, presence_weights=correction.weights, probability_epsilon=float(density_probability_epsilon))
            values = (base_rank, p_rank, q_rank, base_den, p_den, q_den)
            if not all(np.isfinite(float(x)) for x in values):
                raise ValueError("separator contrast produced non-finite evidence")
            row.update({
                "complete": True,
                "baseline_presence_rank": float(base_rank),
                "target_knockout_presence_rank": float(p_rank),
                "competitor_knockout_presence_rank": float(q_rank),
                "target_rank_loss": float(base_rank - p_rank),
                "competitor_rank_loss": float(base_rank - q_rank),
                "baseline_density_log_score": float(base_den),
                "target_knockout_density_log_score": float(p_den),
                "competitor_knockout_density_log_score": float(q_den),
                "target_density_loss": float(base_den - p_den),
                "competitor_density_loss": float(base_den - q_den),
            })
        except (ValueError, KeyError, np.linalg.LinAlgError):
            pass
        rows.append(row)
    return pd.DataFrame(rows)
