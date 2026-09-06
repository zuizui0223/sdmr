import numpy as np
import pandas as pd

import sdmr.oracle_process_identifiability as oracle_module
from sdmr.oracle_process_identifiability import (
    ORACLE_CONTESTED,
    ORACLE_CONTRIBUTORY,
    ORACLE_REPLACEABLE,
    ORACLE_REQUIRED,
    ORACLE_UNAVAILABLE,
    oracle_process_identifiability,
)


def _environment() -> tuple[pd.DataFrame, np.ndarray, np.ndarray, pd.DataFrame]:
    within_group = np.linspace(-1.0, 1.0, 20)
    truth = np.tile(within_group, 5)
    groups = np.repeat(np.arange(5), len(within_group))
    env = pd.DataFrame(
        {
            "p": np.tile(np.linspace(-2.0, 2.0, 20), 5),
            "q": np.tile(np.linspace(2.0, -2.0, 20), 5),
            "r": np.sin(np.linspace(0.0, 5.0, len(truth))),
            "s": np.cos(np.linspace(0.0, 5.0, len(truth))),
            "_truth": truth,
            "_group": groups,
        }
    )
    registry = pd.DataFrame(
        [
            {"predictor": "p", "process": "p_process", "role": "direct"},
            {"predictor": "q", "process": "q_process", "role": "direct"},
            {"predictor": "r", "process": "r_process", "role": "direct"},
            {"predictor": "s", "process": "s_process", "role": "direct"},
        ]
    )
    return env, truth, groups, registry


def test_oracle_separates_required_contributory_replaceable_and_contested(monkeypatch) -> None:
    env, truth, groups, registry = _environment()
    full = ("p", "q", "r", "s")

    def fake_truth_fit(train, test, y_train, predictors, **kwargs):
        y = test["_truth"].to_numpy(float)
        removed = set(full) - set(predictors)
        if not removed:
            return y
        if removed == {"p"}:
            # Exactly constant at the fold truth mean (zero): no held-out truth
            # information remains once p_process is removed.
            return np.zeros(len(test), dtype=float)
        if removed == {"q"}:
            # q_process is perfectly replaceable under the declared predictor
            # system.
            return y
        if removed == {"r"}:
            # Positive but materially degraded truth reconstruction.
            return 0.70 * y
        if removed == {"s"}:
            # Fold-varying loss straddles the 0.02 oracle margin.
            group = int(test["_group"].iloc[0])
            factor = (0.75, 0.80, 0.85, 0.90, 0.95)[group]
            return factor * y
        raise AssertionError(f"unexpected predictor set: {predictors}")

    monkeypatch.setattr(oracle_module, "_fit_predict_truth", fake_truth_fit)
    result = oracle_process_identifiability(
        env,
        truth,
        groups,
        registry,
        predictor_universe=full,
        process_universe=("p_process", "q_process", "r_process", "s_process"),
        n_splits=5,
        relative_loss_margin=0.02,
        sem_multiplier=1.0,
        baseline_r2_floor=0.80,
        required_r2_ceiling=0.0,
    )
    by_process = result.process_summary.set_index("process")

    assert by_process.loc["p_process", "oracle_status"] == ORACLE_REQUIRED
    assert by_process.loc["q_process", "oracle_status"] == ORACLE_REPLACEABLE
    assert by_process.loc["r_process", "oracle_status"] == ORACLE_CONTRIBUTORY
    assert by_process.loc["s_process", "oracle_status"] == ORACLE_CONTESTED
    assert bool(by_process.loc["p_process", "oracle_identifiable_signal"])
    assert bool(by_process.loc["r_process", "oracle_identifiable_signal"])
    assert not bool(by_process.loc["q_process", "oracle_identifiable_signal"])
    assert not bool(by_process.loc["s_process", "oracle_identifiable_signal"])


def test_oracle_is_unavailable_when_full_predictor_system_cannot_reconstruct_truth(monkeypatch) -> None:
    env, truth, groups, registry = _environment()
    full = ("p", "q", "r", "s")

    def weak_truth_fit(train, test, y_train, predictors, **kwargs):
        # Every route, including the full predictor system, misses the truth
        # surface enough to fail the oracle baseline floor.
        return 0.5 * test["_truth"].to_numpy(float)

    monkeypatch.setattr(oracle_module, "_fit_predict_truth", weak_truth_fit)
    result = oracle_process_identifiability(
        env,
        truth,
        groups,
        registry,
        predictor_universe=full,
        process_universe=("p_process", "q_process", "r_process", "s_process"),
        n_splits=5,
        baseline_r2_floor=0.90,
    )

    assert not bool(result.baseline_summary.iloc[0]["baseline_adequate"])
    assert set(result.process_summary["oracle_status"]) == {ORACLE_UNAVAILABLE}


def test_oracle_inputs_do_not_include_generating_process_membership(monkeypatch) -> None:
    env, truth, groups, registry = _environment()
    env_before = env.copy(deep=True)
    registry_before = registry.copy(deep=True)

    def exact_truth_fit(train, test, y_train, predictors, **kwargs):
        return test["_truth"].to_numpy(float)

    monkeypatch.setattr(oracle_module, "_fit_predict_truth", exact_truth_fit)
    oracle_process_identifiability(
        env,
        truth,
        groups,
        registry,
        predictor_universe=("p", "q", "r", "s"),
        process_universe=("p_process", "q_process", "r_process", "s_process"),
        n_splits=5,
    )

    # The oracle consumes the true suitability surface, not a label saying which
    # process generated it; and it must not mutate the frozen predictor contract.
    assert "expected_true_process" not in env.columns
    assert "generating_process" not in env.columns
    pd.testing.assert_frame_equal(env, env_before)
    pd.testing.assert_frame_equal(registry, registry_before)
