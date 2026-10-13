import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
C=ROOT/"configs"/"sdmr_observation_aware_challenge_v1.json"
S=ROOT/"experiments"/"observation_aware_challenge_smoke_v1.py"


def test_contract_reserves_fresh_seeds_without_opening():
    c=json.loads(C.read_text())
    assert c["prospective_reservation"]["seeds"] == [93001,93002,93003]
    assert c["prospective_reservation"]["opened"] is False
    assert c["smoke"]["consumed_seed"] == 92003
    assert c["smoke"]["prospective_claim"] is False


def test_two_information_systems_are_not_pooled():
    c=json.loads(C.read_text())
    u=c["information_systems"]["effort_unavailable"]
    e=c["information_systems"]["effort_conditioned_upper_bound"]
    assert "original occurrence-distribution oracle" in u["reference"]
    assert "effort-conditioned occurrence-distribution oracle" in e["reference"]
    assert "not the same estimand" in e["interpretation"]


def test_effort_is_observation_only_not_process_carrier():
    text=S.read_text()
    assert 'observation_predictors=obs' in text
    assert 'ecological_predictors=tuple(world.predictor_universe)' in text
    assert 'obs=("log_sampling_effort",)' in text
    assert 'process_registry=world.process_registry' in text
    assert 'observation_unresolved_processes=()' in text
