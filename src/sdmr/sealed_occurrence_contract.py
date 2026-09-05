"""Generic occurrence model-pool versus sealed answer-check contract.

The split is frozen from occurrence identities and coordinates before ecological
predictors, accessible-area construction, background sampling, tuning or model
selection.  The returned contract stores only row identities, spatial blocks and
roles; it does not carry environmental values for sealed occurrences.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib

import numpy as np
import pandas as pd

from .validation import make_presence_spatial_partition

MODEL_POOL_ROLE = "model_pool"
ANSWER_CHECK_ROLE = "answer_check"


def _canonical_split_digest(
    rows: pd.DataFrame,
    *,
    id_col: str,
    lon_col: str,
    lat_col: str,
    n_blocks: int,
    holdout_fraction: float,
    random_state: int,
) -> str:
    canonical = rows[[id_col, lon_col, lat_col]].copy()
    canonical[id_col] = canonical[id_col].astype(str)
    canonical[lon_col] = pd.to_numeric(canonical[lon_col], errors="raise")
    canonical[lat_col] = pd.to_numeric(canonical[lat_col], errors="raise")
    canonical = canonical.sort_values(id_col, kind="mergesort")
    payload = canonical.to_csv(index=False, float_format="%.12g").encode("utf-8")
    header = f"{n_blocks}|{holdout_fraction:.12g}|{random_state}|".encode("utf-8")
    return hashlib.sha256(header + payload).hexdigest()


@dataclass(frozen=True)
class OccurrenceAnswerCheckSplit:
    """Frozen occurrence identities assigned to model-pool or answer-check roles."""

    assignment: pd.DataFrame
    id_col: str
    split_digest: str

    def __post_init__(self) -> None:
        required = {self.id_col, "spatial_block", "outer_role"}
        missing = sorted(required - set(self.assignment.columns))
        if missing:
            raise KeyError(f"occurrence split assignment missing columns: {missing}")
        if self.assignment[self.id_col].astype(str).duplicated().any():
            raise ValueError("occurrence split identities must be unique")
        roles = set(self.assignment["outer_role"].astype(str))
        if roles != {MODEL_POOL_ROLE, ANSWER_CHECK_ROLE}:
            raise ValueError(
                "occurrence split must contain both model_pool and answer_check roles"
            )
        if not str(self.split_digest).strip():
            raise ValueError("split_digest must be non-empty")

    @property
    def model_pool_ids(self) -> tuple[str, ...]:
        return tuple(
            self.assignment.loc[
                self.assignment["outer_role"].eq(MODEL_POOL_ROLE), self.id_col
            ].astype(str)
        )

    @property
    def answer_check_ids(self) -> tuple[str, ...]:
        return tuple(
            self.assignment.loc[
                self.assignment["outer_role"].eq(ANSWER_CHECK_ROLE), self.id_col
            ].astype(str)
        )

    def _validate_frame_ids(self, frame: pd.DataFrame, *, id_col: str | None = None) -> str:
        column = self.id_col if id_col is None else str(id_col)
        if column not in frame.columns:
            raise KeyError(f"frame missing occurrence identity column: {column!r}")
        ids = frame[column].astype(str)
        if ids.duplicated().any():
            raise ValueError("frame occurrence identities must be unique")
        known = set(self.assignment[self.id_col].astype(str))
        unknown = sorted(set(ids) - known)
        if unknown:
            raise ValueError(
                "frame contains identities outside frozen occurrence split: "
                + ", ".join(unknown[:10])
            )
        return column

    def model_pool(self, frame: pd.DataFrame, *, id_col: str | None = None) -> pd.DataFrame:
        """Return only model-pool rows; safe for fitting, tuning and M construction."""

        column = self._validate_frame_ids(frame, id_col=id_col)
        allowed = set(self.model_pool_ids)
        return frame.loc[frame[column].astype(str).isin(allowed)].copy().reset_index(drop=True)

    def assert_model_pool_only(
        self,
        frame: pd.DataFrame,
        *,
        id_col: str | None = None,
    ) -> None:
        """Fail closed if answer-check occurrences leak into a pre-selection table."""

        column = self._validate_frame_ids(frame, id_col=id_col)
        leaked = sorted(set(frame[column].astype(str)) & set(self.answer_check_ids))
        if leaked:
            raise RuntimeError(
                "sealed answer-check occurrence leakage before selection completion: "
                + ", ".join(leaked[:10])
            )

    def open_answer_check(
        self,
        frame: pd.DataFrame,
        *,
        selection_receipt: str,
        id_col: str | None = None,
    ) -> pd.DataFrame:
        """Explicitly materialize answer-check rows after a frozen selection receipt exists."""

        receipt = str(selection_receipt).strip()
        if not receipt:
            raise ValueError("selection_receipt must be non-empty before opening answer-check rows")
        column = self._validate_frame_ids(frame, id_col=id_col)
        sealed = set(self.answer_check_ids)
        return frame.loc[frame[column].astype(str).isin(sealed)].copy().reset_index(drop=True)


def freeze_occurrence_answer_check_split(
    occurrences: pd.DataFrame,
    *,
    id_col: str = "occurrence_id",
    lon_col: str = "longitude",
    lat_col: str = "latitude",
    n_blocks: int = 8,
    holdout_fraction: float = 0.20,
    random_state: int = 42,
) -> OccurrenceAnswerCheckSplit:
    """Freeze whole spatial occurrence blocks before ecological feature use.

    Only identity and coordinates are consumed.  The resulting role assignment
    should be persisted before M/background construction or environmental raster
    extraction.  Downstream training code should use :meth:`model_pool` or call
    :meth:`assert_model_pool_only` before fitting/tuning.

    The source rows are canonically sorted by occurrence identity before spatial
    clustering so the same occurrence set, coordinates and seed produce the same
    block/role assignment regardless of input row order.
    """

    required = {id_col, lon_col, lat_col}
    missing = sorted(required - set(occurrences.columns))
    if missing:
        raise KeyError(f"occurrence table missing columns: {missing}")

    source = occurrences[[id_col, lon_col, lat_col]].copy()
    source[id_col] = source[id_col].astype(str).str.strip()
    if source[id_col].eq("").any():
        raise ValueError("occurrence identities must be non-empty")
    if source[id_col].duplicated().any():
        raise ValueError("occurrence identities must be unique before sealing")
    source = source.sort_values(id_col, kind="mergesort").reset_index(drop=True)

    lon = pd.to_numeric(source[lon_col], errors="raise").to_numpy(float)
    lat = pd.to_numeric(source[lat_col], errors="raise").to_numpy(float)
    if not np.isfinite(lon).all() or not np.isfinite(lat).all():
        raise ValueError("occurrence coordinates must be finite")

    partition = make_presence_spatial_partition(
        lon,
        lat,
        n_blocks=int(n_blocks),
        holdout_fraction=float(holdout_fraction),
        random_state=int(random_state),
    )
    test_blocks = set(partition.test_blocks)
    assignment = pd.DataFrame(
        {
            id_col: source[id_col].astype(str).to_numpy(),
            "spatial_block": partition.presence_blocks.astype(int),
        }
    )
    assignment["outer_role"] = np.where(
        assignment["spatial_block"].isin(test_blocks),
        ANSWER_CHECK_ROLE,
        MODEL_POOL_ROLE,
    )
    assignment = assignment.sort_values(id_col, kind="mergesort").reset_index(drop=True)

    digest = _canonical_split_digest(
        source,
        id_col=id_col,
        lon_col=lon_col,
        lat_col=lat_col,
        n_blocks=int(n_blocks),
        holdout_fraction=float(holdout_fraction),
        random_state=int(random_state),
    )
    return OccurrenceAnswerCheckSplit(
        assignment=assignment,
        id_col=id_col,
        split_digest=digest,
    )
