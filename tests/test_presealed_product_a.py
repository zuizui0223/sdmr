import numpy as np
import pandas as pd

from sdmr.data.quality import OccurrenceAdmissionConfig
from sdmr.method import benchmark_species_methods
from sdmr.model import ModelSpec
from sdmr.pilot import MODEL_ROLE, OUTER_ROLE_COL, SEALED_ROLE, prepare_product_a_pilot


def _focal_records(n=120):
    # Deliberately duplicate every approximate 0.05-degree cell twice.  Strict
    # Product-A preparation must thin these before declaring the outer split.
    rows = []
    for i in range(n):
        x = i % 12
        y = i // 12
        lon = -5.0 + x * 0.08
        lat = 40.0 + y * 0.08
        for replicate in range(2):
            rows.append(
                {
                    "gbifID": f"p-{i}-{replicate}",
                    "species": "Plant alpha",
                    "longitude": lon,
                    "latitude": lat,
                }
            )
    return pd.DataFrame(rows)


def _target_group():
    rows = []
    k = 0
    for lon in np.arange(-6.0, -3.0, 0.08):
        for lat in np.arange(39.0, 42.0, 0.08):
            rows.append(
                {
                    "gbifID": f"t-{k}",
                    "species": "Other plant",
                    "longitude": float(lon),
                    "latitude": float(lat),
                }
            )
            k += 1
    return pd.DataFrame(rows)


def test_strict_pilot_thins_and_seals_before_M(monkeypatch):
    focal = _focal_records()
    target = _target_group()
    taxa = pd.DataFrame({"scientific_name": ["Plant alpha"]})

    captured_focal_roles = []
    from sdmr import pilot as pilot_module
    original = pilot_module.occurrence_buffer_membership

    def capture_m(frame, focal_occurrences, **kwargs):
        captured_focal_roles.append(set(focal_occurrences[OUTER_ROLE_COL].astype(str)))
        return original(frame, focal_occurrences, **kwargs)

    monkeypatch.setattr(pilot_module, "occurrence_buffer_membership", capture_m)
    result = prepare_product_a_pilot(
        focal,
        taxa,
        admission_config=OccurrenceAdmissionConfig(),
        min_occurrences=50,
        min_unique_cells=50,
        gate_cell_size_degrees=0.05,
        focal_thin_cell_size_degrees=0.05,
        outer_sealed_fraction=0.20,
        m_strategy="buffer",
        occurrence_buffer_km=300,
        target_group_pool=target,
        background_points=300,
        background_cell_size_degrees=0.05,
        random_state=17,
        strict_background=True,
    )

    assert len(result.occurrences) == 120
    assert set(result.occurrences[OUTER_ROLE_COL]) == {MODEL_ROLE, SEALED_ROLE}
    # The most important barrier: M sees model-pool presences only.
    assert captured_focal_roles == [{MODEL_ROLE}]
    ledger = result.background_ledger.iloc[0]
    assert bool(ledger["outer_sealed_before_M"])
    assert ledger["n_focal_model_occurrences"] < ledger["n_focal_occurrences"]
    assert ledger["n_focal_sealed_occurrences"] > 0
    assert set(result.background[OUTER_ROLE_COL]) == {MODEL_ROLE, SEALED_ROLE}
    # Fitting sufficiency is evaluated on the model pool, not rescued by sealed rows.
    gate = result.species_gate.iloc[0]
    assert gate["n_occurrences_total_thinned"] == 120
    assert gate["n_occurrences_model_pool"] < 120
    assert bool(gate["eligible"])


def test_method_uses_preassigned_outer_roles_without_reopening_sealed_rows():
    rng = np.random.default_rng(4)
    n_model, n_sealed = 80, 24
    n_bg_model, n_bg_sealed = 120, 40

    p = pd.DataFrame(
        {
            "species": "Plant alpha",
            "longitude": np.r_[rng.normal(0, 1, n_model), rng.normal(8, 0.4, n_sealed)],
            "latitude": np.r_[rng.normal(0, 1, n_model), rng.normal(8, 0.4, n_sealed)],
            OUTER_ROLE_COL: [MODEL_ROLE] * n_model + [SEALED_ROLE] * n_sealed,
            "__sdmr_outer_block": [0] * 20 + [1] * 20 + [2] * 20 + [3] * 20 + [4] * n_sealed,
        }
    )
    p["signal"] = np.r_[rng.normal(1.5, 0.5, n_model), rng.normal(1.5, 0.5, n_sealed)]
    p["noise"] = rng.normal(0, 1, len(p))

    b = pd.DataFrame(
        {
            "species": "Plant alpha",
            "longitude": rng.normal(0, 2, n_bg_model + n_bg_sealed),
            "latitude": rng.normal(0, 2, n_bg_model + n_bg_sealed),
            OUTER_ROLE_COL: [MODEL_ROLE] * n_bg_model + [SEALED_ROLE] * n_bg_sealed,
            "__sdmr_outer_block": [0] * (n_bg_model + n_bg_sealed),
            "signal": rng.normal(-1.0, 0.7, n_bg_model + n_bg_sealed),
            "noise": rng.normal(0, 1, n_bg_model + n_bg_sealed),
        }
    )

    result = benchmark_species_methods(
        p,
        b,
        ["signal", "noise"],
        species_name="Plant alpha",
        model_specs=[ModelSpec(C=1.0, degree=1, penalty="l2")],
        max_predictors=2,
        random_repeats=0,
        compute_drop_one=False,
        random_state=9,
    )
    assert result.sealed_metrics["outer_split_preassigned"].all()
    assert set(result.sealed_metrics["n_model_occurrences"]) == {n_model}
    assert set(result.sealed_metrics["n_sealed_occurrences"]) == {n_sealed}
    assert set(result.sealed_metrics["n_model_background"]) == {n_bg_model}
    assert set(result.sealed_metrics["n_sealed_background"]) == {n_bg_sealed}
