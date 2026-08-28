from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "product-a-v2-8-4-presealed-part-reusable.yml"


def _workflow() -> tuple[dict, str]:
    text = WORKFLOW.read_text(encoding="utf-8")
    return yaml.safe_load(text), text


def test_presealed_workflow_is_reusable_only_and_has_no_sealed_stage():
    payload, text = _workflow()
    trigger = payload.get("on", payload.get(True))
    assert set(trigger) == {"workflow_call"}
    assert "workflow_dispatch" not in text
    assert "sealed-audit" not in text
    assert "sealed audit" in text
    assert "product_b_unblocked" not in text
    assert payload["permissions"] == {"contents": "read", "actions": "read"}


def test_group_matrix_is_exactly_one_part_full_denominator():
    payload, text = _workflow()
    jobs = payload["jobs"]
    matrix = jobs["group"]["strategy"]["matrix"]
    assert len(matrix["taxon_index"]) == 12
    assert matrix["M"] == ["buffer_150km", "buffer_300km", "buffer_500km"]
    assert matrix["evaluation_group"] == [
        "base", "thermal", "water", "seasonality_phenology",
        "energy_productivity", "snow", "wind",
    ]
    assert 12 * 3 * 7 == 252
    assert jobs["group"]["timeout-minutes"] == 255
    assert "timeout --signal=TERM --kill-after=30s 225m" in text
    assert "attempt${{ github.run_attempt }}" in text


def test_runtime_and_actions_are_pinned_and_receipt_is_mandatory():
    payload, text = _workflow()
    assert "ref: ${{ inputs.runtime_ref }}" in text
    assert "python-version: '3.12.11'" in text
    assert "--require-hashes" in text
    assert "actions/checkout@11d5960a326750d5838078e36cf38b85af677262" in text
    assert "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065" in text
    assert "actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093" in text
    assert "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02" in text
    assert payload["jobs"]["presealed-receipt"]["needs"] == "final-fit"
    assert "product-a-v2-8-4-presealed-receipt-${{ inputs.part_seed }}" in text
