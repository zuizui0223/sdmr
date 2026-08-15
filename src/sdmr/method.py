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


OUTER_ROLE_COL = "__sdmr_outer_role"
OUTER_BLOCK_COL = "__sdmr_outer_block"
MODEL_ROLE = "model"
SEALED_ROLE = "sealed"


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
    predictive_selection: pd.DataFrame
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


def _preassigned_outer_split(
    presence: pd.DataFrame,
    background: pd.DataFrame,
    *,
    species_name: str,
    lon_col: str,
    lat_col: str,
    n_spatial_blocks: int,
    random_state: int,
):
    """Use a split fixed before M/background construction.

    Inner spatial groups are rebuilt *only from model-pool rows*.  Sealed
    occurrence coordinates therefore do not influence fitting groups, M,
    background construction, predictor selection, or model tuning.
    """

    p_roles = presence[OUTER_ROLE_COL].astype(str)
    b_roles = background[OUTER_ROLE_COL].astype(str)
    invalid_p = set(p_roles) - {MODEL_ROLE, SEALED_ROLE}
    invalid_b = set(b_roles) - {MODEL_ROLE, SEALED_ROLE}
    if invalid_p or invalid_b:
        raise ValueError(
            f"{species_name}: invalid preassigned outer roles: presence={sorted(invalid_p)}, background={sorted(invalid_b)}"
        )

    p_model = presence.loc[p_roles == MODEL_ROLE].reset_index(drop=True)
    p_test = presence.loc[p_roles == SEALED_ROLE].reset_index(drop=True)
    b_model = background.loc[b_roles == MODEL_ROLE].reset_index(drop=True)
    b_test = background.loc[b_roles == SEALED_ROLE].reset_index(drop=True)
    if len(p_model) < 4 or len(p_test) < 1:
        raise ValueError(f"{species_name}: preassigned occurrence split lacks model/sealed rows")
    if len(b_model) < 2 or len(b_test) < 2:
        raise ValueError(f"{species_name}: preassigned background split lacks model/sealed-reference rows")

    # We need group labels for inner CV, not another outer test.  This partition
    # sees model-pool occurrence/background rows only; its train/test labels are
    # deliberately ignored.
    inner = make_spatial_partition(
        p_model[lon_col].to_numpy(float),
        p_model[lat_col].to_numpy(float),
        b_model[lon_col].to_numpy(float),
        b_model[lat_col].to_numpy(float),
        n_blocks=n_spatial_blocks,
        holdout_fraction=0.20,
        random_state=random_state + 500_000,
    )

    if OUTER_BLOCK_COL in presence:
        train_blocks = tuple(sorted(int(x) for x in pd.unique(
            pd.to_numeric(p_model[OUTER_BLOCK_COL], errors="raise")
        )))
        test_blocks = tuple(sorted(int(x) for x in pd.unique(
            pd.to_numeric(p_test[OUTER_BLOCK_COL], errors="raise")
        )))
    else:
        train_blocks = tuple()
        test_blocks = tuple()
    return (
        p_model,
        p_test,
        b_model,
        b_test,
        inner.presence_blocks,
        inner.background_blocks,
        train_blocks,
        test_blocks,
    )


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
    """Freeze each candidate method, then open one sealed spatial test set.

    If ``__sdmr_outer_role`` is present on both occurrence and background
    tables, that upstream split is authoritative.  It was fixed before M and
    background construction and must not be silently replaced here.
    """
    p = _subset_species(occurrences, species_name, species_col)
    b = _subset_species(background, species_name, species_col)
    if len(p) < 12:
        raise ValueError(f"{species_name}: too few occurrences ({len(p)}) for method benchmarking.")

    preassigned = OUTER_ROLE_COL in p.columns or OUTER_ROLE_COL in b.columns
    if preassigned:
        if OUTER_ROLE_COL not in p.columns or OUTER_ROLE_COL not in b.columns:
            raise ValueError(f"{species_name}: outer role must be present on both occurrence and background tables")
        (
            p_model,
            p_test,
            b_model,
            b_test,
            model_presence_groups,
            model_background_groups,
            train_blocks,
            test_blocks,
        ) = _preassigned_outer_split(
            p,
            b,
            species_name=species_name,
            lon_col=lon_col,
            lat_col=lat_col,
            n_spatial_blocks=n_spatial_blocks,
            random_state=random_state,
        )
    else:
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
        model_presence_groups = part.presence_blocks[p_tr]
        model_background_groups = part.background_blocks[b_tr]
        train_blocks = part.train_blocks
        test_blocks = part.test_blocks

    protocols, grid = freeze_candidate_methods(
        p_model, b_model, model_presence_groups, model_background_groups,
        candidate_predictors, model_specs=model_specs, inner_folds=inner_folds,
        min_gain=min_gain, max_predictors=max_predictors, vif_threshold=vif_threshold,
    )
    if not protocols:
        raise ValueError(f"{species_name}: no candidate method could be frozen.")

    predictive_selection = pd.DataFrame(
        columns=["species", "step", "predictor", "inner_presence_rank", "gain"]
    )
    predictive = protocols.get("predictive")
    if predictive is not None:
        selected_again, steps_again, _ = forward_select_predictors(
            p_model, b_model, model_presence_groups, model_background_groups,
            candidate_predictors, inner_folds=inner_folds, min_gain=min_gain,
            max_predictors=max_predictors, model_spec=predictive.model_spec,
        )
        if tuple(selected_again) != predictive.predictors:
            raise RuntimeError("Predictive selection was not reproducible after protocol freezing.")
        predictive_selection = pd.DataFrame(
            [
                {
                    "species": str(species_name),
                    "step": step.step,
                    "predictor": step.predictor,
                    "inner_presence_rank": step.score,
                    "gain": step.gain,
                }
                for step in steps_again
            ]
        )

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
            "outer_split_preassigned": bool(preassigned),
            "n_model_occurrences": len(p_model),
            "n_sealed_occurrences": len(p_test),
            "n_model_background": len(b_model),
            "n_sealed_background": len(b_test),
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
        species=str(species_name),
        protocols=protocols,
        tuning_grid=grid.assign(species=str(species_name)),
        sealed_metrics=pd.DataFrame(sealed_rows),
        random_baseline=pd.DataFrame(random_rows),
        drop_one=pd.concat(drop_frames, ignore_index=True) if drop_frames else pd.DataFrame(),
        predictive_selection=predictive_selection,
        train_blocks=train_blocks,
        test_blocks=test_blocks,
    )
