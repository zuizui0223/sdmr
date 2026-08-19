import pandas as pd
import pytest

from sdmr.data.chelsa import build_chelsa_cog_uri, resolve_chelsa_manifest


def test_chelsa_url_patterns_cover_bioclim_and_summary_special_case():
    assert build_chelsa_cog_uri(remote_name="bio1", retrieval="annual_bio_cog").endswith(
        "/bio/CHELSA_bio1_1981-2010_V.2.1.tif"
    )
    assert build_chelsa_cog_uri(
        remote_name="vpd", retrieval="annual_bio_summary_cog", summary="mean"
    ).endswith("/bio/CHELSA_vpd_mean_1981-2010_V.2.1.tif")
    assert build_chelsa_cog_uri(
        remote_name="rsds", retrieval="annual_bio_summary_cog", summary="mean"
    ).endswith("/bio/CHELSA_rsds_1981-2010_mean_V.2.1.tif")


def test_manifest_resolution_does_not_silently_admit_paper_only_layers():
    manifest = pd.DataFrame(
        [
            {
                "predictor": "bio1",
                "source": "CHELSA-bioclim",
                "version": "2.1",
                "retrieval": "annual_bio_cog",
                "remote_name": "bio1",
                "summary": "",
                "availability": "current",
            },
            {
                "predictor": "rlus",
                "source": "CHELSA-BIOCLIM+-paper",
                "version": "2.1",
                "retrieval": "unresolved",
                "remote_name": "rlus",
                "summary": "",
                "availability": "paper_only",
            },
        ]
    )
    resolved = resolve_chelsa_manifest(manifest)
    rows = resolved.set_index("predictor")
    assert rows.loc["bio1", "resolution_status"] == "resolved"
    assert rows.loc["rlus", "resolution_status"] == "excluded_availability"
    with pytest.raises(ValueError):
        resolve_chelsa_manifest(manifest, include_availability=("current", "paper_only"), strict=True)
