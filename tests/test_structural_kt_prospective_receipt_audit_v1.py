from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_structural_kt_prospective_receipt_v1.py"
_SPEC = spec_from_file_location("audit_structural_kt_saved_receipt", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


def test_original_result_and_source_digest_are_frozen_literals():
    assert _MODULE.ORIGINAL_RUN == 44432358638
    assert len(_MODULE.ORIGINAL_SOURCE_COMMIT) == 40
    assert len(_MODULE.ORIGINAL_INNER_SHA256) == 64
    assert len(_MODULE.ORIGINAL_ZIP_SHA256) == 64
    assert len(_MODULE.SEEDS) == 10


def test_auditor_refuses_wrong_source_bytes_before_any_score_access(tmp_path):
    path = tmp_path / "fake.json"
    path.write_text("{}\n")
    with pytest.raises(ValueError, match="digest mismatch"):
        _MODULE.audit_saved_result(
            path, Path("configs/structural_process_kt_prospective_v1.json")
        )
