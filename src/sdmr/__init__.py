"""sdmr: sealed-holdout tuning and transferable predictor discovery for SDMs."""

from .aggregate import aggregate_predictor_selection, choose_common_predictors
from .benchmark import (
    SpeciesBenchmarkResult,
    TaxonSplitBenchmarkResult,
    benchmark_species,
    benchmark_taxon_split,
)
from .equivalence import correlation_equivalence_groups, drop_group_importance
from .metrics import boyce_index, presence_rank_score
from .model import ModelSpec
from .tuning import (
    FrozenProtocol,
    MethodTaxonValidationResult,
    SpeciesMethodBenchmarkResult,
    benchmark_holdout_sensitivity,
    benchmark_method_corpus,
    benchmark_method_taxon_split,
    benchmark_species_methods,
    drop_one_importance,
    freeze_candidate_methods,
    summarize_method_performance,
    vif_prune_predictors,
    vif_values,
)

__all__ = [
    "FrozenProtocol",
    "MethodTaxonValidationResult",
    "ModelSpec",
    "SpeciesBenchmarkResult",
    "SpeciesMethodBenchmarkResult",
    "TaxonSplitBenchmarkResult",
    "aggregate_predictor_selection",
    "benchmark_holdout_sensitivity",
    "benchmark_method_corpus",
    "benchmark_method_taxon_split",
    "benchmark_species",
    "benchmark_species_methods",
    "benchmark_taxon_split",
    "boyce_index",
    "choose_common_predictors",
    "correlation_equivalence_groups",
    "drop_group_importance",
    "drop_one_importance",
    "freeze_candidate_methods",
    "presence_rank_score",
    "summarize_method_performance",
    "vif_prune_predictors",
    "vif_values",
]

__version__ = "0.2.0"
