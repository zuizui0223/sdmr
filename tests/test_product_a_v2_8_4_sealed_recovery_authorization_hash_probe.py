import hashlib
import json
from pathlib import Path

from sdmr.v2_8_4_sealed_authorization import (
    RECOVERY_DESIGN_PATH,
    REQUIRED_IMPLEMENTATION_PATHS,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def test_v284_sealed_recovery_authorization_hash_probe():
    payload = {
        'implementation_ref': '6c075e1ebc13713c15ceaffd94fd4c4e61eb75ad',
        'newline_canonical_sha256': {
            path: _sha(Path(path)) for path in REQUIRED_IMPLEMENTATION_PATHS
        },
        'caller_workflow_sha256': _sha(
            Path('.github/workflows/product-a-v2-8-4-sealed-authorized.yml')
        ),
        'recovery_design_contract_sha256': _sha(Path(RECOVERY_DESIGN_PATH)),
    }
    raise AssertionError(
        'V284_SEALED_RECOVERY_AUTH_HASH_PROBE='
        + json.dumps(payload, sort_keys=True)
    )
