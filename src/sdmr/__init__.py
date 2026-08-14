"""sdmr: sealed-holdout tuning and transferable predictor discovery for SDMs."""

from .aggregate import aggregate_predictor_selection, choose_common_predictors
from .benchmark import (
    SpeciesBenchmarkResult,
    TaxonSplitBenchmarkResult,
    benchmark_species,
    benchmark_taxon_split,
)
from .drivers import (
    aggregate_process_evidence,
    annotate_predictor_metadata,
    equivalence_group_process_map,
    validate_candidate_manifest,
)
from .equivalence import correlation_equivalence_groups, drop_group_importance
from .heterogeneity import (
    aggregate_process_evidence_across_strata,
    aggregate_process_evidence_by_stratum,
    summarize_process_heterogeneity,
    validate_species_metadata,
)
from .metrics import boyce_index, presence_rank_score
from .synthesis import DriverCorpusResult, aggregate_predictor_evidence, benchmark_driver_corpus_from_strategy
from .model import ModelSpec
from .universality import (
    ProcessCoreSplitResult,
    RepeatedProcessCoreResult,
    benchmark_process_core_taxon_split,
    benchmark_repeated_process_core_splits,
    choose_common_processes,
)
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
    "DriverCorpusResult",
    "FrozenProtocol",
    "MethodTaxonValidationResult",
    "ModelSpec",
    "ProcessCoreSplitResult",
    "RepeatedProcessCoreResult",
    "SpeciesBenchmarkResult",
    "SpeciesMethodBenchmarkResult",
    "TaxonSplitBenchmarkResult",
    "aggregate_predictor_evidence",
    "aggregate_process_evidence_by_stratum",
    "aggregate_process_evidence_across_strata",
    "aggregate_predictor_selection",
    "aggregate_process_evidence",
    "annotate_predictor_metadata",
    "benchmark_driver_corpus_from_strategy",
    "benchmark_holdout_sensitivity",
    "benchmark_method_corpus",
    "benchmark_method_taxon_split",
    "benchmark_process_core_taxon_split",
    "benchmark_repeated_process_core_splits",
    "benchmark_species",
    "benchmark_species_methods",
    "benchmark_taxon_split",
    "boyce_index",
    "choose_common_predictors",
    "choose_common_processes",
    "correlation_equivalence_groups",
    "equivalence_group_process_map",
    "drop_group_importance",
    "drop_one_importance",
    "freeze_candidate_methods",
    "presence_rank_score",
    "summarize_method_performance",
    "vif_prune_predictors",
    "validate_candidate_manifest",
    "summarize_process_heterogeneity",
    "validate_species_metadata",
    "vif_values",
]

__version__ = "0.2.0"
