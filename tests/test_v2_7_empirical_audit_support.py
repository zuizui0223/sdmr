import numpy as np
import pandas as pd
import pytest

from sdmr.v2_7_empirical_audit_support import (
    _complete_count,
    audit_support_ledger,
    select_partition_aware_empirical_audit_space,
)
from sdmr.validation import SpatialPartition


def _partition(p_groups, b_groups):
    return SpatialPartition(
        presence_blocks=np.asarray(p_groups, dtype=int),
        background_blocks=np.asarray(b_groups, dtype=int),
        train_blocks=(0, 1, 2),
        test_blocks=(3,),
        centers_xyz=np.zeros((4, 3), dtype=float),
    )


def test_process_representative_space_avoids_43_variable_complete_case_collapse():
    processes = ("thermal", "water", "seasonality", "energy", "snow", "wind")
    predictors = [f"x{i:02d}" for i in range(43)]
    process = [processes[i % len(processes)] for i in range(43)]
    manifest = pd.DataFrame({"predictor": predictors, "process": process})
    # Make exactly one deterministic representative per process fully observed.
    representatives = {proc: predictors[process.index(proc)] for proc in processes}

    def frame(n):
        data = pd.DataFrame({name: np.arange(n, dtype=float) for name in predictors})
        non_reps = [name for name in predictors if name not in set(representatives.values())]
        # Spread one missing value per non-representative so the 43-variable
        # complete-case intersection collapses, while each process has one fully
        # observed representative.
        for i, name in enumerate(non_reps):
            data.loc[i % n, name] = np.nan
        return data

    occurrence = frame(24)
    backgrounds = {name: frame(48) for name in ("m150", "m300", "m500")}
    p_groups = np.repeat(np.arange(4), 6)
    b_groups = np.repeat(np.arange(4), 12)
    partitions = {name: _partition(p_groups, b_groups) for name in backgrounds}

    assert _complete_count(backgrounds["m150"], predictors) == 0
    result = select_partition_aware_empirical_audit_space(
        manifest,
        occurrence,
        backgrounds,
        partitions,
        outer_folds=4,
        minimum_predictor_coverage=0.95,
        minimum_joint_coverage=0.80,
        minimum_processes=4,
    )
    assert set(result.predictors) == set(representatives.values())
    assert set(result.processes) == set(processes)
    assert result.support_ledger["audit_support_complete"].all()
    assert result.support_ledger["n_complete_fit_background"].min() >= 5
    assert result.support_ledger["n_complete_evaluation_background"].min() >= 5
    assert result.support_ledger["n_complete_heldout_occurrences"].min() >= 2


def test_partition_support_prunes_process_axis_with_spatially_concentrated_missingness():
    predictors = ["thermal", "water", "seasonality", "energy", "snow"]
    manifest = pd.DataFrame({"predictor": predictors, "process": predictors})
    # Four spatial groups; group 0 has only two occurrences.  Snow is missing in
    # exactly one of those rows: 95% overall occurrence coverage, but only one
    # complete held-out occurrence when group 0 is the test fold.
    p_groups = np.asarray([0, 0, *([1] * 6), *([2] * 6), *([3] * 6)], dtype=int)
    occurrence = pd.DataFrame({name: np.arange(len(p_groups), dtype=float) for name in predictors})
    occurrence.loc[0, "snow"] = np.nan
    b_groups = np.repeat(np.arange(4), 10)
    backgrounds = {
        name: pd.DataFrame({p: np.arange(len(b_groups), dtype=float) for p in predictors})
        for name in ("m150", "m300", "m500")
    }
    partitions = {name: _partition(p_groups, b_groups) for name in backgrounds}

    initial_support = audit_support_ledger(
        occurrence,
        backgrounds,
        partitions,
        predictors,
        outer_folds=4,
    )
    assert not initial_support["audit_support_complete"].all()
    assert initial_support["n_complete_heldout_occurrences"].min() == 1

    result = select_partition_aware_empirical_audit_space(
        manifest,
        occurrence,
        backgrounds,
        partitions,
        outer_folds=4,
        minimum_predictor_coverage=0.95,
        minimum_joint_coverage=0.80,
        minimum_processes=4,
    )
    assert set(result.initial_predictors) == set(predictors)
    assert set(result.predictors) == {"thermal", "water", "seasonality", "energy"}
    removed = result.pruning_ledger.loc[
        result.pruning_ledger["action"].eq("remove_process_axis"), "removed_predictor"
    ].dropna().tolist()
    assert removed == ["snow"]
    assert result.support_ledger["audit_support_complete"].all()


def test_partition_support_abstains_when_minimum_four_processes_still_cannot_support_recovery():
    predictors = ["thermal", "water", "seasonality", "snow"]
    manifest = pd.DataFrame({"predictor": predictors, "process": predictors})
    p_groups = np.asarray([0, 0, *([1] * 6), *([2] * 6), *([3] * 6)], dtype=int)
    occurrence = pd.DataFrame({name: np.arange(len(p_groups), dtype=float) for name in predictors})
    occurrence.loc[0, "snow"] = np.nan
    b_groups = np.repeat(np.arange(4), 10)
    backgrounds = {
        name: pd.DataFrame({p: np.arange(len(b_groups), dtype=float) for p in predictors})
        for name in ("m150", "m300", "m500")
    }
    partitions = {name: _partition(p_groups, b_groups) for name in backgrounds}
    with pytest.raises(ValueError, match="cannot support the minimum 4 ecological audit processes"):
        select_partition_aware_empirical_audit_space(
            manifest,
            occurrence,
            backgrounds,
            partitions,
            outer_folds=4,
            minimum_predictor_coverage=0.95,
            minimum_joint_coverage=0.80,
            minimum_processes=4,
        )


def test_audit_selection_is_independent_of_candidate_score_columns():
    manifest = pd.DataFrame(
        {
            "predictor": ["thermal", "water", "seasonality", "energy"],
            "process": ["thermal", "water", "seasonality", "energy"],
            "candidate_score": [1000.0, -1000.0, 7.0, 0.0],
        }
    )
    p_groups = np.repeat(np.arange(4), 4)
    b_groups = np.repeat(np.arange(4), 8)
    occurrence = pd.DataFrame({p: np.arange(16, dtype=float) for p in manifest["predictor"]})
    backgrounds = {
        name: pd.DataFrame({p: np.arange(32, dtype=float) for p in manifest["predictor"]})
        for name in ("m150", "m300", "m500")
    }
    partitions = {name: _partition(p_groups, b_groups) for name in backgrounds}
    first = select_partition_aware_empirical_audit_space(
        manifest,
        occurrence,
        backgrounds,
        partitions,
        outer_folds=4,
        minimum_processes=4,
    )
    changed = manifest.copy(); changed["candidate_score"] *= -999999
    second = select_partition_aware_empirical_audit_space(
        changed,
        occurrence,
        backgrounds,
        partitions,
        outer_folds=4,
        minimum_processes=4,
    )
    assert first.predictors == second.predictors
    assert first.processes == second.processes
