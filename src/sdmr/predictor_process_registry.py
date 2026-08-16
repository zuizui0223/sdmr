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
