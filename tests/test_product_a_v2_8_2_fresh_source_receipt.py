import hashlib
import json
from pathlib import Path


RECEIPT = Path('configs/product_a_v2_8_2_fresh_raw_source_receipt.json')
SOURCE = Path('configs/product_a_v2_8_2_fresh_source_acquisition_contract.json')
PANEL = Path('configs/product_a_v2_8_2_fresh_confirmation_taxa.csv')


def test_v282_terminal_raw_source_receipt_pins_exact_successful_run():
    receipt = json.loads(RECEIPT.read_text())
    source = json.loads(SOURCE.read_text())
    panel_sha = hashlib.sha256(PANEL.read_bytes()).hexdigest()

    assert receipt['purpose'] == 'product_a_v2_8_2_fresh_raw_source_receipt'
    assert receipt['tracks_issue'] == 155
    assert receipt['upstream_source_issue'] == 148
    assert receipt['workflow_run_id'] == 33006988136
    assert receipt['workflow_conclusion'] == 'success'
    assert receipt['execution_sha'] == '1baa9f48250ffb5544f2af6706f6166cbce02381'
    assert receipt['execution_ref'] == 'frozen/product-a-v2-8-2-fresh-source-1baa9f48'
    assert receipt['authorization']['commit_sha'] == '4de98f6340d6324f8a7e1440a1387c20abc48a3c'
    assert receipt['authorization']['execution_config_blob_sha'] == '16fa44899977792baa1b1b527d0cef3a62c61956'
    assert receipt['authorization']['launcher_merge_sha'] == 'b2d41b879b584be00722aaa1408a9fafbb7d1cce'

    assert panel_sha == '835059c9ca4328253ea306f7b4027615007d558f6999a1049677d8903ce4a3c1'
    assert receipt['fresh_taxon_panel']['sha256'] == panel_sha
    assert receipt['fresh_taxon_panel']['n_taxa'] == 12
    assert receipt['fresh_taxon_panel']['selected_candidate_rank'] == 1
    assert receipt['fresh_taxon_panel']['selected_global_sealed_fraction'] == 0.25
    assert receipt['fresh_taxon_panel']['sealed_fraction_retuning_allowed'] is False
    assert receipt['fresh_taxon_panel']['post_source_taxon_reselection_allowed'] is False

    assert receipt['snapshot']['date'] == '2026-08-01'
    assert receipt['snapshot']['doi'] == '10.15468/dl.fs3btq'
    assert receipt['snapshot']['citation_sha256'] == '022a524b59c4c037b28f252c08294e0f22c5eb7b3bce5c52a0a5fc6016f17050'
    assert receipt['snapshot']['snapshot_shard_count'] == 9705
    assert receipt['snapshot']['snapshot_shard_catalog_sha256'] == '47300bbeb7d7b10711e685cff20d7574737c3440228e9b0247efac40a3d0ca84'
    assert receipt['snapshot']['temporal_independence_claim_allowed'] is False

    assert receipt['source_receipt_artifact'] == {
        'id': 9621763614,
        'name': 'product-a-v2-8-2-fresh-raw-source-receipt',
        'digest': 'sha256:9c5113031ed39d78145bc20d9f2a1989bd84f164fac58118d9000203829ffebd',
        'unpacked_payload_sha256': '0391526723745760181a24a63615c006058e3d1badd3fdc5b85d8c2ed0553caf',
    }

    focal = receipt['focal']
    assert focal['artifact_id'] == 9621755806
    assert focal['artifact_digest'] == 'sha256:a4cd9f37e7f058999cd53598542137d7078605858a1ce2a7e66e02dd2dfc2e7c'
    assert focal['manifest_artifact_id'] == 9621756562
    assert focal['manifest_artifact_digest'] == 'sha256:1f51dd2799d2c2b8967db8e373ed8decfd0840e373b359d047d19eaad61066d2'
    assert focal['manifest_unpacked_payload_sha256'] == '75da0ac12760b356ee50840d5956cc2b2f4ab761e66873d4f6a1a661996d9b38'
    assert focal['file_sha256'] == '4366258f2495604a0c9a5058aeb0111a751493b538ba436760f8555182d32fc5'
    assert focal['query_sha256'] == '40f25b5bafff11f5471b389778e29d29f7be02a4e76cd335cfdcee637517dc7e'
    assert focal['n_rows'] == 4637024 and focal['n_taxa'] == 12 and focal['parallel_chunk_count'] == 16

    target = receipt['target_group']
    assert target['artifact_id'] == 9621354699
    assert target['artifact_digest'] == 'sha256:431c0cca0eacfb6d1cb423b032996df051a5dd5efc056d9da43d96e56bb08f6c'
    assert target['manifest_artifact_id'] == 9621355161
    assert target['manifest_artifact_digest'] == 'sha256:c5f596d15b2313a1fcaa834bd9824befe9b2690c4a3a94abff711237370fdf89'
    assert target['manifest_unpacked_payload_sha256'] == '22a096ab16b7e6b02ac514f731a60f4a848f32bc4a29be1eca0a40c1845affcd'
    assert target['file_sha256'] == '9e8fb2827919e86d450cb5870093cef2adc752bee22a15540406265747d20bf6'
    assert target['query_sha256'] == 'b2261d66b156189bf9fd949046ad4f5b0a10697c584efe2ba009ca2d5dc8fdf7'
    assert target['excluded_taxa_sha256'] == panel_sha and target['excluded_taxa_count'] == 12
    assert target['one_per_grid_cell_degrees'] == 0.05 and target['parallel_chunk_count'] == 16
    assert target['source_independent_of_focal_occurrence_geography'] is True

    assert all(value is False for value in receipt['information_barrier'].values())
    assert source['next_gate'].startswith('after both v2_8_2 raw artifacts exist, pin exact run/artifact/file/query fingerprints')
    assert all(value is False for value in source['information_barrier'].values())
    assert 'separate_nonexecuting_pr' in receipt['next_gate']
