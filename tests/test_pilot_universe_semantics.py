import pandas as pd

from sdmr.pilot_cli import _supports_standard_universes


def _row(predictor, source="CHELSA-bioclim", candidate_class="core_climate"):
    return {
        "predictor": predictor,
        "source": source,
        "version": "2.1",
        "candidate_class": candidate_class,
        "process": "climate",
        "mechanism": "test",
    }


def test_partial_bioclim_manifest_is_custom_not_mislabeled_bioclim19():
    manifest = pd.DataFrame([_row("bio1"), _row("bio4"), _row("bio12"), _row("bio15")])
    assert not _supports_standard_universes(manifest)


def test_complete_bioclim_plus_extension_supports_distinct_standard_universes():
    rows = [_row(f"bio{i}") for i in range(1, 20)]
    rows.append(_row("gdd5", candidate_class="extended_climate"))
    rows.append(_row("vpd", source="CHELSA-BIOCLIM+", candidate_class="extended_climate"))
    manifest = pd.DataFrame(rows)
    assert _supports_standard_universes(manifest)
