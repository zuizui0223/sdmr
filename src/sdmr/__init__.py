"""sdmr: transferable predictor discovery for presence-only SDMs."""

from .aggregate import aggregate_predictor_selection, choose_common_predictors
from .benchmark import (
    SpeciesBenchmarkResult,
    TaxonSplitBenchmarkResult,
    benchmark_species,
    benchmark_taxon_split,
)
from .metrics import boyce_index, presence_rank_score

__all__ = [
    "SpeciesBenchmarkResult",
    "TaxonSplitBenchmarkResult",
    "aggregate_predictor_selection",
    "benchmark_species",
    "benchmark_taxon_split",
    "boyce_index",
    "choose_common_predictors",
    "presence_rank_score",
]

__version__ = "0.1.0"
