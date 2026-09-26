"""Fresh empirical SDMR validation boundary.

Nothing in this namespace authorizes outcome access by itself.  The final frozen
contract must pass the fail-closed validators before a fresh empirical execution
receipt can be created.
"""

from .contract import (
    EMPIRICAL_GATES,
    PRIMARY_RECONSTRUCTION_METRIC,
    FreshContractError,
    contract_sha256,
    validate_final_freeze_contract,
    validate_prefreeze_contract,
)

__all__ = [
    "EMPIRICAL_GATES",
    "PRIMARY_RECONSTRUCTION_METRIC",
    "FreshContractError",
    "contract_sha256",
    "validate_final_freeze_contract",
    "validate_prefreeze_contract",
]
