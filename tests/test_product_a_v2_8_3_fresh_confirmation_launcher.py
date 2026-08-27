from pathlib import Path


LAUNCHER = Path('.github/workflows/product-a-v2-8-3-fresh-confirmation-pr-launch.yml')


def test_v283_launcher_is_trigger_only_and_exact_pinned():
    text = LAUNCHER.read_text()
    assert "configs/product_a_v2_8_3_fresh_confirmation_pr_trigger.txt" in text
    assert "authorization_commit_sha = '4011d40754871a6067756a034b6827a28926bad4'" in text
    assert "authorization_blob_sha = 'bef669dd35f1708fe6c8ea292a8afbca67e04792'" in text
    assert "expected_runtime_sha = '8095dd814f2c20babe2865f5a5a0835dde047727'" in text
    assert "expected_frozen_ref = 'frozen/product-a-v2-8-3-fresh-confirmation-8095dd81'" in text
    assert "expected_panel_sha256 = '835059c9ca4328253ea306f7b4027615007d558f6999a1049677d8903ce4a3c1'" in text
    assert "workflow = 'product-a-v2-8-3-fresh-confirmation.yml'" in text


def test_v283_launcher_rechecks_authorization_and_all_frozen_blobs():
    text = LAUNCHER.read_text()
    assert "local != auth" in text
    assert "if len(required_paths) != 21" in text
    assert "if set(frozen) != set(required_paths)" in text
    assert "frozen v2.8.3 scientific blob changed" in text
    assert "'configs/product_a_v2_8_3_fresh_confirmation_contract.json'" in text
    assert "'src/sdmr/v2_8_3_fresh_aggregate.py'" in text
    assert "'src/sdmr/v2_7_2_fresh_sealed_audit.py'" in text
    assert "'src/sdmr/v2_7_3_presealed_feasibility.py'" in text


def test_v283_launcher_preserves_scientific_boundary_and_is_idempotent():
    text = LAUNCHER.read_text()
    assert "'scientific_promotion_allowed'," in text
    assert "'product_b_unblocked'," in text
    assert "'post_outcome_fraction_change_allowed'," in text
    assert "if len(runs) > 1" in text
    assert "if not runs:" in text
    assert "expected exactly one exact v2.8.3 scientific run" in text
    assert "'authorization_commit_sha': authorization_commit_sha" in text
    assert "'authorization_blob_sha': authorization_blob_sha" in text
    assert "'expected_runtime_sha': expected_runtime_sha" in text
    assert "'expected_frozen_ref': expected_frozen_ref" in text
