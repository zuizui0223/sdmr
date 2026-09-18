"""SDMR v3 process-information identification.

This namespace is scientifically separate from the frozen Product-A v2.x line.
"""

from .states import PROCESS_STATES, classify_process_state

__all__ = ["PROCESS_STATES", "classify_process_state"]
