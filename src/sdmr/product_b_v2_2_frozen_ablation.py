"""Product-B v2.2 frozen-representation process ablation.

Product A asks whether an ecological recovery *procedure* can recover the niche
when a process domain is removed and the procedure is allowed to re-optimise.
That is a necessity / replaceability question.

Product B asks a different question: after Product A has recovered one ecological
representation, how much of that recovered niche geometry is carried by each
process domain across taxa?  Re-running feature selection after a process is
removed lets the algorithm adapt and can make the Product-B result depend on
selection feasibility rather than on the recovered representation itself.

This module therefore freezes the predictors selected by the Product-A procedure
within each outer fold, removes one process from that selected representation,
refits only the statistical response surface, and evaluates the same held-out
fold.  No predictor selection or process-dependent candidate selection is rerun.
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
from .observation_corrected_recovery import observation_corrected_heldout_niche_recovery_profile
from .observation_process import inverse_observation_propensity_weights


def _selected_predictors(value: object) -> tuple[str, ...]:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ()
    return tuple(x for x in (part.strip() for part in str(value).split(",")) if x)


def _constant_scores(n: int) -> np.ndarray:
    return np.full(int(n), 0.5, dtype=float)


def frozen_representation_process_ablation(
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
) -> pd.DataFrame:
    """Ablate processes from the base fold representation without reselection.

    ``base_fold_metrics`` must contain exactly one row for every requested fold
    of the already evaluated frozen Product-A procedure.  Its
    ``selected_predictors`` column is the representation being intervened on.

    If removing a process leaves no fitted predictor, the ablated ecological
    surface is defined as constant suitability.  This is an explicit null
    representation, not a failed or silently skipped fold, so Product B retains a
    complete denominator without interpreting numerical/selection failure as
    biological necessity.
    """

    p_groups = np.asarray(presence_groups)
    b_groups = np.asarray(background_groups)
    if len(p_groups) != len(presence) or len(b_groups) != len(background):
        raise ValueError("spatial group arrays must align with model-pool rows")
    required = {"fold", "candidate", "selected_predictors"}
    missing = required - set(base_fold_metrics.columns)
    if missing:
        raise KeyError(f"base_fold_metrics missing columns: {sorted(missing)}")
    base = base_fold_metrics.loc[
        base_fold_metrics["candidate"].astype(str).eq(procedure.label)
    ].copy()
    expected_folds = tuple(range(int(outer_folds)))
    observed_folds = tuple(sorted(pd.to_numeric(base["fold"], errors="raise").astype(int)))
    if observed_folds != expected_folds or len(base) != len(expected_folds):
        raise ValueError(
            f"base representation requires exact folds {list(expected_folds)}, observed={list(observed_folds)}"
        )
    if base.duplicated("fold").any():
        raise ValueError("base representation is not unique by fold")
    base_by_fold = {
        int(row.fold): row
        for row in base.sort_values("fold", kind="mergesort").itertuples(index=False)
    }

    folds = min(int(outer_folds), len(np.unique(p_groups)))
    if folds != int(outer_folds) or folds < 2:
        raise ValueError("requested Product-B outer folds are not structurally available")
    splitter = GroupKFold(n_splits=folds)
    dummy = np.zeros(len(presence), dtype=int)
    observation = tuple(dict.fromkeys(str(x) for x in procedure.observation_predictors))
    aliases = {str(k): str(v) for k, v in process_aliases.items()}
    rows: list[dict[str, object]] = []

    for fold, (train_idx, test_idx) in enumerate(splitter.split(dummy, groups=p_groups)):
        train_blocks = np.unique(p_groups[train_idx])
        test_blocks = np.unique(p_groups[test_idx])
        bg_train_mask = np.isin(b_groups, train_blocks)
        bg_test_mask = np.isin(b_groups, test_blocks)
        if bg_train_mask.sum() < 5 or bg_test_mask.sum() < 5 or len(test_idx) < 2:
            raise ValueError(f"frozen Product-B fold {fold} lacks structural background support")
        p_train = presence.iloc[train_idx].reset_index(drop=True)
        p_test = presence.iloc[test_idx].reset_index(drop=True)
        b_train = background.loc[bg_train_mask].reset_index(drop=True)
        b_test = background.loc[bg_test_mask].reset_index(drop=True)
        base_selected = _selected_predictors(getattr(base_by_fold[fold], "selected_predictors"))
        if not base_selected:
            raise ValueError(f"base fold {fold} selected no predictors")
        unknown = sorted(set(base_selected) - set(presence.columns) - set(background.columns))
        if unknown:
            raise KeyError(f"base fold {fold} references unknown predictors: {unknown}")

        weights = inverse_observation_propensity_weights(
            p_train,
            b_train,
            p_test,
            observation if observation_correction_active else (),
            truncation_quantile=observation_weight_truncation_quantile,
        )

        for process in process_domains:
            process = str(process)
            excluded = tuple(
                predictor
                for predictor in base_selected
                if predictor not in set(observation)
                and aliases.get(str(predictor), str(predictor)) == process
            )
            retained = tuple(p for p in base_selected if p not in set(excluded))
            retained_observation = tuple(p for p in observation if p in retained)
            retained_ecological = tuple(p for p in retained if p not in set(retained_observation))

            if retained:
                model = fit_relative_suitability_model(
                    p_train,
                    b_train,
                    retained,
                    model_spec=procedure.model_spec,
                )
                train_p_scores = score_relative_suitability(model, p_train, retained)
                test_p_scores = score_relative_suitability(model, p_test, retained)
                test_b_scores = score_relative_suitability(model, b_test, retained)
                ecological_b_scores = score_ecological_suitability(
                    model,
                    b_test,
                    retained,
                    observation_predictors=retained_observation,
                    observation_reference=b_train,
                )
                null_representation = False
            else:
                train_p_scores = _constant_scores(len(p_train))
                test_p_scores = _constant_scores(len(p_test))
                test_b_scores = _constant_scores(len(b_test))
                ecological_b_scores = _constant_scores(len(b_test))
                null_representation = True

            profile = observation_corrected_heldout_niche_recovery_profile(
                b_train,
                b_test,
                p_test,
                ecological_b_scores,
                weights.weights,
                audit_predictors,
            )
            rows.append(
                {
                    "fold": int(fold),
                    "candidate": procedure.label + "::frozen_ablate::" + process,
                    "procedure": procedure.label + "::frozen_ablate::" + process,
                    "base_candidate": procedure.label,
                    "strategy": procedure.strategy,
                    "model": procedure.model_spec.label,
                    "selected_predictors": ",".join(retained),
                    "selected_ecological_predictors": ",".join(retained_ecological),
                    "n_predictors": len(retained),
                    "n_ecological_predictors": len(retained_ecological),
                    "base_selected_predictors": ",".join(base_selected),
                    "excluded_process_domain": process,
                    "excluded_predictors": ",".join(excluded),
                    "predictor_reselection_after_process_drop": False,
                    "frozen_representation_ablation": True,
                    "null_representation_after_drop": bool(null_representation),
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
                }
            )

    result = pd.DataFrame(rows)
    expected_rows = len(expected_folds) * len(tuple(process_domains))
    if len(result) != expected_rows:
        raise AssertionError(
            f"frozen Product-B ablation denominator changed: expected {expected_rows}, observed {len(result)}"
        )
    return result.sort_values(
        ["excluded_process_domain", "fold"], kind="mergesort"
    ).reset_index(drop=True)
