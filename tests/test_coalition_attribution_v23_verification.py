import hashlib
import json
from types import SimpleNamespace

import pandas as pd
import pytest

from sdmr import coalition_attribution_v23_verification as verifier
from sdmr.coalition_attribution_v23 import classify_pair, ROUTES


@pytest.mark.parametrize("corruption", [None, "state", "missing_pair", "aggregate", "config", "target_as_source"])
def test_saved_evidence_verification(tmp_path, monkeypatch, corruption):
    cfg = dict(families=["example"], minimum_source_perturbations=3,
               rank_margin=.02, density_margin=.01, chance_score=.5, adequacy_margin=.01)
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(cfg), encoding="utf-8")
    monkeypatch.setattr(verifier, "CONFIG", config_path)
    monkeypatch.setattr(verifier, "load_contract", lambda: cfg)
    pair = dict(family="example", seed=17001, target_block=0, process_a="a", process_b="b")
    monkeypatch.setattr(verifier, "load_manifest", lambda _: pd.DataFrame([pair]))
    monkeypatch.setattr(verifier, "_base_objects", lambda: (None,) * 7 + ([SimpleNamespace(label="linear")],))
    receipt = dict(implementation_commit="frozen", config_sha256=hashlib.sha256(config_path.read_bytes()).hexdigest())
    (tmp_path / "execution_receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
    directory = tmp_path / "example"
    directory.mkdir()
    rows = []
    for source in range(1, 5):
        row = dict(**pair, source_block=source, model_label="linear", complete=True)
        for route, loss in zip(ROUTES, [0, .06, .06, .12]):
            row.update({f"{route}_prediction_rank": .7 - loss,
                        f"{route}_ecological_rank": .7 - loss,
                        f"{route}_ecological_density": -.3 - loss})
        rows.append(row)
    evidence = pd.DataFrame(rows)
    result = {**pair, **classify_pair(evidence, model_labels=["linear"])}
    aggregate = [result.copy()]
    if corruption == "state":
        result["state"] = "a_specific"
    if corruption == "aggregate":
        aggregate[0]["state"] = "a_specific"
    if corruption == "missing_pair":
        evidence.loc[:, "target_block"] = 2
    if corruption == "config":
        config_path.write_text("changed", encoding="utf-8")
    if corruption == "target_as_source":
        evidence.loc[0, "source_block"] = 0
    evidence.to_csv(directory / "model_evidence.csv", index=False)
    (directory / "pair_results.json").write_text(json.dumps([result]), encoding="utf-8")
    (tmp_path / "frozen_pair_states.json").write_text(json.dumps(aggregate), encoding="utf-8")
    if corruption:
        with pytest.raises(ValueError):
            verifier.verify("unused", tmp_path)
        assert not (tmp_path / "verification_receipt.json").exists()
    else:
        result = verifier.verify("unused", tmp_path)
        assert result["n_pair_states_reproduced"] == 1
        assert len(result["input_sha256"]) == 2
