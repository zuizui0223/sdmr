"""Development-only forest known-truth benchmark for SDMR × Structural.

Generates eight declared Gaussian/selection worlds and scores fixed models on
region-held-out, physical-site units. Never imports GBIF/FIA/beetle responses.
No clinical/causal or Product-A/M5/Structural empirical promotion is authorized.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Literal

import numpy as np

from .contextual_structure_evidence import (
    PairedHeldoutLoss,
    StructuralContextContract,
    audit_contextual_structure,
    unit_ledger_sha256,
)

WorldName = Literal[
    "direct_structure",
    "measured_site_proxy",
    "shared_carrier",
    "observation_selection",
    "spatial_only",
    "temporal_transfer",
    "operator_mismatch",
    "omitted_driver",
]
WORLDS: tuple[str, ...] = (
    "direct_structure",
    "measured_site_proxy",
    "shared_carrier",
    "observation_selection",
    "spatial_only",
    "temporal_transfer",
    "operator_mismatch",
    "omitted_driver",
)


@dataclass(frozen=True)
class ForestSample:
    world: str
    seed: int
    site_id: np.ndarray
    region: np.ndarray
    climate: np.ndarray
    b0: np.ndarray
    b1: np.ndarray
    z0: np.ndarray
    z1: np.ndarray
    tree0: np.ndarray
    tree1: np.ndarray
    beetle0: np.ndarray
    beetle1: np.ndarray
    observed: np.ndarray
    within_effect: float
    observation_selection_known: bool
    declared_carriers: tuple[str, ...]


@dataclass(frozen=True)
class ForestScore:
    world: str
    seed: int
    n_sites_source: int
    n_sites_observed: int
    n_regions: int
    spatial_gain: float
    temporal_gain: float
    closure_gain: float
    beetle_gain: float
    full_vs_null_gain: float
    spatial_p: float
    temporal_p: float
    within_effect: float
    observation_selection_known: bool
    declared_carriers: tuple[str, ...]
    inference_ceiling: str


def generate_forest_world(
    world: str, seed: int, *, n_regions: int = 8, sites_per_region: int = 64
) -> ForestSample:
    """Produce two visits of each physical site and an explicit selection mask.

    The 'known' process/selection labels are oracle metadata for scoring only;
    no fitted model receives them or latent site quality U.
    """
    if world not in WORLDS:
        raise ValueError("unknown known-truth world")
    if not isinstance(seed, int) or seed < 0:
        raise ValueError("seed must be nonnegative")
    if n_regions < 6 or sites_per_region < 16:
        raise ValueError("insufficient source-independent regions/sites")
    rng = np.random.default_rng(seed)
    n = n_regions * sites_per_region
    region = np.repeat(np.arange(n_regions), sites_per_region)
    # Regional context changes the marginal support without directly changing beta.
    region_shift = rng.normal(0, 0.22, n_regions)
    u = rng.normal(0, 1, n) + region_shift[region]
    climate = 0.35 * u + rng.normal(0, 1, n)
    v0, v1 = rng.normal(0, 0.8, (2, n))
    b0, b1 = u + v0, u + v1
    e0, e1 = rng.normal(0, 0.48, (2, n))
    beta = 0.8 if world in (
        "direct_structure", "shared_carrier", "temporal_transfer"
    ) else 0.0
    base = 0.28 * climate + 0.90 * u
    tree0 = base + beta * v0 + e0
    tree1 = base + beta * v1 + e1
    if world == "temporal_transfer":
        # Site-level snapshot association persists, but temporal change
        # is specifically linked to the *change* in structure.
        tree0 = base + e0
        tree1 = base + beta * (v1 - v0) + e1
    if world == "omitted_driver":
        # An unmeasured, site-persistent driver is independent of C and B.
        missing = rng.normal(0, 1.8, n)
        tree0, tree1 = missing + e0, missing + e1
    if world == "observation_selection":
        # Underlying Y is independent of structure conditional on climate;
        # outcome-dependent availability selects sites with similar B and Y.
        tree0, tree1 = 0.28 * climate + e0, 0.28 * climate + e1
        observed = (np.abs(b0 - tree0) < 1.1) & (np.abs(b1 - tree1) < 1.1)
    else:
        observed = np.ones(n, dtype=bool)

    # The extra measured representation is site quality in one world and a
    # perfect alternative structural carrier in another.
    z0 = np.zeros(n)
    z1 = np.zeros(n)
    if world == "measured_site_proxy":
        z0, z1 = u.copy(), u.copy()
    if world == "shared_carrier":
        z0, z1 = b0.copy(), b1.copy()

    # This separate endpoint represents a different biological operator.
    # It is NOT interchangeable with survivor growth.
    beetle0 = 0.28 * climate + e0
    beetle1 = 0.28 * climate + e1
    if world == "operator_mismatch":
        beetle0 = 0.28 * climate + 1.0 * b0 + e0
        beetle1 = 0.28 * climate + 1.0 * b1 + e1

    return ForestSample(
        world=world, seed=seed, site_id=np.arange(n), region=region,
        climate=climate, b0=b0, b1=b1, z0=z0, z1=z1,
        tree0=tree0, tree1=tree1,
        beetle0=beetle0, beetle1=beetle1, observed=observed,
        within_effect=beta,
        observation_selection_known=world != "observation_selection",
        declared_carriers=("b", "z") if world == "shared_carrier" else ("b",),
    )


def _predict(
    train_features: np.ndarray,
    y_train: np.ndarray,
    test_features: np.ndarray,
) -> np.ndarray:
    """Deterministic ridge: intercept unpenalized, scales estimated from train."""
    if train_features.ndim != 2 or test_features.ndim != 2:
        raise ValueError("features must be 2D")
    mean = train_features.mean(axis=0)
    scale = train_features.std(axis=0)
    scale[scale < 1e-12] = 1.0
    train = (train_features - mean) / scale
    test = (test_features - mean) / scale
    design = np.column_stack([np.ones(train.shape[0]), train])
    other = np.column_stack([np.ones(test.shape[0]), test])
    penalty = np.eye(design.shape[1]) * 0.01
    penalty[0, 0] = 0.0
    coeff = np.linalg.solve(design.T @ design + penalty, design.T @ y_train)
    return other @ coeff


def _score_comparison(
    sample: ForestSample, *, axis: str, endpoint: str, carrier_drop: bool = False
) -> tuple[float, float]:
    """Return (candidate increment, conditional block sign-flip p).

    Temporal means same-interval within-site change, NOT prospective forecasting:
    B at visit 1 is observed alongside the visit-1 response. No claim of
    prior-to-future predictive validity is authorized by this axis.

    Carrier closure compares the full fitted representation against the
    process-free reference. It is not a proof of physiological necessity.
    """
    if axis not in ("spatial", "temporal"):
        raise ValueError("invalid axis")
    if endpoint not in ("tree", "beetle"):
        raise ValueError("invalid endpoint")

    m = sample.observed
    region = sample.region[m]
    climate = sample.climate[m]
    b0, b1 = sample.b0[m], sample.b1[m]
    z0, z1 = sample.z0[m], sample.z1[m]
    y0 = (sample.tree0 if endpoint == "tree" else sample.beetle0)[m]
    y1 = (sample.tree1 if endpoint == "tree" else sample.beetle1)[m]
    if axis == "spatial":
        y = y0
        b = b0
        z = z0
        climate_feature = climate
    else:
        y = y1 - y0
        b = b1 - b0
        z = z1 - z0
        climate_feature = np.zeros_like(climate)

    use_z = sample.world in ("measured_site_proxy", "shared_carrier")
    if use_z and not (carrier_drop and sample.world == "shared_carrier"):
        reference = np.column_stack([climate_feature, z])
    else:
        reference = np.column_stack([climate_feature])
    full = np.column_stack([climate_feature, z, b]) if use_z else np.column_stack([climate_feature, b])

    # Exactly one site per line; each entire region is held out in turn.
    pairs: list[PairedHeldoutLoss] = []
    for reg in np.unique(region):
        train, test = region != reg, region == reg
        if train.sum() < 30 or test.sum() < 8:
            raise ValueError("insufficient heldout source support")
        ref_pred = _predict(reference[train], y[train], reference[test])
        full_pred = _predict(full[train], y[train], full[test])
        for j, ref, alt in zip(np.flatnonzero(m)[test],
                               (y[test] - ref_pred) ** 2,
                               (y[test] - full_pred) ** 2):
            pairs.append(PairedHeldoutLoss(str(int(j)), str(int(reg)), float(ref), float(alt)))

    blocks = tuple(str(int(x)) for x in sorted(np.unique(region)))
    # Synthetic provenance. Digest does not purport to identify a field archive.
    source_hash = sha256(f"dev-only:{sample.world}:{sample.seed}".encode()).hexdigest()
    contract = StructuralContextContract(
        system="synthetic_forest_v1",
        endpoint="tree_growth" if endpoint == "tree" else "beetle_composition",
        operator="growth" if endpoint == "tree" else "community",
        process="structure", candidate="basal_area",
        reference="climate+source-defined proxy",
        evidence_family_id=f"synthetic:{sample.world}:{sample.seed}",
        source_receipt_sha256=source_hash,
        expected_unit_ledger_sha256=unit_ledger_sha256(pairs),
        expected_blocks=blocks,
        validation_axis=axis, evidence_class="synthetic",
        metric="squared_error", minimum_blocks=6,
        target_time="current",
        feature_time="contemporaneous",
    )
    result = audit_contextual_structure(pairs, contract)
    assert result.status == "synthetic_diagnostic_only"
    assert result.signed_block_p is not None
    return result.gain_block_equal, result.signed_block_p


def _full_vs_null(sample: ForestSample) -> float:
    """Spatial heldout adequacy check versus a learned train-only intercept."""
    r, y, c, b = (
        sample.region[sample.observed], sample.tree0[sample.observed],
        sample.climate[sample.observed], sample.b0[sample.observed]
    )
    z = sample.z0[sample.observed]
    features = np.column_stack([c, z, b]) if sample.world in (
        "measured_site_proxy", "shared_carrier"
    ) else np.column_stack([c, b])
    blocks = []
    for reg in np.unique(r):
        tr, te = r != reg, r == reg
        null = np.full(int(te.sum()), float(y[tr].mean()))
        full = _predict(features[tr], y[tr], features[te])
        blocks.append(float(np.mean((y[te] - null) ** 2 - (y[te] - full) ** 2)))
    return float(np.mean(blocks))


def score_forest_world(sample: ForestSample) -> ForestScore:
    """Development diagnostic: report components, no causal/process promotion."""
    n_by_region = np.bincount(sample.region[sample.observed])
    if len(n_by_region) < 6 or np.any(n_by_region < 8):
        raise ValueError("world has insufficient observed independent blocks")
    spatial, sp = _score_comparison(sample, axis="spatial", endpoint="tree")
    temporal, tp = _score_comparison(sample, axis="temporal", endpoint="tree")
    closure, _ = _score_comparison(sample, axis="spatial", endpoint="tree", carrier_drop=True)
    beetle, _ = _score_comparison(sample, axis="spatial", endpoint="beetle")
    full = _full_vs_null(sample)
    return ForestScore(
        world=sample.world, seed=sample.seed,
        n_sites_source=len(sample.site_id), n_sites_observed=int(sample.observed.sum()),
        n_regions=len(n_by_region), spatial_gain=spatial, temporal_gain=temporal,
        closure_gain=closure, beetle_gain=beetle,
        full_vs_null_gain=full, spatial_p=sp, temporal_p=tp,
        within_effect=sample.within_effect,
        observation_selection_known=sample.observation_selection_known,
        declared_carriers=sample.declared_carriers,
        inference_ceiling="development_known_truth_only",
    )
