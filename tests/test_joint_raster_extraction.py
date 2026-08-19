import pandas as pd

import sdmr.pilot_cli as pilot_cli


def test_joint_raster_extraction_calls_sampler_once_and_restores_roles(monkeypatch):
    calls = []

    def fake_extract(points, specs):
        calls.append((len(points), tuple(specs)))
        out = points.copy()
        out["bio1"] = range(len(out))
        provenance = pd.DataFrame([{"predictor": "bio1", "uri": "fake.tif"}])
        return out, provenance

    monkeypatch.setattr(pilot_cli, "extract_raster_values", fake_extract)
    occ = pd.DataFrame({"species": ["a", "a"], "longitude": [1, 2], "latitude": [3, 4]})
    bg = pd.DataFrame({"species": ["a"], "longitude": [5], "latitude": [6]})

    occ_out, bg_out, provenance = pilot_cli._extract_joint_rasters(occ, bg, ["spec"])
    assert calls == [(3, ("spec",))]
    assert len(occ_out) == 2 and len(bg_out) == 1
    assert "__sdmr_point_role" not in occ_out and "__sdmr_point_role" not in bg_out
    assert provenance.loc[0, "extraction_mode"] == "joint_occurrence_background"
    assert provenance.loc[0, "n_occurrence_points"] == 2
    assert provenance.loc[0, "n_background_points"] == 1
