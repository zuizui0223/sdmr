"""Product-B v4 process intervention on a frozen Product-A response surface.

Unlike v2/v3 drop-one ablations, the fitted statistical response surface is not
refit after process information is removed.  A Product-A fold model is
reconstructed once from its already frozen selected predictors, then one process
domain is jointly marginalized over a deterministic model-pool background
reference while every non-intervened predictor remains at the evaluation row.

This estimates dependence of the recovered Product-A niche surface on process
information, rather than unique non-substitutable contribution after
re-optimisation.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

from .metrics import continuous_boyce_index, presence_rank_score
from .model import fit_relative_suitability_model, score_ecological_suitability, score_relative_suitability
from .model_criteria import or10
from .niche_recovery_procedure import RecoveryProcedure
from .niche_recovery_selection import RECOVERY_DIRECTIONS
from .observation_corrected_recovery import observation_corrected_heldout_niche_recovery_profile
from .observation_process import inverse_observation_propensity_weights


def _selected_predictors(value: object) -> tuple[str, ...]:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ()
    return tuple(x for x in (part.strip() for part in str(value).split(",")) if x)


def _joint_reference_subset(
    reference: pd.DataFrame,
    columns: Sequence[str],
    *,
    max_reference_rows: int,
) -> pd.DataFrame:
    cols = tuple(dict.fromkeys(str(x) for x in columns))
    if not cols:
        return pd.DataFrame(index=[0])
    missing = sorted(set(cols) - set(reference.columns))
    if missing:
        raise KeyError(f"reference missing marginalized predictors: {missing}")
    if int(max_reference_rows) < 1:
        raise ValueError("max_reference_rows must be >= 1")
    data = reference[list(cols)].apply(pd.to_numeric, errors="coerce").dropna()
    if data.empty:
        return data
    n_ref = min(int(max_reference_rows), len(data))
    if n_ref < len(data):
        idx = np.unique(np.rint(np.linspace(0, len(data) - 1, n_ref)).astype(int))
        data = data.iloc[idx]
    return data.reset_index(drop=True)


def score_with_joint_reference_marginalization(
    model,
    frame: pd.DataFrame,
    predictors: Sequence[str],
    marginalized_predictors: Sequence[str],
    reference: pd.DataFrame,
    *,
    max_reference_rows: int = 64,
) -> np.ndarray:
    """Score a fixed fitted model after jointly marginalizing selected predictors.

    Marginalized predictors are sampled jointly from deterministic rows of the
    supplied reference, preserving their within-reference covariance.  All other
    predictors remain row-specific.  The fitted model and coefficients are never
    changed.
    """

    cols = tuple(dict.fromkeys(str(x) for x in predictors))
    marginalized = tuple(dict.fromkeys(str(x) for x in marginalized_predictors))
    if not cols:
        raise ValueError("predictors must not be empty")
    unknown = sorted(set(marginalized) - set(cols))
    if unknown:
        raise ValueError(f"marginalized predictors are not in fitted predictors: {unknown}")
    missing_frame = sorted(set(cols) - set(frame.columns))
    if missing_frame:
        raise KeyError(f"evaluation frame missing fitted predictors: {missing_frame}")
    if not marginalized:
        return score_relative_suitability(model, frame, cols)

    fixed = tuple(x for x in cols if x not in set(marginalized))
    if fixed:
        fixed_values = frame[list(fixed)].apply(pd.to_numeric, errors="coerce")
        valid = fixed_values.notna().all(axis=1).to_numpy()
    else:
        valid = np.ones(len(frame), dtype=bool)
    scores = np.full(len(frame), np.nan, dtype=float)
    if not np.any(valid):
        return scores

    ref = _joint_reference_subset(
        reference,
        marginalized,
        max_reference_rows=max_reference_rows,
    )
    if ref.empty:
        return scores

    valid_index = np.flatnonzero(valid)
    fixed_arrays = {
        col: pd.to_numeric(frame.loc[valid, col], errors="coerce").to_numpy(float)
        for col in fixed
    }
    accumulated = np.zeros(len(valid_index), dtype=float)
    n_predictions = 0
    marginalized_set = set(marginalized)
    for _, ref_row in ref.iterrows():
        X = np.empty((len(valid_index), len(cols)), dtype=float)
        for j, col in enumerate(cols):
            if col in marginalized_set:
                X[:, j] = float(ref_row[col])
            else:
                X[:, j] = fixed_arrays[col]
        prediction = model.predict_proba(X)[:, 1]
        if np.isfinite(prediction).all():
            accumulated += prediction
            n_predictions += 1
    if n_predictions:
        scores[valid_index] = accumulated / n_predictions
    return scores


def frozen_surface_process_intervention(
    presence: pd.DataFrame,
    background: pd.DataFrame,
    presence_groups: Sequence[int] | np.ndarray,
    background_groups: Sequence[int] | np.ndarray,
    base_fold_metrics: pd.DataFrame,
    audit_predictors: Sequence[str],
    procedure: RecoveryProcedure,
    process_domains: Sequence[str],
    process_aliases: Mapping[str, str],
    *,
    outer_folds: int,
    observation_correction_active: bool = False,
    observation_weight_truncation_quantile: float = 0.99,
    max_reference_rows: int = 64,
    base_reconstruction_tolerance: float = 1e-8,
) -> pd.DataFrame:
    """Erase process information from one fixed Product-A fold surface.

    The base fold's selected predictors are read from frozen Product-A evidence.
    The base model is reconstructed once on that fold's original training data.
    Every process intervention reuses exactly that fitted model; only prediction-
    time process values are jointly marginalized over the training background.
    """

    p_groups = np.asarray(presence_groups)
    b_groups = np.asarray(background_groups)
    if len(p_groups) != len(presence) or len(b_groups) != len(background):
        raise ValueError("spatial group arrays must align with model-pool rows")
    required = {"fold", "candidate", "selected_predictors", "presence_rank", *RECOVERY_DIRECTIONS}
    missing = required - set(base_fold_metrics.columns)
    if missing:
        raise KeyError(f"base_fold_metrics missing columns: {sorted(missing)}")
    base = base_fold_metrics.loc[base_fold_metrics["candidate"].astype(str).eq(procedure.label)].copy()
    expected_folds = tuple(range(int(outer_folds)))
    observed_folds = tuple(sorted(pd.to_numeric(base["fold"], errors="raise").astype(int)))
    if observed_folds != expected_folds or len(base) != len(expected_folds):
        raise ValueError(f"base surface requires exact folds {list(expected_folds)}, observed={list(observed_folds)}")
    if base.duplicated("fold").any():
        raise ValueError("base surface is not unique by fold")
    base_by_fold = {int(row.fold): row for row in base.sort_values("fold", kind="mergesort").itertuples(index=False)}

    folds = min(int(outer_folds), len(np.unique(p_groups)))
    if folds != int(outer_folds) or folds < 2:
        raise ValueError("requested Product-B v4 outer folds are not structurally available")
    splitter = GroupKFold(n_splits=folds)
    dummy = np.zeros(len(presence), dtype=int)
    observation = tuple(dict.fromkeys(str(x) for x in procedure.observation_predictors))
    observation_set = set(observation)
    aliases = {str(k): str(v) for k, v in process_aliases.items()}
    processes = tuple(str(x) for x in process_domains)
    if not processes or len(set(processes)) != len(processes):
        raise ValueError("process_domains must be non-empty and unique")
    if float(base_reconstruction_tolerance) < 0:
        raise ValueError("base_reconstruction_tolerance must be >= 0")

    rows: list[dict[str, object]] = []
    for fold, (train_idx, test_idx) in enumerate(splitter.split(dummy, groups=p_groups)):
        train_blocks = np.unique(p_groups[train_idx])
        test_blocks = np.unique(p_groups[test_idx])
        bg_train_mask = np.isin(b_groups, train_blocks)
        bg_test_mask = np.isin(b_groups, test_blocks)
        if bg_train_mask.sum() < 5 or bg_test_mask.sum() < 5 or len(test_idx) < 2:
            raise ValueError(f"frozen Product-B v4 fold {fold} lacks structural background support")
        p_train = presence.iloc[train_idx].reset_index(drop=True)
        p_test = presence.iloc[test_idx].reset_index(drop=True)
        b_train = background.loc[bg_train_mask].reset_index(drop=True)
        b_test = background.loc[bg_test_mask].reset_index(drop=True)
        base_selected = _selected_predictors(getattr(base_by_fold[fold], "selected_predictors"))
        if not base_selected:
            raise ValueError(f"base fold {fold} selected no predictors")
        unavailable = sorted(set(base_selected) - (set(presence.columns) & set(background.columns)))
        if unavailable:
            raise KeyError(f"base fold {fold} references unavailable predictors: {unavailable}")

        # Reconstruct the original Product-A fold fit once; all interventions reuse it.
        model = fit_relative_suitability_model(p_train, b_train, base_selected, model_spec=procedure.model_spec)
        base_train_p = score_relative_suitability(model, p_train, base_selected)
        base_test_p = score_relative_suitability(model, p_test, base_selected)
        base_test_b = score_relative_suitability(model, b_test, base_selected)
        base_ecological_b = score_ecological_suitability(
            model,
            b_test,
            base_selected,
            observation_predictors=tuple(x for x in observation if x in base_selected),
            observation_reference=b_train,
        )
        weights = inverse_observation_propensity_weights(
            p_train,
            b_train,
            p_test,
            observation if observation_correction_active else (),
            truncation_quantile=observation_weight_truncation_quantile,
        )
        base_profile = observation_corrected_heldout_niche_recovery_profile(
            b_train,
            b_test,
            p_test,
            base_ecological_b,
            weights.weights,
            audit_predictors,
        ).as_dict()
        expected_row = base_by_fold[fold]
        reconstructed = {"presence_rank": presence_rank_score(base_test_p, base_test_b), **base_profile}
        for metric in ("presence_rank", *RECOVERY_DIRECTIONS):
            expected = float(getattr(expected_row, metric))
            actual = float(reconstructed[metric])
            if not np.isfinite(expected) or not np.isfinite(actual) or abs(expected - actual) > float(base_reconstruction_tolerance):
                raise ValueError(
                    f"Product-B v4 base surface reconstruction mismatch fold={fold} metric={metric}: expected={expected}, actual={actual}"
                )

        base_ecological = tuple(p for p in base_selected if p not in observation_set)
        retained_observation = tuple(p for p in observation if p in base_selected)
        for process in processes:
            process_predictors = tuple(
                predictor
                for predictor in base_selected
                if predictor not in observation_set and aliases.get(str(predictor), str(predictor)) == process
            )
            train_p_scores = score_with_joint_reference_marginalization(
                model, p_train, base_selected, process_predictors, b_train, max_reference_rows=max_reference_rows
            )
            test_p_scores = score_with_joint_reference_marginalization(
                model, p_test, base_selected, process_predictors, b_train, max_reference_rows=max_reference_rows
            )
            test_b_scores = score_with_joint_reference_marginalization(
                model, b_test, base_selected, process_predictors, b_train, max_reference_rows=max_reference_rows
            )
            ecological_marginalized = tuple(dict.fromkeys((*process_predictors, *retained_observation)))
            ecological_b_scores = score_with_joint_reference_marginalization(
                model,
                b_test,
                base_selected,
                ecological_marginalized,
                b_train,
                max_reference_rows=max_reference_rows,
            )
            profile = observation_corrected_heldout_niche_recovery_profile(
                b_train,
                b_test,
                p_test,
                ecological_b_scores,
                weights.weights,
                audit_predictors,
            )
            rows.append({
                "fold": int(fold),
                "candidate": procedure.label + "::frozen_surface_marginalize::" + process,
                "procedure": procedure.label + "::frozen_surface_marginalize::" + process,
                "base_candidate": procedure.label,
                "strategy": procedure.strategy,
                "model": procedure.model_spec.label,
                "selected_predictors": ",".join(base_selected),
                "selected_ecological_predictors": ",".join(base_ecological),
                "n_predictors": len(base_selected),
                "n_ecological_predictors": len(base_ecological),
                "base_selected_predictors": ",".join(base_selected),
                "excluded_process_domain": process,
                "intervened_process_predictors": ",".join(process_predictors),
                "process_represented_in_base_surface": bool(process_predictors),
                "process_intervention": "joint_training_background_marginalization",
                "process_reference_rows_maximum": int(max_reference_rows),
                "model_refit_after_process_intervention": False,
                "predictor_reselection_after_process_intervention": False,
                "fitted_product_a_surface_frozen": True,
                "same_outer_fold_partition_as_product_a_base_evidence": True,
                "base_surface_reconstruction_verified": True,
                "presence_rank": presence_rank_score(test_p_scores, test_b_scores),
                "continuous_boyce": continuous_boyce_index(test_p_scores, test_b_scores),
                "or10": or10(train_p_scores, test_p_scores),
                "observation_correction_active": bool(observation_correction_active),
                "observation_weight_ess": weights.effective_sample_size,
                "n_model_presence": len(p_train),
                "n_heldout_presence": len(p_test),
                "n_model_background": len(b_train),
                "n_heldout_background": len(b_test),
                **profile.as_dict(),
            })

    result = pd.DataFrame(rows)
    expected_rows = len(expected_folds) * len(processes)
    if len(result) != expected_rows:
        raise AssertionError(f"Product-B v4 expected {expected_rows} intervention rows, found {len(result)}")
    return result
