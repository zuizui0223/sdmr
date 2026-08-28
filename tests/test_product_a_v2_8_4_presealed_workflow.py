from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "product-a-v2-8-4-presealed-part-reusable.yml"


def _workflow() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_presealed_workflow_is_reusable_only_and_has_no_sealed_stage():
    text = _workflow()
    trigger = text.split("permissions:", 1)[0]
    assert "on:\n  workflow_call:\n" in trigger
    assert "workflow_dispatch" not in text
    assert "sealed-audit" not in text
    assert "sealed audit" in text
    assert "product_b_unblocked" not in text
    assert "permissions:\n  contents: read\n  actions: read\n" in text


def test_group_matrix_is_exactly_one_part_full_denominator():
    text = _workflow()
    group = text.split("\n  group:\n", 1)[1].split("\n  aggregate-M:\n", 1)[0]
    assert "taxon_index: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]" in group
    assert "M: [buffer_150km, buffer_300km, buffer_500km]" in group
    assert "evaluation_group: [base, thermal, water, seasonality_phenology, energy_productivity, snow, wind]" in group
    assert 12 * 3 * 7 == 252
    assert "timeout-minutes: 255" in group
    assert "timeout --signal=TERM --kill-after=30s 225m" in group
    assert "attempt${{ github.run_attempt }}" in group


def test_runtime_and_actions_are_pinned_and_receipt_is_mandatory():
    text = _workflow()
    assert "ref: ${{ inputs.runtime_ref }}" in text
    assert "python-version: '3.12.11'" in text
    assert "--require-hashes" in text
    assert "actions/checkout@11d5960a326750d5838078e36cf38b85af677262" in text
    assert "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065" in text
    assert "actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093" in text
    assert "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02" in text
    receipt = text.split("\n  presealed-receipt:\n", 1)[1]
    assert "    needs: final-fit\n" in receipt
    assert "product-a-v2-8-4-presealed-receipt-${{ inputs.part_seed }}" in text
