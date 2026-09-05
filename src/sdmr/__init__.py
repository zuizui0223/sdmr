"""sdmr: sealed-holdout ecological identification and SDM benchmarking."""

from .aggregate import aggregate_predictor_selection, choose_common_predictors
from .benchmark import SpeciesBenchmarkResult, TaxonSplitBenchmarkResult, benchmark_species, benchmark_taxon_split
from .cross_taxon_process_evidence import CrossTaxonProcessEvidence, aggregate_cross_taxon_process_evidence
from .drivers import aggregate_process_evidence, annotate_predictor_metadata, equivalence_group_process_map, validate_candidate_manifest
from .ecological_identification_learner import IdentificationLearnerFit, fit_ecological_identification_learner
from .ecological_identification_workflow import (
    EcologicalIdentificationConfig,
    EcologicalIdentificationWorkflowFit,
    PreparedEcologicalIdentificationStudy,
    ProcessRegistryReviewRequired,
    prepare_ecological_identification_study,
    quick_fit_ecological_identification,
)
from .ecological_inference_certificate import EcologicalInferenceCertificate, build_ecological_inference_certificate
from .ecological_interpretation import EcologicalInterpretationBundle, build_ecological_interpretation_bundle
from .ecological_response_profile import EcologicalResponseProfile, ecological_response_profile
from .empirical_product_a_v2 import EmpiricalNichePerturbation, EmpiricalProductAV2Result, benchmark_empirical_product_a_v2
from .equivalence import correlation_equivalence_groups, drop_group_importance
from .heterogeneity import (
    aggregate_process_evidence_across_strata,
    aggregate_process_evidence_by_stratum,
    summarize_process_heterogeneity,
    validate_species_metadata,
)
from .metrics import boyce_index, presence_rank_score
from .model import ModelSpec
from .niche_recovery_procedure import (
    PROCEDURE_STRATEGIES,
    RecoveryProcedure,
    RecoveryProcedureBenchmark,
    benchmark_recovery_procedures,
    cross_validated_recovery_procedure,
    select_recovery_procedure,
)
from .predictor_process_registry import PredictorProcessEntry, PredictorProcessRegistry
from .promotion import ProductAPromotionAssessment, ProductAPromotionCriteria, assess_product_a_promotion
from .protocol import (
    ProductAProtocolValidationResult,
    benchmark_product_a_protocol_grid,
    occurrence_feature_fingerprint,
    validate_matched_protocol_specifications,
)
from .protocol_stability import RepeatedProductAProtocolResult, benchmark_repeated_product_a_protocols
from .specification import (
    DataSpecificationBenchmarkResult,
    benchmark_matched_data_specifications,
    occurrence_table_fingerprint,
    validate_matched_occurrence_specifications,
)
from .synthesis import DriverCorpusResult, aggregate_predictor_evidence, benchmark_driver_corpus_from_strategy
from .universe import CandidateUniverse, UniverseMethodValidationResult, benchmark_method_universe_taxon_split, candidate_universes_from_manifest
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
    "CandidateUniverse",
    "CrossTaxonProcessEvidence",
    "DataSpecificationBenchmarkResult",
    "DriverCorpusResult",
    "EcologicalIdentificationConfig",
    "EcologicalIdentificationWorkflowFit",
    "EcologicalInferenceCertificate",
    "EcologicalInterpretationBundle",
    "EcologicalResponseProfile",
    "EmpiricalNichePerturbation",
    "EmpiricalProductAV2Result",
    "FrozenProtocol",
    "IdentificationLearnerFit",
    "MethodTaxonValidationResult",
    "ModelSpec",
    "PROCEDURE_STRATEGIES",
    "PredictorProcessEntry",
    "PredictorProcessRegistry",
    "PreparedEcologicalIdentificationStudy",
    "ProcessCoreSplitResult",
    "ProcessRegistryReviewRequired",
    "ProductAPromotionAssessment",
    "ProductAPromotionCriteria",
    "ProductAProtocolValidationResult",
    "RecoveryProcedure",
    "RecoveryProcedureBenchmark",
    "RepeatedProcessCoreResult",
    "RepeatedProductAProtocolResult",
    "SpeciesBenchmarkResult",
    "SpeciesMethodBenchmarkResult",
    "TaxonSplitBenchmarkResult",
    "UniverseMethodValidationResult",
    "aggregate_cross_taxon_process_evidence",
    "aggregate_predictor_evidence",
    "aggregate_process_evidence_by_stratum",
    "aggregate_process_evidence_across_strata",
    "aggregate_predictor_selection",
    "aggregate_process_evidence",
    "annotate_predictor_metadata",
    "assess_product_a_promotion",
    "benchmark_driver_corpus_from_strategy",
    "benchmark_empirical_product_a_v2",
    "benchmark_holdout_sensitivity",
    "benchmark_matched_data_specifications",
    "benchmark_method_corpus",
    "benchmark_method_taxon_split",
    "benchmark_method_universe_taxon_split",
    "benchmark_process_core_taxon_split",
    "benchmark_product_a_protocol_grid",
    "benchmark_recovery_procedures",
    "benchmark_repeated_process_core_splits",
    "benchmark_repeated_product_a_protocols",
    "benchmark_species",
    "benchmark_species_methods",
    "benchmark_taxon_split",
    "boyce_index",
    "build_ecological_inference_certificate",
    "build_ecological_interpretation_bundle",
    "candidate_universes_from_manifest",
    "choose_common_predictors",
    "choose_common_processes",
    "correlation_equivalence_groups",
    "cross_validated_recovery_procedure",
    "ecological_response_profile",
    "equivalence_group_process_map",
    "drop_group_importance",
    "drop_one_importance",
    "fit_ecological_identification_learner",
    "freeze_candidate_methods",
    "occurrence_feature_fingerprint",
    "occurrence_table_fingerprint",
    "prepare_ecological_identification_study",
    "presence_rank_score",
    "quick_fit_ecological_identification",
    "select_recovery_procedure",
    "summarize_method_performance",
    "summarize_process_heterogeneity",
    "validate_candidate_manifest",
    "validate_matched_occurrence_specifications",
    "validate_matched_protocol_specifications",
    "validate_species_metadata",
    "vif_prune_predictors",
    "vif_values",
]

__version__ = "0.3.0.dev0"
