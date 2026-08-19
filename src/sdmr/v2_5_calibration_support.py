"""Pre-truth calibration-support contract for Product-A v2.5.

v2.4 could only discover that a required validation boundary was uncalibrated
after the validation panel had already been opened.  This module moves that
failure mode in front of validation: the declared calibration taxa must cover
every predictor x response quantity that any declared validation family can
require.

The check uses only the frozen scenario/family declarations.  It never simulates
or reads generating truth and therefore can run before any validation worker is
started.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterable, Mapping, Sequence


DEFAULT_RESPONSE_QUANTITIES = ("optimum", "lower_limit", "upper_limit")


@dataclass(frozen=True)
class CalibrationSupportAudit:
    required_validation_keys: tuple[tuple[str, str], ...]
    declared_calibration_keys: tuple[tuple[str, str], ...]
    missing_keys: tuple[tuple[str, str], ...]
    support_counts: tuple[tuple[str, str, int], ...]
    minimum_support_per_key: int

    @property
    def complete(self) -> bool:
        return not self.missing_keys and all(
            count >= self.minimum_support_per_key
            for _, _, count in self.support_counts
            if (_, _) in self.required_validation_keys
        )


def response_processes_for_family(family: str) -> tuple[str, ...]:
    """Return frozen response axes required by one bundled known-truth family.

    This mirrors the scenario semantics in ``known_truth_response`` without
    constructing the simulation.  Only ``omitted_driver`` requires the additional
    soil axis; all currently bundled families audit temperature and water.
    """

    family = str(family)
    if not family:
        raise ValueError("family must be non-empty")
    if family == "omitted_driver":
        return ("temperature", "water", "soil")
    return ("temperature", "water")


def _families(rows: Sequence[Mapping[str, object]], *, label: str) -> tuple[str, ...]:
    values: list[str] = []
    for row in rows:
        family = str(row.get("family", ""))
        if not family:
            raise ValueError(f"{label} contains a row without family")
        values.append(family)
    if not values:
        raise ValueError(f"{label} must be non-empty")
    return tuple(values)


def required_response_keys(
    families: Iterable[str],
    *,
    quantities: Sequence[str] = DEFAULT_RESPONSE_QUANTITIES,
) -> tuple[tuple[str, str], ...]:
    quantities = tuple(str(value) for value in quantities)
    if not quantities or any(not value for value in quantities):
        raise ValueError("quantities must be non-empty strings")
    keys = {
        (predictor, quantity)
        for family in families
        for predictor in response_processes_for_family(str(family))
        for quantity in quantities
    }
    return tuple(sorted(keys))


def audit_calibration_support(
    *,
    calibration: Sequence[Mapping[str, object]],
    validation: Sequence[Mapping[str, object]],
    quantities: Sequence[str] = DEFAULT_RESPONSE_QUANTITIES,
    minimum_support_per_key: int = 1,
) -> CalibrationSupportAudit:
    """Audit declared calibration support before validation truth can be opened."""

    minimum_support_per_key = int(minimum_support_per_key)
    if minimum_support_per_key < 1:
        raise ValueError("minimum_support_per_key must be >= 1")

    calibration_families = _families(calibration, label="calibration")
    validation_families = _families(validation, label="validation")
    required = required_response_keys(validation_families, quantities=quantities)
    declared = required_response_keys(calibration_families, quantities=quantities)

    counts: dict[tuple[str, str], int] = {key: 0 for key in required}
    for family in calibration_families:
        supported = set(required_response_keys((family,), quantities=quantities))
        for key in counts:
            if key in supported:
                counts[key] += 1

    missing = tuple(
        sorted(key for key in required if counts.get(key, 0) < minimum_support_per_key)
    )
    support_counts = tuple(
        (predictor, quantity, int(counts[(predictor, quantity)]))
        for predictor, quantity in required
    )
    return CalibrationSupportAudit(
        required_validation_keys=required,
        declared_calibration_keys=declared,
        missing_keys=missing,
        support_counts=support_counts,
        minimum_support_per_key=minimum_support_per_key,
    )


def require_calibration_support(config: Mapping[str, object]) -> CalibrationSupportAudit:
    """Fail closed unless every panel has predeclared calibration support.

    The v2.5 config contains a top-level ``calibration_support`` contract and one
    ``calibration`` plus ``validation`` taxon list per panel.  The returned audit
    is the union across panels; any panel failure raises before model fitting.
    """

    support = config.get("calibration_support")
    if not isinstance(support, Mapping):
        raise ValueError("config requires calibration_support")
    minimum = int(support.get("minimum_calibration_taxa_per_key", 1))
    quantities_raw = support.get("quantities", DEFAULT_RESPONSE_QUANTITIES)
    if not isinstance(quantities_raw, Sequence) or isinstance(quantities_raw, (str, bytes)):
        raise ValueError("calibration_support.quantities must be a sequence")
    quantities = tuple(str(value) for value in quantities_raw)

    panels = config.get("panels")
    if not isinstance(panels, Sequence) or isinstance(panels, (str, bytes)) or not panels:
        raise ValueError("config requires non-empty panels")

    all_required: set[tuple[str, str]] = set()
    all_declared: set[tuple[str, str]] = set()
    all_missing: set[tuple[str, str]] = set()
    aggregate_counts: dict[tuple[str, str], int] = {}
    failures: list[str] = []
    for panel in panels:
        if not isinstance(panel, Mapping):
            raise ValueError("panel entries must be mappings")
        name = str(panel.get("name", "")) or "<unnamed>"
        calibration = panel.get("calibration")
        validation = panel.get("validation")
        if not isinstance(calibration, Sequence) or isinstance(calibration, (str, bytes)):
            raise ValueError(f"panel {name} requires calibration taxa")
        if not isinstance(validation, Sequence) or isinstance(validation, (str, bytes)):
            raise ValueError(f"panel {name} requires validation taxa")
        audit = audit_calibration_support(
            calibration=calibration,
            validation=validation,
            quantities=quantities,
            minimum_support_per_key=minimum,
        )
        all_required.update(audit.required_validation_keys)
        all_declared.update(audit.declared_calibration_keys)
        all_missing.update(audit.missing_keys)
        for predictor, quantity, count in audit.support_counts:
            key = (predictor, quantity)
            aggregate_counts[key] = min(aggregate_counts.get(key, count), count)
        if not audit.complete:
            failures.append(
                f"{name}: " + ", ".join(f"{p}/{q}" for p, q in audit.missing_keys)
            )

    if failures:
        raise ValueError(
            "validation response keys lack predeclared calibration support: "
            + "; ".join(failures)
        )

    return CalibrationSupportAudit(
        required_validation_keys=tuple(sorted(all_required)),
        declared_calibration_keys=tuple(sorted(all_declared)),
        missing_keys=tuple(sorted(all_missing)),
        support_counts=tuple(
            (predictor, quantity, aggregate_counts[(predictor, quantity)])
            for predictor, quantity in sorted(all_required)
        ),
        minimum_support_per_key=minimum,
    )
