"""Process-specific information purging with truth-blind collateral audits.

v6 residualized every retained ecological predictor against the full excluded
process closure. That removes target-process leakage, but can also remove shared
environmental structure carried by other declared processes. v7 separates the
excluded process into:

* a component predictable from the closures of the other declared processes; and
* a residual component not explained by those competing process representations.

Only the latter component is used to residualize retained predictors. Both fits
use background environments only. No occurrence labels, suitability values,
external biological labels, fitted SDM coefficients, or generating-process truth
are accepted by this API.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd
from sklearn.metrics import r2_score
from sklearn.model_selection import GroupKFold, KFold

from .process_information_purge import (
    _numeric_complete,
    _purge_regressor,
    _rank_correlation,
)


COLLATERAL_PRESERVED = "collateral_preserved"
COLLATERAL_LOSS = "collateral_loss"
COLLATERAL_INDETERMINATE = "collateral_indeterminate"
COLLATERAL_INCOMPLETE = "collateral_incomplete"
COLLATERAL_STRUCTURAL_OVERLAP = "collateral_structural_overlap"


def _unique(values: Sequence[str], *, name: str, allow_empty: bool = False) -> tuple[str, ...]:
    out = tuple(str(x).strip() for x in values)
    if not out and not allow_empty:
        raise ValueError(f"{name} must be non-empty")
    if any(not x for x in out):
        raise ValueError(f"{name} must not contain empty strings")
    if len(set(out)) != len(out):
        raise ValueError(f"{name} must not contain duplicates")
    return out


@dataclass(frozen=True)
class ProcessSpecificInformationPurge:
    process: str
    process_predictors: tuple[str, ...]
    competing_predictors: tuple[str, ...]
    retained_predictors: tuple[str, ...]
    degree: int
    ridge_alpha: float
    n_fit_rows: int
    unique_component_regressor: object | None
    retained_regressor: object

    def unique_component(self, frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        z, z_valid = _numeric_complete(frame, self.process_predictors)
        if self.competing_predictors:
            w, w_valid = _numeric_complete(frame, self.competing_predictors)
            valid = z_valid & w_valid
        else:
            w = np.empty((len(frame), 0), dtype=float)
            valid = z_valid
        unique = np.full_like(z, np.nan, dtype=float)
        if valid.any():
            if self.unique_component_regressor is None:
                shared = np.zeros_like(z[valid])
            else:
                shared = np.asarray(self.unique_component_regressor.predict(w[valid]), dtype=float)
                if shared.ndim == 1:
                    shared = shared[:, None]
            unique[valid] = z[valid] - shared
        return unique, valid

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        unique, unique_valid = self.unique_component(frame)
        retained, retained_valid = _numeric_complete(frame, self.retained_predictors)
        valid = unique_valid & retained_valid
        result = frame.copy()
        for predictor in self.retained_predictors:
            result[predictor] = np.nan
        if not valid.any():
            return result
        predicted = np.asarray(self.retained_regressor.predict(unique[valid]), dtype=float)
        if predicted.ndim == 1:
            predicted = predicted[:, None]
        if predicted.shape != retained[valid].shape:
            raise RuntimeError("process-specific purge regressor returned unexpected shape")
        residual = retained[valid] - predicted
        for j, predictor in enumerate(self.retained_predictors):
            result.loc[valid, predictor] = residual[:, j]
        return result


def fit_process_specific_information_purge(
    background: pd.DataFrame,
    *,
    process: str,
    process_predictors: Sequence[str],
    competing_predictors: Sequence[str],
    retained_predictors: Sequence[str],
    degree: int = 2,
    ridge_alpha: float = 1.0,
    minimum_complete_rows: int = 10,
) -> ProcessSpecificInformationPurge:
    """Fit a background-only purge using only the target process's unique component."""

    process_name = str(process).strip()
    if not process_name:
        raise ValueError("process must be non-empty")
    target = _unique(process_predictors, name="process_predictors")
    competing = _unique(competing_predictors, name="competing_predictors", allow_empty=True)
    retained = _unique(retained_predictors, name="retained_predictors")
    overlap = sorted(set(target) & set(retained))
    if overlap:
        raise ValueError("process and retained predictors must be disjoint: " + ", ".join(overlap))
    target_competing_overlap = sorted(set(target) & set(competing))
    if target_competing_overlap:
        raise ValueError(
            "target and competing process closures overlap structurally: "
            + ", ".join(target_competing_overlap)
        )
    if int(minimum_complete_rows) < 5:
        raise ValueError("minimum_complete_rows must be >= 5")

    z, z_valid = _numeric_complete(background, target)
    y, y_valid = _numeric_complete(background, retained)
    if competing:
        w, w_valid = _numeric_complete(background, competing)
        valid = z_valid & y_valid & w_valid
    else:
        w = np.empty((len(background), 0), dtype=float)
        valid = z_valid & y_valid
    n = int(valid.sum())
    if n < int(minimum_complete_rows):
        raise ValueError(
            f"process-specific purge needs at least {int(minimum_complete_rows)} complete background rows; found {n}"
        )

    unique_regressor = None
    if competing:
        unique_regressor = _purge_regressor(degree=int(degree), ridge_alpha=float(ridge_alpha))
        unique_regressor.fit(w[valid], z[valid])
        shared = np.asarray(unique_regressor.predict(w[valid]), dtype=float)
        if shared.ndim == 1:
            shared = shared[:, None]
        unique = z[valid] - shared
    else:
        unique = z[valid]

    retained_regressor = _purge_regressor(degree=int(degree), ridge_alpha=float(ridge_alpha))
    retained_regressor.fit(unique, y[valid])
    return ProcessSpecificInformationPurge(
        process=process_name,
        process_predictors=target,
        competing_predictors=competing,
        retained_predictors=retained,
        degree=int(degree),
        ridge_alpha=float(ridge_alpha),
        n_fit_rows=n,
        unique_component_regressor=unique_regressor,
        retained_regressor=retained_regressor,
    )


