"""Reference-conditioned, block-aware ecological structure evidence.

Exploratory next-generation SDMR method. No historical Product-A, M5,
real-v5 or Structural biological endpoint is reopened by this module.

It audits *paired, additive, held-out losses* supplied by independent
model-fitting code. It does NOT infer causal competition, process necessity,
or universal portability. Use process_information_closure for the separate
full-system / all-carriers process knockout question.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from hashlib import sha256
from itertools import product
import json
from math import isfinite
from random import Random
from typing import Sequence


ADDITIVE_LOSSES = frozenset(
    {"squared_error", "hellinger_squared", "log_loss", "brier"}
)
VALID_AXES = frozenset({"spatial", "temporal", "region", "taxon"})
VALID_CLASSES = frozenset({"synthetic", "retrospective", "prospective"})


@dataclass(frozen=True)
class StructuralContextContract:
    """Pre-outcome identity and inferential scope for a paired model contrast."""

    system: str
    endpoint: str
    operator: str
    process: str
    candidate: str
    reference: str
    evidence_family_id: str
    source_receipt_sha256: str
    expected_unit_ledger_sha256: str
    expected_blocks: tuple[str, ...]
    validation_axis: str
    evidence_class: str
    metric: str
    minimum_blocks: int = 6
    minimum_gain: float = 0.0
    alpha: float = 0.05
    mc_draws: int = 9999
    mc_seed: int = 0
    target_time: str = "current"
    feature_time: str = "contemporaneous"
    train_only_preprocessing: bool = True
    outcome_blind_design: bool = True

    def __post_init__(self) -> None:
        for field in (
            "system", "endpoint", "operator", "process", "candidate",
            "reference", "evidence_family_id",
        ):
            if not getattr(self, field).strip():
                raise ValueError(field + " must be non-empty")
        for field in ("source_receipt_sha256", "expected_unit_ledger_sha256"):
            digest = getattr(self, field)
            if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise ValueError(field + " must be a lowercase SHA-256 digest")
        if not self.expected_blocks or len(set(self.expected_blocks)) != len(self.expected_blocks):
            raise ValueError("expected_blocks must be non-empty and unique")
        if any(not b.strip() for b in self.expected_blocks):
            raise ValueError("expected_blocks must not contain empty values")
        if self.validation_axis not in VALID_AXES:
            raise ValueError("invalid validation_axis")
        if self.evidence_class not in VALID_CLASSES:
            raise ValueError("invalid evidence_class")
        if self.metric not in ADDITIVE_LOSSES:
            raise ValueError("metric must be an additive per-unit loss, never RMSE")
        if self.minimum_blocks < 2 or not isinstance(self.minimum_blocks, int):
            raise ValueError("minimum_blocks must be an integer >= 2")
        if not isfinite(self.minimum_gain) or self.minimum_gain < 0:
            raise ValueError("minimum_gain must be finite and nonnegative")
        if not isfinite(self.alpha) or not 0 < self.alpha < 1:
            raise ValueError("alpha must lie strictly between 0 and 1")
        if not isinstance(self.mc_draws, int) or self.mc_draws < 999:
            raise ValueError("mc_draws must be an integer >= 999")
        if not isinstance(self.mc_seed, int) or self.mc_seed < 0:
            raise ValueError("mc_seed must be a nonnegative integer")
        if self.target_time not in ("current", "future"):
            raise ValueError("invalid target_time")
        if self.feature_time not in ("prior", "contemporaneous"):
            raise ValueError("invalid feature_time")
        if self.target_time == "future" and self.feature_time != "prior":
            raise ValueError("future endpoint may only use prior predictors")
        if not self.train_only_preprocessing:
            raise ValueError("held-out features or targets cannot enter training preprocessing")
        if self.evidence_class == "prospective" and not self.outcome_blind_design:
            raise ValueError("prospective status requires outcome-blind frozen design")


@dataclass(frozen=True)
class PairedHeldoutLoss:
    unit_id: str
    block_id: str
    reference_loss: float
    candidate_loss: float


@dataclass(frozen=True)
class StructuralContextResult:
    contract: StructuralContextContract
    n_units: int
    n_blocks: int
    block_deltas: tuple[tuple[str, float], ...]
    reference_block_equal_loss: float
    candidate_block_equal_loss: float
    gain_block_equal: float
    favorable_blocks: int
    signed_block_test: str
    signed_block_p: float | None
    status: str


def unit_ledger_sha256(rows: Sequence[PairedHeldoutLoss]) -> str:
    """Hash ONLY response-blind (unit, block) identities, never scores."""
    keys = sorted((r.unit_id, r.block_id) for r in rows)
    payload = json.dumps(keys, ensure_ascii=False, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def _signed_block_p(
    deltas: tuple[float, ...], *, mc_draws: int, seed: int
) -> tuple[str, float]:
    """Two-sided sign-flip conditional diagnostic; assumes block exchangeability.

    Exact at n<=16, deterministic Monte Carlo for larger n. This is NOT
    a population confidence interval nor a causal process identification test.
    """
    n = len(deltas)
    observed = abs(sum(deltas))
    tolerance = 1e-12 * max(1.0, observed)
    if n <= 16:
        n_extreme = sum(
            abs(sum(sign * d for sign, d in zip(signs, deltas)))
            >= observed - tolerance
            for signs in product((-1, 1), repeat=n)
        )
        return "exact_signed_block", n_extreme / (2 ** n)
    rng = Random(seed)
    n_extreme = 0
    for _ in range(mc_draws):
        trial = sum((1 if rng.getrandbits(1) else -1) * d for d in deltas)
        n_extreme += abs(trial) >= observed - tolerance
    return "mc_signed_block", (n_extreme + 1) / (mc_draws + 1)


def audit_contextual_structure(
    rows: Sequence[PairedHeldoutLoss],
    contract: StructuralContextContract,
) -> StructuralContextResult:
    """Audit exactly one frozen reference vs reference+candidate contrast.

    Block units, not repeated trees, traps, taxa or measurement occasions,
    receive equal weight. Both losses must be out-of-fold for the same unit.
    """
    rows = tuple(rows)
    if not rows:
        raise ValueError("no held-out rows supplied")
    if len({r.unit_id for r in rows}) != len(rows):
        raise ValueError("duplicate held-out unit IDs")
    if any(not r.unit_id.strip() or not r.block_id.strip() for r in rows):
        raise ValueError("unit_id and block_id must be non-empty")
    if unit_ledger_sha256(rows) != contract.expected_unit_ledger_sha256:
        raise ValueError("unit ledger differs from the frozen response-blind identity")
    groups: dict[str, list[PairedHeldoutLoss]] = defaultdict(list)
    for row in rows:
        for loss in (row.reference_loss, row.candidate_loss):
            if not isfinite(loss) or loss < 0:
                raise ValueError("paired additive losses must be finite and nonnegative")
        groups[row.block_id].append(row)
    if set(groups) != set(contract.expected_blocks):
        raise ValueError("block denominator differs from frozen expected_blocks")

    ref_means: list[float] = []
    plus_means: list[float] = []
    deltas: list[float] = []
    for block in contract.expected_blocks:
        values = groups[block]
        ref = sum(r.reference_loss for r in values) / len(values)
        plus = sum(r.candidate_loss for r in values) / len(values)
        ref_means.append(ref)
        plus_means.append(plus)
        deltas.append(ref - plus)
    gain = sum(deltas) / len(deltas)
    n_blocks = len(deltas)
    test, p = ("not_estimable", None)
    if n_blocks >= contract.minimum_blocks:
        test, p = _signed_block_p(
            tuple(deltas), mc_draws=contract.mc_draws, seed=contract.mc_seed
        )

    if p is None:
        status = "not_estimable"
    elif contract.evidence_class == "synthetic":
        status = "synthetic_diagnostic_only"
    elif contract.evidence_class == "retrospective" or not contract.outcome_blind_design:
        status = "retrospective_diagnostic_only"
    elif gain > contract.minimum_gain and p <= contract.alpha:
        status = "conditional_predictive_gain"
    elif gain < -contract.minimum_gain and p <= contract.alpha:
        status = "conditional_predictive_harm"
    else:
        status = "increment_unresolved"

    return StructuralContextResult(
        contract=contract,
        n_units=len(rows),
        n_blocks=n_blocks,
        block_deltas=tuple(zip(contract.expected_blocks, deltas)),
        reference_block_equal_loss=sum(ref_means) / n_blocks,
        candidate_block_equal_loss=sum(plus_means) / n_blocks,
        gain_block_equal=gain,
        favorable_blocks=sum(d > 0 for d in deltas),
        signed_block_test=test,
        signed_block_p=p,
        status=status,
    )


def integration_scope(a: StructuralContextResult, b: StructuralContextResult) -> str:
    """Refuse pooling incompatible ecology or non-independent evidence families."""
    x, y = a.contract, b.contract
    if x.endpoint != y.endpoint or x.operator != y.operator:
        return "methodological_alignment_only_different_endpoints_or_operators"
    if x.process != y.process or x.candidate != y.candidate:
        return "different_process_or_candidate_no_pooled_effect"
    if x.evidence_family_id == y.evidence_family_id:
        return "shared_source_not_independent_replication"
    if x.metric != y.metric:
        return "different_loss_scales_not_comparable"
    if x.validation_axis != y.validation_axis:
        return "different_validation_axes_no_pooled_effect"
    if x.evidence_class != "prospective" or y.evidence_class != "prospective":
        return "retrospective_or_synthetic_not_confirmatory"
    return "candidate_for_external_harmonization_not_automatic_pooling"
