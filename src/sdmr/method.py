"""Within-species Product-A method tuning with sealed answer-check occurrences."""

from __future__ import annotations
from collections.abc import Sequence
from dataclasses import dataclass
import numpy as np
import pandas as pd
from .baselines import vif_prune_predictors
from .importance import drop_one_importance
from .model import ModelSpec, evaluate_predictor_set
from .selection import cross_validated_score, forward_select_predictors
from .validation import make_spatial_partition


@dataclass(frozen=True)
class FrozenProtocol:
    strategy: str
    predictors: tuple[str, ...]
    model_spec: ModelSpec
    inner_score: float


@dataclass
class SpeciesMethodBenchmarkResult:
    species: str
    protocols: dict[str, FrozenProtocol]
    tuning_grid: pd.DataFrame
    sealed_metrics: pd.DataFrame
    random_baseline: pd.DataFrame
    drop_one: pd.DataFrame
    train_blocks: tuple[int, ...]
    test_blocks: tuple[int, ...]


def _default_model_specs() -> list[ModelSpec]:
    return [ModelSpec(C=c, degree=d, penalty=p) for d in (1, 2) for p in ("l1", "l2") for c in (0.1, 1.0, 10.0)]


def _better(candidate: FrozenProtocol, current: FrozenProtocol | None) -> bool:
    if not candidate.predictors or not np.isfinite(candidate.inner_score):
        return False
    if current is None or candidate.inner_score > current.inner_score + 1e-12:
        return True
    if abs(candidate.inner_score - current.inner_score) <= 1e-12:
        if len(candidate.predictors) != len(current.predictors):
            return len(candidate.predictors) < len(current.predictors)
        a = (candidate.model_spec.degree, candidate.model_spec.C, candidate.model_spec.penalty)
        b = (current.model_spec.degree, current.model_spec.C, current.model_spec.penalty)
        return a < b
    return False


def freeze_candidate_methods(
    model_presence: pd.DataFrame,
    model_background: pd.DataFrame,
    presence_groups: np.ndarray,
    background_groups: np.ndarray,
    candidate_predictors: Sequence[str],
    *,
    model_specs: Sequence[ModelSpec] | None = None,
    inner_folds: int = 4,
    min_gain: float = 0.005,
    max_predictors: int | None = 8,
    vif_threshold: float = 5.0,
) -> tuple[dict[str, FrozenProtocol], pd.DataFrame]:
    """Tune all choices inside the model pool; sealed occurrences are absent."""
    specs = list(model_specs or _default_model_specs())
    if not specs:
        raise ValueError("At least one ModelSpec is required.")
    vif_predictors, _ = vif_prune_predictors(model_background, candidate_predictors, threshold=vif_threshold)
    best: dict[str, FrozenProtocol] = {}
    rows = []
    for spec in specs:
        strategy_sets = {"all": list(candidate_predictors), "vif": list(vif_predictors)}
        try:
            selected, _, _ = forward_select_predictors(
                model_presence, model_background, presence_groups, background_groups,
                candidate_predictors, inner_folds=inner_folds, min_gain=min_gain,
                max_predictors=max_predictors, model_spec=spec,
            )
            strategy_sets["predictive"] = selected
        except ValueError:
            strategy_sets["predictive"] = []
        for strategy, predictors in strategy_sets.items():
            score = float("nan") if not predictors else cross_validated_score(
                model_presence, model_background, presence_groups, background_groups,
                predictors, n_splits=inner_folds, model_spec=spec,
            )
            protocol = FrozenProtocol(strategy, tuple(predictors), spec, float(score))
            rows.append({
                "strategy": strategy, "model": spec.label, "C": spec.C,
                "degree": spec.degree, "penalty": spec.penalty,
                "n_predictors": len(predictors), "predictors": ",".join(predictors),
                "inner_presence_rank": score,
            })
            if _better(protocol, best.get(strategy)):
                best[strategy] = protocol
    return best, pd.DataFrame(rows)


def _subset_species(frame: pd.DataFrame, species_name: str, species_col: str) -> pd.DataFrame:
    if species_col not in frame.columns:
        return frame.reset_index(drop=True)
    return frame.loc[frame[species_col].astype(str) == str(species_name)].reset_index(drop=True)


