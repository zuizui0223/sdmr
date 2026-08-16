"""Predeclared mapping from raw environmental predictors to ecological meaning.

Product-B synthesis must not confuse three levels:

1. a raw raster/predictor (for example a specific CHELSA variable);
2. a broader ecological process (for example thermal regime);
3. a substitutable/equivalence group of predictors that are explicitly judged to
   carry overlapping ecological information for the planned analysis.

Those mappings are scientific metadata, not something to infer after seeing which
variables win.  This registry validates and externalizes the mapping.  It ships no
real-data default equivalences because grouping BIOCLIM/CHELSA/soil variables is a
claim that must be predeclared for the actual Product-B analysis.

The existing Product-B candidate manifest remains the metadata source of truth.
``from_candidate_manifest`` upgrades that table into this richer registry without
requiring a second raster catalogue.  If no explicit equivalence group is present,
each predictor is conservatively treated as its own group.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

import pandas as pd


PredictorRole = Literal["ecological", "observation"]


@dataclass(frozen=True)
class PredictorProcessEntry:
    predictor: str
    process: str
    equivalence_group: str
    role: PredictorRole = "ecological"
    source_family: str = "unspecified"
    units: str = "unspecified"
    rationale: str = ""


@dataclass(frozen=True)
class PredictorProcessRegistry:
    entries: tuple[PredictorProcessEntry, ...]

    def __post_init__(self) -> None:
        if not self.entries:
            raise ValueError("predictor process registry must contain at least one entry")
        seen: set[str] = set()
        for entry in self.entries:
            predictor = str(entry.predictor).strip()
            process = str(entry.process).strip()
            group = str(entry.equivalence_group).strip()
            if not predictor:
                raise ValueError("predictor names must be non-empty")
            if predictor in seen:
                raise ValueError(f"duplicate predictor in registry: {predictor!r}")
            seen.add(predictor)
            if not process:
                raise ValueError(f"process must be non-empty for {predictor!r}")
            if not group:
                raise ValueError(f"equivalence_group must be non-empty for {predictor!r}")
            if entry.role not in {"ecological", "observation"}:
                raise ValueError(
                    f"role must be 'ecological' or 'observation' for {predictor!r}"
                )

    @classmethod
    def from_frame(cls, frame: pd.DataFrame) -> "PredictorProcessRegistry":
        required = {"predictor", "process", "equivalence_group", "role"}
        missing = required - set(frame.columns)
        if missing:
            raise KeyError(f"predictor registry frame missing columns: {sorted(missing)}")
        entries = []
        for row in frame.to_dict(orient="records"):
            entries.append(
                PredictorProcessEntry(
                    predictor=str(row["predictor"]),
                    process=str(row["process"]),
                    equivalence_group=str(row["equivalence_group"]),
                    role=str(row["role"]),
                    source_family=str(row.get("source_family", "unspecified")),
                    units=str(row.get("units", "unspecified")),
                    rationale=str(row.get("rationale", "")),
                )
            )
        return cls(tuple(entries))

    @classmethod
    def from_candidate_manifest(cls, manifest: pd.DataFrame) -> "PredictorProcessRegistry":
        """Build from the existing Product-B candidate manifest conservatively.

        Required legacy columns are only ``predictor`` and ``process`` here; the
        full manifest validator can still enforce source/version/mechanism in the
        upstream Product-B pipeline. Optional v2 columns:

        - ``equivalence_group``: predeclared interpretation group; defaults to the
          predictor itself rather than inventing substitution;
        - ``role``: ecological/observation; defaults to ecological;
        - ``units``: literal axis units for interpretation;
        - ``rationale``: explicit grouping/process rationale.

        ``source`` is reused as ``source_family`` and ``mechanism`` can serve as a
        fallback rationale, avoiding duplicate metadata tables.
        """

        required = {"predictor", "process"}
        missing = required - set(manifest.columns)
        if missing:
            raise KeyError(f"candidate manifest missing columns: {sorted(missing)}")
        rows = []
        for row in manifest.to_dict(orient="records"):
            predictor = str(row["predictor"])
            equivalence = row.get("equivalence_group")
            if pd.isna(equivalence) if equivalence is not None else True:
                equivalence = predictor
            role = row.get("role", "ecological")
            if pd.isna(role):
                role = "ecological"
            rationale = row.get("rationale")
            if rationale is None or pd.isna(rationale) or str(rationale).strip() == "":
                rationale = row.get("mechanism", "")
            rows.append(
                PredictorProcessEntry(
                    predictor=predictor,
                    process=str(row["process"]),
                    equivalence_group=str(equivalence),
                    role=str(role),
                    source_family=str(row.get("source", row.get("source_family", "unspecified"))),
                    units=str(row.get("units", "unspecified")),
                    rationale=str(rationale),
                )
            )
        return cls(tuple(rows))

    def as_frame(self) -> pd.DataFrame:
        return pd.DataFrame([asdict(entry) for entry in self.entries]).sort_values(
            ["role", "process", "equivalence_group", "predictor"],
            kind="mergesort",
        ).reset_index(drop=True)

    def process_aliases(self, *, ecological_only: bool = True) -> dict[str, str]:
        return {
            entry.predictor: entry.process
            for entry in self.entries
            if not ecological_only or entry.role == "ecological"
        }

    def equivalence_aliases(self, *, ecological_only: bool = True) -> dict[str, str]:
        return {
            entry.predictor: entry.equivalence_group
            for entry in self.entries
            if not ecological_only or entry.role == "ecological"
        }

    @property
    def ecological_predictors(self) -> tuple[str, ...]:
        return tuple(sorted(entry.predictor for entry in self.entries if entry.role == "ecological"))

    @property
    def observation_predictors(self) -> tuple[str, ...]:
        return tuple(sorted(entry.predictor for entry in self.entries if entry.role == "observation"))

    def validate_candidate_predictors(self, predictors: tuple[str, ...] | list[str]) -> None:
        known = {entry.predictor for entry in self.entries}
        unknown = sorted(set(str(x) for x in predictors) - known)
        if unknown:
            raise KeyError(f"candidate predictors absent from predeclared registry: {unknown}")
