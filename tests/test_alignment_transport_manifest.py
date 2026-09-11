from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "configs" / "alignment_transport_v15_focus_manifest.csv"


def test_v15_focus_manifest_is_frozen_nine_cell_subset():
    frame = pd.read_csv(MANIFEST)
    assert list(frame.columns) == ["family", "seed", "target_process", "v14_classification"]
    assert len(frame) == 9
    assert not frame.duplicated(["family", "seed", "target_process"]).any()
    assert set(frame["v14_classification"]) == {"conditioning_alignment_required", "mixed"}
    assert (frame["v14_classification"] == "conditioning_alignment_required").sum() == 7
    assert (frame["v14_classification"] == "mixed").sum() == 2
