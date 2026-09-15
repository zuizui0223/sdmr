"""Truth-blind four-route predictive attribution for consumed development.

Rows are paired ModelSpec scores within source-block omissions. Full, drop_a,
drop_b and drop_both routes must share exactly the same training/test rows.
One-SEM bands are inherited descriptive stability bands, not confidence
intervals from independent experimental replicates.
"""
from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

ROUTES = ("full", "drop_a", "drop_b", "drop_both")
SCORES = ("prediction_rank", "ecological_rank", "ecological_density")
SCORE_COLUMNS = tuple(f"{route}_{score}" for route in ROUTES for score in SCORES)


def classify_pair(evidence: pd.DataFrame, *, model_labels: Sequence[str],
                  minimum_sources: int = 3, rank_margin: float = 0.02,
                  density_margin: float = 0.01, chance: float = 0.5,
                  adequacy_margin: float = 0.01) -> dict:
    """Return route losses and a conservative attribution state; never fit.

Lower-band losses above both margins support contribution. Upper-band losses
below both margins support no *material* loss at this resolution. Every band
overlapping a margin remains uncertain. No process names or truth are inputs.
"""
    if not model_labels or len(set(model_labels)) != len(model_labels):
        raise ValueError("model labels must be nonempty and unique")
    if minimum_sources < 2 or min(rank_margin, density_margin, adequacy_margin) < 0:
        raise ValueError("invalid classification settings")
    required = {"source_block", "model_label", "complete", *SCORE_COLUMNS}
    if not required.issubset(evidence.columns):
        raise ValueError("missing four-route evidence columns")
    if evidence.duplicated(["source_block", "model_label"]).any():
        raise ValueError("duplicate source/model evidence")
    if not set(evidence.model_label).issubset(set(model_labels)):
        raise ValueError("unknown ModelSpec")
    if evidence.complete.isna().any() or not evidence.complete.map(lambda x: isinstance(x, (bool, np.bool_))).all():
        raise ValueError("complete must contain booleans")
    values = evidence.loc[evidence.complete, list(SCORE_COLUMNS)].to_numpy(float)
    if not np.isfinite(values).all():
        raise ValueError("nonfinite complete evidence")
    source_means = []
    for _, group in evidence.groupby("source_block", sort=True):
        if set(group.model_label) == set(model_labels) and group.complete.all():
            source_means.append(group[list(SCORE_COLUMNS)].mean())
    result = {"n_source_perturbations": len(source_means)}
    if len(source_means) < minimum_sources:
        return {**result, "state": "insufficient_evidence"}
    frame = pd.DataFrame(source_means)

    def band(values):
        values = np.asarray(values, dtype=float)
        mean = float(values.mean())
        sem = float(values.std(ddof=1) / np.sqrt(len(values)))
        return {"mean": mean, "sem": sem, "lower": mean - sem, "upper": mean + sem}

    adequate = True
    for score in ("prediction_rank", "ecological_rank"):
        value = band(frame[f"full_{score}"])
        result[f"full_{score}"] = value
        adequate &= value["mean"] >= chance + adequacy_margin - 1e-12 and value["lower"] >= chance - 1e-12
    result["full_adequate"] = bool(adequate)
    for route in ("drop_a", "drop_b", "drop_both"):
        rank = band(frame.full_ecological_rank - frame[f"{route}_ecological_rank"])
        density = band(frame.full_ecological_density - frame[f"{route}_ecological_density"])
        supported = rank["lower"] > rank_margin and density["lower"] > density_margin
        bounded = rank["upper"] <= rank_margin and density["upper"] <= density_margin
        result[route] = {"rank_loss": rank, "density_loss": density,
                         "effect": "supported" if supported else "bounded_small" if bounded else "uncertain"}
    a, b, both = (result[r]["effect"] for r in ("drop_a", "drop_b", "drop_both"))
    if not adequate:
        state = "full_inadequate"
    elif both != "supported":
        state = "joint_contribution_not_established"
    elif a == b == "supported":
        state = "joint_required"
    elif a == "supported" and b == "bounded_small":
        state = "a_specific"
    elif b == "supported" and a == "bounded_small":
        state = "b_specific"
    elif a == b == "bounded_small":
        state = "redundant_predictive_support"
    else:
        state = "joint_supported_attribution_uncertain"
    return {**result, "state": state}
