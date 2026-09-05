"""Ergonomic high-level workflow for ecological identification.

The low-level SDMR primitives remain available for audit-heavy workflows.  This
module provides a small, safe public surface for routine use:

1. freeze occurrence model-pool versus sealed answer-check roles from identities
   and coordinates only;
2. build or validate the prospectively declared predictor-process registry;
3. derive grouped inner spatial folds from model-pool occurrences and background;
4. fit the set-valued ecological-identification learner;
5. open the sealed answer-check only after the learner has emitted a selection
   receipt;
6. export a compact audit bundle for review or publication.

The workflow never learns process labels from the ecological outcome.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from collections.abc import Sequence
import hashlib
import json

import numpy as np
import pandas as pd

from .ecological_identification_learner import (
    IdentificationLearnerFit,
    fit_ecological_identification_learner,
)
from .model import ModelSpec
from .process_information_closure import normalize_process_information_registry
from .process_registry_proposal import (
    freeze_process_registry_proposal,
    propose_process_information_registry,
)
from .sealed_occurrence_contract import (
    OccurrenceAnswerCheckSplit,
    freeze_occurrence_answer_check_split,
)
from .validation import make_spatial_partition


DEFAULT_MODEL_SPECS = (
    ModelSpec(C=0.1, degree=1, random_state=0),
    ModelSpec(C=1.0, degree=1, random_state=0),
    ModelSpec(C=10.0, degree=1, random_state=0),
)


class ProcessRegistryReviewRequired(ValueError):
    """Raised when semi-automatic classification still needs human review.

    The full proposal is attached as ``proposal`` so interactive callers can
    display only the flagged rows rather than asking users to classify every
    predictor manually.
    """

    def __init__(self, proposal: pd.DataFrame):
        self.proposal = proposal.copy()
        flagged = self.proposal.loc[self.proposal["review_required"].astype(bool)]
        labels = [
            f"{row.predictor}:{row.status}"
            for row in flagged[["predictor", "status"]].drop_duplicates().itertuples(index=False)
        ]
        super().__init__(
            "process registry requires review before freezing: " + ", ".join(labels)
        )


@dataclass(frozen=True)
class EcologicalIdentificationConfig:
    """Frozen workflow settings for a single ecological-identification study."""

    id_col: str = "occurrence_id"
    lon_col: str = "longitude"
    lat_col: str = "latitude"
    outer_n_blocks: int = 8
    answer_check_fraction: float = 0.20
    outer_random_state: int = 42
    inner_n_blocks: int = 8
    inner_n_splits: int = 4
    inner_random_state: int = 73
    chance_score: float = 0.50
    minimum_margin: float = 0.01
    sem_multiplier: float = 1.0
    model_specs: tuple[ModelSpec, ...] = DEFAULT_MODEL_SPECS

    def __post_init__(self) -> None:
        for name in ("id_col", "lon_col", "lat_col"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} must be non-empty")
        if self.outer_n_blocks < 4:
            raise ValueError("outer_n_blocks must be >= 4")
        if not 0 < self.answer_check_fraction < 1:
            raise ValueError("answer_check_fraction must lie in (0, 1)")
        if self.inner_n_blocks < self.inner_n_splits:
            raise ValueError("inner_n_blocks must be >= inner_n_splits")
        if self.inner_n_splits < 2:
            raise ValueError("inner_n_splits must be >= 2")
        if not 0 <= self.chance_score < 1:
            raise ValueError("chance_score must lie in [0, 1)")
        if self.minimum_margin < 0 or self.chance_score + self.minimum_margin > 1:
            raise ValueError("minimum_margin produces an invalid adequacy floor")
        if self.sem_multiplier < 0:
            raise ValueError("sem_multiplier must be >= 0")
        labels = [spec.label for spec in self.model_specs]
        if not labels or len(labels) != len(set(labels)):
            raise ValueError("model_specs must contain unique non-empty model identities")

    def as_manifest(self) -> dict[str, object]:
        return {
            "id_col": self.id_col,
            "lon_col": self.lon_col,
            "lat_col": self.lat_col,
            "outer_n_blocks": int(self.outer_n_blocks),
            "answer_check_fraction": float(self.answer_check_fraction),
            "outer_random_state": int(self.outer_random_state),
            "inner_n_blocks": int(self.inner_n_blocks),
            "inner_n_splits": int(self.inner_n_splits),
            "inner_random_state": int(self.inner_random_state),
            "chance_score": float(self.chance_score),
            "minimum_margin": float(self.minimum_margin),
            "sem_multiplier": float(self.sem_multiplier),
            "model_specs": [spec.label for spec in self.model_specs],
        }


def _unique_nonempty(values: Sequence[str], *, name: str) -> tuple[str, ...]:
    result = tuple(dict.fromkeys(str(value).strip() for value in values))
    if not result or any(not value for value in result):
        raise ValueError(f"{name} must contain non-empty values")
    return result


def _direct_registry_proposal(registry: pd.DataFrame) -> pd.DataFrame:
    proposal = registry.copy()
    for column, default in (
        ("rule_ids", "declared"),
        ("match_basis", "direct_registry"),
        ("source_family", ""),
        ("units", ""),
    ):
        if column not in proposal.columns:
            proposal[column] = default
    proposal["status"] = "declared"
    proposal["review_required"] = False
    return proposal[
        [
            "predictor",
            "process",
            "role",
            "rule_ids",
            "match_basis",
            "source_family",
            "units",
            "status",
            "review_required",
        ]
    ].reset_index(drop=True)


@dataclass(frozen=True)
class PreparedEcologicalIdentificationStudy:
    """Frozen outer split and process taxonomy, ready for model-pool fitting."""

    config: EcologicalIdentificationConfig
    occurrence_split: OccurrenceAnswerCheckSplit
    registry_proposal: pd.DataFrame
    process_registry: pd.DataFrame
    predictors: tuple[str, ...]
    process_universe: tuple[str, ...]

    @property
    def model_pool_ids(self) -> tuple[str, ...]:
        return self.occurrence_split.model_pool_ids

    @property
    def answer_check_ids(self) -> tuple[str, ...]:
        return self.occurrence_split.answer_check_ids

    def fit(
        self,
        occurrence_features: pd.DataFrame,
        background_features: pd.DataFrame,
    ) -> "EcologicalIdentificationWorkflowFit":
        """Fit using model-pool occurrences only and automatic inner spatial groups.

        ``occurrence_features`` may contain both model-pool and sealed rows: the
        outer contract filters to model-pool identities before any learner call.
        Every frozen model-pool identity must be present. ``background_features``
        must already follow the study's prospectively frozen background/M recipe;
        this workflow cannot infer whether an externally prepared background was
        constructed from sealed occurrences.
        """

        cfg = self.config
        required_occurrence = {cfg.id_col, cfg.lon_col, cfg.lat_col, *self.predictors}
        missing_occurrence = sorted(required_occurrence - set(occurrence_features.columns))
        if missing_occurrence:
            raise KeyError(f"occurrence feature table missing columns: {missing_occurrence}")
        required_background = {cfg.lon_col, cfg.lat_col, *self.predictors}
        missing_background = sorted(required_background - set(background_features.columns))
        if missing_background:
            raise KeyError(f"background feature table missing columns: {missing_background}")

        model_presence = self.occurrence_split.model_pool(
            occurrence_features,
            id_col=cfg.id_col,
        )
        expected_model_ids = set(self.model_pool_ids)
        observed_model_ids = set(model_presence[cfg.id_col].astype(str))
        if observed_model_ids != expected_model_ids:
            missing = sorted(expected_model_ids - observed_model_ids)
            extra = sorted(observed_model_ids - expected_model_ids)
            raise ValueError(
                "occurrence_features must contain every frozen model-pool occurrence; "
                f"missing={missing[:10]}, extra={extra[:10]}"
            )

        inner = make_spatial_partition(
            pd.to_numeric(model_presence[cfg.lon_col], errors="raise").to_numpy(float),
            pd.to_numeric(model_presence[cfg.lat_col], errors="raise").to_numpy(float),
            pd.to_numeric(background_features[cfg.lon_col], errors="raise").to_numpy(float),
            pd.to_numeric(background_features[cfg.lat_col], errors="raise").to_numpy(float),
            n_blocks=int(cfg.inner_n_blocks),
            holdout_fraction=0.20,
            random_state=int(cfg.inner_random_state),
        )

        learner = fit_ecological_identification_learner(
            model_presence,
            background_features.reset_index(drop=True),
            inner.presence_blocks,
            inner.background_blocks,
            predictors=self.predictors,
            process_registry=self.process_registry,
            process_universe=self.process_universe,
            model_specs=cfg.model_specs,
            n_splits=int(cfg.inner_n_splits),
            chance_score=float(cfg.chance_score),
            minimum_margin=float(cfg.minimum_margin),
            sem_multiplier=float(cfg.sem_multiplier),
            occurrence_split=self.occurrence_split,
            occurrence_id_col=cfg.id_col,
        )

        group_table = pd.DataFrame(
            {
                "dataset": ["presence"] * len(model_presence)
                + ["background"] * len(background_features),
                "row_index": list(range(len(model_presence)))
                + list(range(len(background_features)),),
                "spatial_group": np.concatenate(
                    [inner.presence_blocks, inner.background_blocks]
                ).astype(int),
            }
        )
        return EcologicalIdentificationWorkflowFit(
            prepared=self,
            learner=learner,
            inner_group_ledger=group_table,
        )


@dataclass(frozen=True)
class EcologicalIdentificationWorkflowFit:
    """Fitted high-level study with explicit answer-check and audit helpers."""

    prepared: PreparedEcologicalIdentificationStudy
    learner: IdentificationLearnerFit
    inner_group_ledger: pd.DataFrame

    @property
    def process_summary(self) -> pd.DataFrame:
        return self.learner.process_summary.copy()

    @property
    def baseline_summary(self) -> pd.DataFrame:
        return self.learner.baseline_summary.copy()

    @property
    def selection_receipt(self) -> str:
        return self.learner.selection_receipt

    def evaluate_answer_check(
        self,
        full_occurrence_features: pd.DataFrame,
        answer_background: pd.DataFrame,
    ) -> dict[str, float | int | str]:
        """Open the sealed occurrence answer-check after fitting has completed."""

        return self.learner.evaluate_answer_check(
            full_occurrence_features,
            answer_background,
            self.prepared.occurrence_split,
            id_col=self.prepared.config.id_col,
        )

    def audit_tables(self) -> dict[str, pd.DataFrame]:
        return {
            "occurrence_split": self.prepared.occurrence_split.assignment.copy(),
            "registry_proposal": self.prepared.registry_proposal.copy(),
            "process_registry": self.prepared.process_registry.copy(),
            "inner_groups": self.inner_group_ledger.copy(),
            "baseline_summary": self.learner.baseline_summary.copy(),
            "process_summary": self.learner.process_summary.copy(),
            "fold_evidence": self.learner.fold_evidence.copy(),
        }

    def export_audit_bundle(self, directory: str | Path) -> Path:
        """Write deterministic CSV audit tables and a compact JSON manifest."""

        root = Path(directory)
        root.mkdir(parents=True, exist_ok=True)
        hashes: dict[str, str] = {}
        for name, frame in self.audit_tables().items():
            path = root / f"{name}.csv"
            frame.to_csv(path, index=False)
            hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()

        manifest = {
            "selection_receipt": self.selection_receipt,
            "occurrence_split_digest": self.prepared.occurrence_split.split_digest,
            "predictors": list(self.prepared.predictors),
            "process_universe": list(self.prepared.process_universe),
            "admissible_model_labels": list(self.learner.admissible_model_labels),
            "config": self.prepared.config.as_manifest(),
            "files_sha256": hashes,
        }
        manifest_path = root / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return manifest_path


def prepare_ecological_identification_study(
    occurrence_index: pd.DataFrame,
    predictor_metadata: pd.DataFrame,
    *,
    classification_rules: pd.DataFrame | None = None,
    predictors: Sequence[str] | None = None,
    config: EcologicalIdentificationConfig | None = None,
) -> PreparedEcologicalIdentificationStudy:
    """Freeze the outer occurrence split and process registry before fitting.

    Two registry modes are supported:

    * semi-automatic: pass ``classification_rules`` and metadata containing
      predictor/source/units; unmatched or conflicting rows raise
      :class:`ProcessRegistryReviewRequired` with the proposal attached;
    * direct: omit ``classification_rules`` and provide metadata with explicit
      ``predictor``, ``process`` and ``role`` columns.
    """

    cfg = config or EcologicalIdentificationConfig()
    if "predictor" not in predictor_metadata.columns:
        raise KeyError("predictor_metadata must contain a 'predictor' column")
    predictor_tuple = _unique_nonempty(
        tuple(predictors) if predictors is not None else tuple(predictor_metadata["predictor"]),
        name="predictors",
    )

    split = freeze_occurrence_answer_check_split(
        occurrence_index,
        id_col=cfg.id_col,
        lon_col=cfg.lon_col,
        lat_col=cfg.lat_col,
        n_blocks=int(cfg.outer_n_blocks),
        holdout_fraction=float(cfg.answer_check_fraction),
        random_state=int(cfg.outer_random_state),
    )

    if classification_rules is not None:
        proposal = propose_process_information_registry(
            predictor_metadata,
            classification_rules,
        )
        if proposal["review_required"].astype(bool).any():
            raise ProcessRegistryReviewRequired(proposal)
        registry = freeze_process_registry_proposal(
            proposal,
            expected_predictors=predictor_tuple,
        )
    else:
        required = {"predictor", "process", "role"}
        missing = sorted(required - set(predictor_metadata.columns))
        if missing:
            raise KeyError(
                "without classification_rules, predictor_metadata must contain "
                f"explicit registry columns: {missing}"
            )
        registry = normalize_process_information_registry(
            predictor_metadata[["predictor", "process", "role"]],
            predictor_universe=predictor_tuple,
        )
        proposal = _direct_registry_proposal(registry)

    process_universe = _unique_nonempty(
        tuple(registry["process"].astype(str)),
        name="process_universe",
    )
    return PreparedEcologicalIdentificationStudy(
        config=cfg,
        occurrence_split=split,
        registry_proposal=proposal,
        process_registry=registry,
        predictors=predictor_tuple,
        process_universe=process_universe,
    )


def quick_fit_ecological_identification(
    occurrence_features: pd.DataFrame,
    background_features: pd.DataFrame,
    predictor_metadata: pd.DataFrame,
    *,
    classification_rules: pd.DataFrame | None = None,
    predictors: Sequence[str] | None = None,
    config: EcologicalIdentificationConfig | None = None,
) -> EcologicalIdentificationWorkflowFit:
    """One-call convenience wrapper for already frozen feature/background recipes.

    For maximum information-barrier discipline, use
    :func:`prepare_ecological_identification_study` first and construct M/background
    from ``study.model_pool_ids`` before calling ``study.fit``. This convenience
    function is intended for workflows where the feature recipe and background
    construction were already prospectively frozen independently of the sealed
    answer-check outcomes.
    """

    cfg = config or EcologicalIdentificationConfig()
    occurrence_index = occurrence_features[[cfg.id_col, cfg.lon_col, cfg.lat_col]].copy()
    study = prepare_ecological_identification_study(
        occurrence_index,
        predictor_metadata,
        classification_rules=classification_rules,
        predictors=predictors,
        config=cfg,
    )
    return study.fit(occurrence_features, background_features)
