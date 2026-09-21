"""Development-only resampling from exact known-truth observation distributions."""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from .occurrence_oracle import occurrence_distribution_components
from .worlds import KnownTruthWorld


def resample_world_observations(
    world: KnownTruthWorld,
    *,
    n_occurrences: int,
    n_background: int,
    sampling_seed: int,
) -> KnownTruthWorld:
    """Resample record rows with replacement while preserving ecological truth."""

    n_occurrences = int(n_occurrences)
    n_background = int(n_background)
    if n_occurrences <= 0 or n_background <= 0:
        raise ValueError("n_occurrences and n_background must be positive")

    distribution = occurrence_distribution_components(world)
    rng = np.random.default_rng(int(sampling_seed))
    n_cells = len(world.environment)

    occurrence_idx = rng.choice(
        n_cells,
        size=n_occurrences,
        replace=True,
        p=distribution.q_occurrence,
    )
    background_idx = rng.choice(
        n_cells,
        size=n_background,
        replace=True,
        p=distribution.q_background,
    )

    occurrences = world.environment.iloc[occurrence_idx].copy().reset_index(drop=True)
    occurrences["record_role"] = "occurrence"
    occurrences["sample_id"] = [
        f"occ-{int(sampling_seed)}-{i}" for i in range(n_occurrences)
    ]

    background = world.environment.iloc[background_idx].copy().reset_index(drop=True)
    background["record_role"] = "background"
    background["sample_id"] = [
        f"bg-{int(sampling_seed)}-{i}" for i in range(n_background)
    ]

    return replace(
        world,
        occurrences=occurrences,
        background=background,
    )
