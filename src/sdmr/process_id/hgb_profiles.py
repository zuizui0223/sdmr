"""Frozen HGB profile registry shared by screening and finite inference."""
from __future__ import annotations


HGB_PROFILES = {
    "current": {
        "learning_rate": 0.08,
        "max_iter": 200,
        "max_leaf_nodes": 31,
        "min_samples_leaf": 20,
        "l2_regularization": 1e-3,
        "early_stopping": False,
    },
    "shallow7": {
        "learning_rate": 0.05,
        "max_iter": 100,
        "max_leaf_nodes": 7,
        "min_samples_leaf": 40,
        "l2_regularization": 1.0,
        "early_stopping": False,
    },
    "shallow3": {
        "learning_rate": 0.05,
        "max_iter": 100,
        "max_leaf_nodes": 3,
        "min_samples_leaf": 40,
        "l2_regularization": 1.0,
        "early_stopping": False,
    },
    "early7": {
        "learning_rate": 0.05,
        "max_iter": 200,
        "max_leaf_nodes": 7,
        "min_samples_leaf": 40,
        "l2_regularization": 1.0,
        "early_stopping": True,
        "validation_fraction": 0.2,
        "n_iter_no_change": 10,
    },
}


def get_hgb_profile(name: str) -> dict[str, object]:
    """Return a defensive copy of one frozen HGB profile."""

    key = str(name)
    if key not in HGB_PROFILES:
        raise ValueError(f"unknown HGB profile: {key!r}")
    return dict(HGB_PROFILES[key])
