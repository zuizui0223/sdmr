import hashlib
import json
from pathlib import Path

from sdmr.v2_8_4_sealed_authorization import REQUIRED_IMPLEMENTATION_PATHS


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def test_truth_blind_authorization_hash_probe():
    payload = {
        'implementation_ref': '2690c169adc2d9261a13b4c801c8a02006fc7cca',
        'newline_canonical_sha256': {
            path: _sha(Path(path)) for path in REQUIRED_IMPLEMENTATION_PATHS
        },
        'caller_workflow_sha256': _sha(Path('.github/workflows/product-a-v2-8-4-sealed-authorized.yml')),
    }
    raise AssertionError('V284_SEALED_AUTH_HASH_PROBE=' + json.dumps(payload, sort_keys=True))