def benchmark_species_methods(
    occurrences: pd.DataFrame,
    background: pd.DataFrame,
    candidate_predictors: Sequence[str],
    *,
    species_name: str = "species",
    species_col: str = "species",
    lon_col: str = "longitude",
    lat_col: str = "latitude",
    sealed_fraction: float = 0.20,
    n_spatial_blocks: int = 8,
    inner_folds: int = 4,
    min_gain: float = 0.005,
    max_predictors: int | None = 8,
    vif_threshold: float = 5.0,
    model_specs: Sequence[ModelSpec] | None = None,
    random_repeats: int = 20,
    compute_drop_one: bool = True,
    random_state: int = 42,
) -> SpeciesMethodBenchmarkResult:
    """Freeze each candidate method, then open one sealed spatial test set."""
    p = _subset_species(occurrences, species_name, species_col)
    b = _subset_species(background, species_name, species_col)
    if len(p) < 12:
        raise ValueError(f"{species_name}: too few occurrences ({len(p)}) for method benchmarking.")
    part = make_spatial_partition(
        p[lon_col].to_numpy(float), p[lat_col].to_numpy(float),
        b[lon_col].to_numpy(float), b[lat_col].to_numpy(float),
        n_blocks=n_spatial_blocks, holdout_fraction=sealed_fraction,
        random_state=random_state,
    )
    p_tr = np.isin(part.presence_blocks, part.train_blocks)
    p_te = np.isin(part.presence_blocks, part.test_blocks)
    b_tr = np.isin(part.background_blocks, part.train_blocks)
    b_te = np.isin(part.background_blocks, part.test_blocks)
    p_model, p_test = p.loc[p_tr].reset_index(drop=True), p.loc[p_te].reset_index(drop=True)
    b_model, b_test = b.loc[b_tr].reset_index(drop=True), b.loc[b_te].reset_index(drop=True)
    protocols, grid = freeze_candidate_methods(
        p_model, b_model, part.presence_blocks[p_tr], part.background_blocks[b_tr],
        candidate_predictors, model_specs=model_specs, inner_folds=inner_folds,
        min_gain=min_gain, max_predictors=max_predictors, vif_threshold=vif_threshold,
    )
    if not protocols:
        raise ValueError(f"{species_name}: no candidate method could be frozen.")
    sealed_rows, drop_frames = [], []
    for strategy, protocol in protocols.items():
        metrics = evaluate_predictor_set(
            p_model, b_model, p_test, b_test, protocol.predictors,
            model_spec=protocol.model_spec,
        )
        sealed_rows.append({
            "species": str(species_name), "strategy": strategy,
            "model": protocol.model_spec.label, "inner_presence_rank": protocol.inner_score,
            "n_predictors": len(protocol.predictors), "predictors": ",".join(protocol.predictors),
            **metrics,
        })
        if compute_drop_one:
            imp = drop_one_importance(
                p_model, b_model, p_test, b_test, protocol.predictors,
                model_spec=protocol.model_spec,
            )
            if len(imp):
                drop_frames.append(imp.assign(species=str(species_name), strategy=strategy, model=protocol.model_spec.label))
    random_rows = []
    predictive = protocols.get("predictive")
    if predictive is not None and random_repeats > 0:
        rng = np.random.default_rng(random_state + 100_000)
        candidates = np.array(list(dict.fromkeys(candidate_predictors)), dtype=object)
        size = max(1, min(len(predictive.predictors), len(candidates)))
        for repeat in range(int(random_repeats)):
            chosen = sorted(str(x) for x in rng.choice(candidates, size=size, replace=False))
            metrics = evaluate_predictor_set(p_model, b_model, p_test, b_test, chosen, model_spec=predictive.model_spec)
            random_rows.append({
                "species": str(species_name), "repeat": repeat,
                "model": predictive.model_spec.label, "n_predictors": size,
                "predictors": ",".join(chosen), **metrics,
            })
    return SpeciesMethodBenchmarkResult(
        str(species_name), protocols, grid.assign(species=str(species_name)),
        pd.DataFrame(sealed_rows), pd.DataFrame(random_rows),
        pd.concat(drop_frames, ignore_index=True) if drop_frames else pd.DataFrame(),
        part.train_blocks, part.test_blocks,
    )