def _interval_state(mean_loss: float, sem_loss: float, *, complete: bool, sem_multiplier: float) -> str:
    if not complete or not np.isfinite(mean_loss) or not np.isfinite(sem_loss):
        return COLLATERAL_INCOMPLETE
    lower = float(mean_loss) - float(sem_multiplier) * float(sem_loss)
    upper = float(mean_loss) + float(sem_multiplier) * float(sem_loss)
    if lower > 0.0:
        return COLLATERAL_LOSS
    if upper <= 0.0:
        return COLLATERAL_PRESERVED
    return COLLATERAL_INDETERMINATE


def cross_validated_collateral_information_audit(
    background: pd.DataFrame,
    *,
    process: str,
    process_predictors: Sequence[str],
    competing_process_predictors: Mapping[str, Sequence[str]],
    retained_predictors: Sequence[str],
    groups: Sequence[object] | np.ndarray | None = None,
    n_splits: int = 3,
    degree: int = 2,
    ridge_alpha: float = 1.0,
    sem_multiplier: float = 1.0,
) -> pd.DataFrame:
    """Audit target erasure and collateral loss without occurrence or truth labels.

    For the target process, the audit asks whether its closure remains
    reconstructable from retained predictors after process-specific purging. For
    every other declared process, it asks how much ability to reconstruct that
    process's original closure is lost after the target purge. Collateral states
    use a zero-margin paired fold interval: positive loss with the whole
    one-SEM interval above zero is ``collateral_loss``; uncertainty is retained as
    ``collateral_indeterminate`` rather than silently accepted.
    """

    process_name = str(process).strip()
    target = _unique(process_predictors, name="process_predictors")
    retained = _unique(retained_predictors, name="retained_predictors")
    if int(n_splits) < 2:
        raise ValueError("n_splits must be >= 2")
    if float(sem_multiplier) < 0:
        raise ValueError("sem_multiplier must be >= 0")

    competitor_map: dict[str, tuple[str, ...]] = {}
    for name, predictors in competing_process_predictors.items():
        q = str(name).strip()
        if not q or q == process_name:
            raise ValueError("competing process names must be non-empty and differ from target process")
        competitor_map[q] = _unique(predictors, name=f"competing_process_predictors[{q}]")
    competing_union = tuple(
        dict.fromkeys(p for cols in competitor_map.values() for p in cols if p not in set(target))
    )
    structural = {
        q: tuple(sorted(set(cols) & set(target))) for q, cols in competitor_map.items()
    }

    required = tuple(dict.fromkeys(target + retained + tuple(p for cols in competitor_map.values() for p in cols)))
    _, valid = _numeric_complete(background, required)
    index = np.flatnonzero(valid)
    if len(index) < max(10, 2 * int(n_splits)):
        raise ValueError("insufficient complete background rows for collateral audit")

    if groups is None:
        splitter = KFold(n_splits=int(n_splits), shuffle=False)
        split_iter = splitter.split(index)
    else:
        g = np.asarray(groups)
        if len(g) != len(background):
            raise ValueError("groups must align with background rows")
        g_valid = g[index]
        if len(np.unique(g_valid)) < int(n_splits):
            raise ValueError("insufficient unique groups for collateral audit")
        splitter = GroupKFold(n_splits=int(n_splits))
        split_iter = splitter.split(index, groups=g_valid)

    fold_rows: list[dict[str, object]] = []
    audit_targets = {process_name: target, **competitor_map}
    for fold, (train_local, test_local) in enumerate(split_iter):
        train_idx = index[np.asarray(train_local)]
        test_idx = index[np.asarray(test_local)]
        train = background.iloc[train_idx].reset_index(drop=True)
        test = background.iloc[test_idx].reset_index(drop=True)
        purge = fit_process_specific_information_purge(
            train,
            process=process_name,
            process_predictors=target,
            competing_predictors=competing_union,
            retained_predictors=retained,
            degree=int(degree),
            ridge_alpha=float(ridge_alpha),
            minimum_complete_rows=5,
        )
        train_after = purge.transform(train)
        test_after = purge.transform(test)

        for audited_process, audited_predictors in audit_targets.items():
            overlap = structural.get(audited_process, ())
            if overlap:
                for predictor in audited_predictors:
                    fold_rows.append(
                        {
                            "target_process": process_name,
                            "audited_process": audited_process,
                            "audited_predictor": predictor,
                            "audit_role": "collateral_preservation",
                            "fold": int(fold),
                            "complete": False,
                            "structural_overlap": True,
                            "pre_r2": np.nan,
                            "post_r2": np.nan,
                            "r2_loss": np.nan,
                            "pre_rank_correlation": np.nan,
                            "post_rank_correlation": np.nan,
                        }
                    )
                continue

            before_model = _purge_regressor(degree=int(degree), ridge_alpha=float(ridge_alpha))
            after_model = _purge_regressor(degree=int(degree), ridge_alpha=float(ridge_alpha))
            before_model.fit(train[list(retained)].to_numpy(float), train[list(audited_predictors)].to_numpy(float))
            after_model.fit(train_after[list(retained)].to_numpy(float), train[list(audited_predictors)].to_numpy(float))
            pred_before = np.asarray(before_model.predict(test[list(retained)].to_numpy(float)), dtype=float)
            pred_after = np.asarray(after_model.predict(test_after[list(retained)].to_numpy(float)), dtype=float)
            if pred_before.ndim == 1:
                pred_before = pred_before[:, None]
            if pred_after.ndim == 1:
                pred_after = pred_after[:, None]
            truth = test[list(audited_predictors)].to_numpy(float)
            for j, predictor in enumerate(audited_predictors):
                pre_r2 = float(r2_score(truth[:, j], pred_before[:, j]))
                post_r2 = float(r2_score(truth[:, j], pred_after[:, j]))
                fold_rows.append(
                    {
                        "target_process": process_name,
                        "audited_process": audited_process,
                        "audited_predictor": predictor,
                        "audit_role": (
                            "target_erasure" if audited_process == process_name else "collateral_preservation"
                        ),
                        "fold": int(fold),
                        "complete": True,
                        "structural_overlap": False,
                        "pre_r2": pre_r2,
                        "post_r2": post_r2,
                        "r2_loss": pre_r2 - post_r2,
                        "pre_rank_correlation": _rank_correlation(truth[:, j], pred_before[:, j]),
                        "post_rank_correlation": _rank_correlation(truth[:, j], pred_after[:, j]),
                    }
                )

    folds = pd.DataFrame(fold_rows)
    rows: list[dict[str, object]] = []
    for (audited_process, predictor, role), group in folds.groupby(
        ["audited_process", "audited_predictor", "audit_role"], sort=True
    ):
        structural_overlap = bool(group["structural_overlap"].astype(bool).any())
        complete = bool(len(group) == int(n_splits) and group["complete"].astype(bool).all())
        losses = pd.to_numeric(group["r2_loss"], errors="coerce").to_numpy(float)
        finite = losses[np.isfinite(losses)]
        mean_loss = float(np.mean(finite)) if len(finite) else float("nan")
        sem_loss = (
            float(np.std(finite, ddof=1) / np.sqrt(len(finite)))
            if len(finite) >= 2
            else (0.0 if len(finite) == 1 else float("nan"))
        )
        if structural_overlap:
            state = COLLATERAL_STRUCTURAL_OVERLAP
        elif role == "collateral_preservation":
            state = _interval_state(
                mean_loss,
                sem_loss,
                complete=complete,
                sem_multiplier=float(sem_multiplier),
            )
        else:
            state = "target_erasure_diagnostic"
        rows.append(
            {
                "target_process": process_name,
                "audited_process": str(audited_process),
                "audited_predictor": str(predictor),
                "audit_role": str(role),
                "complete": complete,
                "structural_overlap": structural_overlap,
                "mean_pre_r2": float(pd.to_numeric(group["pre_r2"], errors="coerce").mean()),
                "mean_post_r2": float(pd.to_numeric(group["post_r2"], errors="coerce").mean()),
                "mean_r2_loss": mean_loss,
                "sem_r2_loss": sem_loss,
                "mean_pre_rank_correlation": float(pd.to_numeric(group["pre_rank_correlation"], errors="coerce").mean()),
                "mean_post_rank_correlation": float(pd.to_numeric(group["post_rank_correlation"], errors="coerce").mean()),
                "collateral_state": state,
                "n_folds": int(len(group)),
            }
        )
    return pd.DataFrame(rows)
