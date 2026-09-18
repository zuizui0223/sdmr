"""SDMR v3 process-information identification.

This namespace is scientifically separate from the frozen Product-A v2.x line.
"""

from .evidence import OccurrenceProcessEvaluation, evaluate_occurrence_processes
from .registry import FrozenProcessRegistry, freeze_process_registry
from .states import PROCESS_STATES, classify_process_state
from .taxonomy import DEFAULT_PLANT_PROCESSES

__all__ = [
    "DEFAULT_PLANT_PROCESSES",
    "FrozenProcessRegistry",
    "OccurrenceProcessEvaluation",
    "PROCESS_STATES",
    "classify_process_state",
    "evaluate_occurrence_processes",
    "freeze_process_registry",
]
