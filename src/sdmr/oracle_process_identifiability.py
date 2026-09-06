"""Oracle observational-identifiability benchmark for known-truth niches.

This module is only for simulations where the complete ecological suitability
surface is known. It does **not** use occurrence labels and is never an input to
real-data fitting. Instead it asks a representation-conditioned question:

    how much information about the true suitability surface is irreversibly lost
    when every predictor declared to carry process P is removed?

That target is deliberately different from raw generating-process membership. A
process may appear in the generating equation yet be observationally replaceable
because the declared predictor system contains proxies or substitutable process
information. Conversely, a process-information closure may be identifiable even
when no single fitted model is unique.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import hashlib

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import r2_score
from sklearn.model_selection import GroupKFold

from .process_information_closure import normalize_process_information_registry


ORACLE_REPLACEABLE = "oracle_replaceable_under_predictor_system"
ORACLE_CONTRIBUTORY = "oracle_contributory_under_predictor_system"
ORACLE_REQUIRED = "oracle_required_under_predictor_system"
ORACLE_CONTESTED = "oracle_contested_under_predictor_system"
ORACLE_UNAVAILABLE = "oracle_unavailable"


@dataclass(frozen=True)
class OracleProcessIdentifiability:
    """Cross-validated oracle process-information benchmark."""

    predictor_universe: tuple[str, ...]
    process_universe: tuple[str, ...]
    fold_evidence: pd.DataFrame
    baseline_summary: pd.DataFrame
    process_summary: pd.DataFrame
    relative_loss_margin: float
    sem_multiplier: float
    baseline_r2_floor: float
    required_r2_ceiling: float
    selection_receipt: str


def _clean_unique(values: Sequence[str], *, name: str) -> tuple[str, ...]:
    out = tuple(str(x).strip() for x in values)
    if not out or any(not x for x in out):
        raise ValueError(f"{name} must contain non-empty values")
    if len(set(out)) != len(out):
        raise ValueError(f"{name} must contain unique values")
    return out


def _sem(values: np.ndarray) -> float:
    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]
    if len(finite) >= 2:
        return float(np.std(finite, ddof=1) / np.sqrt(len(finite)))
    if len(finite) == 1:
        return 0.0
    return float("nan")


def _fit_predict_truth(
    train: pd.DataFrame,
    test: pd.DataFrame,
    y_train: np.ndarray,
    predictors: tuple[str, ...],
    *,
    max_iter: int,
    max_leaf_nodes: int,
    min_samples_leaf: int,
    learning_rate: float,
    l2_regularization: float,
) -> np.ndarray:
    if not predictors:
        return np.full(len(test), float(np.mean(y_train)), dtype=float)

    x_train = train.loc[:, list(predictors)].apply(pd.to_numeric, errors="coerce").to_numpy(float)
    x_test = test.loc[:, list(predictors)].apply(pd.to_numeric, errors="coerce").to_numpy(float)
    if not np.isfinite(x_train).all() or not np.isfinite(x_test).all():
        raise ValueError("oracle predictors must be finite")
    if not np.isfinite(y_train).all():
        raise ValueError("oracle truth target must be finite")

    model = HistGradientBoostingRegressor(
        loss="squared_error",
        learning_rate=float(learning_rate),
        max_iter=int(max_iter),
        max_leaf_nodes=int(max_leaf_nodes),
        min_samples_leaf=int(min_samples_leaf),
        l2_regularization=float(l2_regularization),
        early_stopping=False,
        random_state=0,
    )
    model.fit(x_train, y_train)
    pred = np.asarray(model.predict(x_test), dtype=float)
    lo = float(np.min(y_train))
    hi = float(np.max(y_train))
    if hi > lo:
        pred = np.clip(pred, lo, hi)
    return pred


def oracle_process_identifiability(
    environment: pd.DataFrame,
    true_suitability: Sequence[float] | np.ndarray,
    spatial_groups: Sequence[object] | np.ndarray,
    process_registry: pd.DataFrame,
    *,
    predictor_universe: Sequence[str],
    process_universe: Sequence[str],
    n_splits: int = 5,
    relative_loss_margin: float = 0.02,
    sem_multiplier: float = 1.0,
    baseline_r2_floor: float = 0.80,
    required_r2_ceiling: float = 0.0,
    max_iter: int = 200,
    max_leaf_nodes: int = 31,
    min_samples_leaf: int = 20,
    learning_rate: float = 0.08,
    l2_regularization: float = 1e-3,
) -> OracleProcessIdentifiability:
    """Estimate process-information identifiability against the true surface.

    Per spatial fold, a flexible deterministic oracle regressor reconstructs the
    true suitability surface from (a) the full declared predictor system and (b)
    the same system after removing the complete closure of each process. The
    primary loss is the paired drop in held-out R2:

        delta_p = R2_full - R2_without_process_p.

    Status rules are prospective-friendly and set-valued:

    - ``oracle_required``: process-free reconstruction does not beat a constant
      predictor at the upper one-SEM bound and the paired loss exceeds margin;
    - ``oracle_contributory``: the lower paired-loss bound exceeds margin;
    - ``oracle_replaceable``: the upper paired-loss bound is at or below margin;
    - ``oracle_contested``: the uncertainty interval crosses the margin;
    - ``oracle_unavailable``: baseline truth reconstruction is itself inadequate
      or the CV evidence is incomplete.

    These labels are conditional on the declared predictor/process system and the
    frozen oracle function class. They are not causal or physiological truth.
    """
    predictors = _clean_unique(predictor_universe, name="predictor_universe")
    processes = _clean_unique(process_universe, name="process_universe")
    if int(n_splits) < 2:
        raise ValueError("n_splits must be >= 2")
    if not 0.0 <= float(relative_loss_margin) <= 1.0:
        raise ValueError("relative_loss_margin must be in [0, 1]")
    if float(sem_multiplier) < 0:
        raise ValueError("sem_multiplier must be >= 0")
    if not -1.0 <= float(baseline_r2_floor) <= 1.0:
        raise ValueError("baseline_r2_floor must be in [-1, 1]")
    if not -1.0 <= float(required_r2_ceiling) <= 1.0:
        raise ValueError("required_r2_ceiling must be in [-1, 1]")

    missing = sorted(set(predictors) - set(environment.columns))
    if missing:
        raise KeyError("environment missing oracle predictors: " + ", ".join(missing))
    y = np.asarray(true_suitability, dtype=float)
    groups = np.asarray(spatial_groups)
    if y.ndim != 1 or len(y) != len(environment):
        raise ValueError("true_suitability must align with environment rows")
    if len(groups) != len(environment):
        raise ValueError("spatial_groups must align with environment rows")
    if not np.isfinite(y).all():
        raise ValueError("true_suitability must be finite")
    if len(np.unique(groups)) < int(n_splits):
        raise ValueError("insufficient spatial groups for oracle CV")

    registry = normalize_process_information_registry(
        process_registry.copy(deep=True),
        process_universe=processes,
        predictor_universe=predictors,
    )
    splitter = GroupKFold(n_splits=int(n_splits))
    fold_rows: list[dict[str, object]] = []

    index = np.arange(len(environment))
    for fold, (train_idx, test_idx) in enumerate(splitter.split(index, groups=groups)):
        train = environment.iloc[train_idx].reset_index(drop=True)
        test = environment.iloc[test_idx].reset_index(drop=True)
        y_train = y[train_idx]
        y_test = y[test_idx]
        try:
            baseline_pred = _fit_predict_truth(
                train,
                test,
                y_train,
                predictors,
                max_iter=max_iter,
                max_leaf_nodes=max_leaf_nodes,
                min_samples_leaf=min_samples_leaf,
                learning_rate=learning_rate,
                l2_regularization=l2_regularization,
            )
            baseline_r2 = float(r2_score(y_test, baseline_pred))
            baseline_complete = bool(np.isfinite(baseline_r2))
        except (ValueError, KeyError, np.linalg.LinAlgError):
            baseline_r2 = float("nan")
            baseline_complete = False

        fold_rows.append(
            {
                "fold": int(fold),
                "route_type": "baseline",
                "process": "",
                "retained_predictors": ",".join(predictors),
                "complete": baseline_complete,
                "truth_surface_r2": baseline_r2,
                "paired_r2_loss": 0.0 if baseline_complete else float("nan"),
            }
        )

        for process in processes:
            excluded = set(
                registry.loc[registry["process"].astype(str).eq(process), "predictor"].astype(str)
            )
            retained = tuple(x for x in predictors if x not in excluded)
            try:
                if not baseline_complete:
                    raise ValueError("baseline oracle unavailable")
                knockout_pred = _fit_predict_truth(
                    train,
                    test,
                    y_train,
                    retained,
                    max_iter=max_iter,
                    max_leaf_nodes=max_leaf_nodes,
                    min_samples_leaf=min_samples_leaf,
                    learning_rate=learning_rate,
                    l2_regularization=l2_regularization,
                )
                knockout_r2 = float(r2_score(y_test, knockout_pred))
                complete = bool(np.isfinite(knockout_r2))
                loss = float(baseline_r2 - knockout_r2) if complete else float("nan")
            except (ValueError, KeyError, np.linalg.LinAlgError):
                knockout_r2 = float("nan")
                loss = float("nan")
                complete = False
            fold_rows.append(
                {
                    "fold": int(fold),
                    "route_type": "process_exclusion",
                    "process": process,
                    "retained_predictors": ",".join(retained),
                    "complete": complete,
                    "truth_surface_r2": knockout_r2,
                    "paired_r2_loss": loss,
                }
            )

    evidence = pd.DataFrame(fold_rows)
    baseline = evidence.loc[evidence["route_type"].eq("baseline")].copy()
    baseline_values = pd.to_numeric(baseline["truth_surface_r2"], errors="coerce").to_numpy(float)
    baseline_complete = bool(
        len(baseline) == int(n_splits)
        and baseline["complete"].astype(bool).all()
        and np.isfinite(baseline_values).all()
    )
    baseline_mean = float(np.mean(baseline_values)) if baseline_complete else float("nan")
    baseline_sem = _sem(baseline_values) if baseline_complete else float("nan")
    baseline_lower = (
        baseline_mean - float(sem_multiplier) * baseline_sem
        if np.isfinite(baseline_mean) and np.isfinite(baseline_sem)
        else float("nan")
    )
    baseline_adequate = bool(
        baseline_complete
        and np.isfinite(baseline_lower)
        and baseline_lower >= float(baseline_r2_floor)
    )
    baseline_summary = pd.DataFrame(
        [
            {
                "complete": baseline_complete,
                "mean_truth_surface_r2": baseline_mean,
                "sem_truth_surface_r2": baseline_sem,
                "lower_truth_surface_r2": baseline_lower,
                "baseline_adequate": baseline_adequate,
                "n_folds": int(len(baseline)),
            }
        ]
    )

    process_rows: list[dict[str, object]] = []
    for process in processes:
        group = evidence.loc[
            evidence["route_type"].eq("process_exclusion")
            & evidence["process"].astype(str).eq(process)
        ].copy()
        r2 = pd.to_numeric(group["truth_surface_r2"], errors="coerce").to_numpy(float)
        loss = pd.to_numeric(group["paired_r2_loss"], errors="coerce").to_numpy(float)
        complete = bool(
            len(group) == int(n_splits)
            and group["complete"].astype(bool).all()
            and np.isfinite(r2).all()
            and np.isfinite(loss).all()
        )
        mean_r2 = float(np.mean(r2)) if complete else float("nan")
        sem_r2 = _sem(r2) if complete else float("nan")
        upper_r2 = (
            mean_r2 + float(sem_multiplier) * sem_r2
            if np.isfinite(mean_r2) and np.isfinite(sem_r2)
            else float("nan")
        )
        mean_loss = float(np.mean(loss)) if complete else float("nan")
        sem_loss = _sem(loss) if complete else float("nan")
        lower_loss = (
            mean_loss - float(sem_multiplier) * sem_loss
            if np.isfinite(mean_loss) and np.isfinite(sem_loss)
            else float("nan")
        )
        upper_loss = (
            mean_loss + float(sem_multiplier) * sem_loss
            if np.isfinite(mean_loss) and np.isfinite(sem_loss)
            else float("nan")
        )

        if not baseline_adequate or not complete:
            status = ORACLE_UNAVAILABLE
        elif upper_r2 <= float(required_r2_ceiling) and lower_loss > float(relative_loss_margin):
            status = ORACLE_REQUIRED
        elif lower_loss > float(relative_loss_margin):
            status = ORACLE_CONTRIBUTORY
        elif upper_loss <= float(relative_loss_margin):
            status = ORACLE_REPLACEABLE
        else:
            status = ORACLE_CONTESTED

        process_rows.append(
            {
                "process": process,
                "oracle_status": status,
                "oracle_identifiable_signal": status in {ORACLE_CONTRIBUTORY, ORACLE_REQUIRED},
                "complete": complete,
                "mean_process_free_r2": mean_r2,
                "sem_process_free_r2": sem_r2,
                "upper_process_free_r2": upper_r2,
                "mean_paired_r2_loss": mean_loss,
                "sem_paired_r2_loss": sem_loss,
                "lower_paired_r2_loss": lower_loss,
                "upper_paired_r2_loss": upper_loss,
                "n_folds": int(len(group)),
            }
        )
    process_summary = pd.DataFrame(process_rows)

    receipt_payload = "\n".join(
        [
            "predictors=" + ",".join(predictors),
            "processes=" + ",".join(processes),
            "registry=" + registry.to_csv(index=False),
            f"n_splits={int(n_splits)}",
            f"relative_loss_margin={float(relative_loss_margin):.12g}",
            f"sem_multiplier={float(sem_multiplier):.12g}",
            f"baseline_r2_floor={float(baseline_r2_floor):.12g}",
            f"required_r2_ceiling={float(required_r2_ceiling):.12g}",
            f"max_iter={int(max_iter)}",
            f"max_leaf_nodes={int(max_leaf_nodes)}",
            f"min_samples_leaf={int(min_samples_leaf)}",
            f"learning_rate={float(learning_rate):.12g}",
            f"l2_regularization={float(l2_regularization):.12g}",
            "oracle_status=" + process_summary[["process", "oracle_status"]].to_csv(index=False),
        ]
    )
    receipt = hashlib.sha256(receipt_payload.encode("utf-8")).hexdigest()
    return OracleProcessIdentifiability(
        predictor_universe=predictors,
        process_universe=processes,
        fold_evidence=evidence,
        baseline_summary=baseline_summary,
        process_summary=process_summary,
        relative_loss_margin=float(relative_loss_margin),
        sem_multiplier=float(sem_multiplier),
        baseline_r2_floor=float(baseline_r2_floor),
        required_r2_ceiling=float(required_r2_ceiling),
        selection_receipt=receipt,
    )
