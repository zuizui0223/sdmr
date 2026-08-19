"""Model admissibility for validated observation-process nuisance terms.

If a candidate-independent observation audit demonstrates a reproducible nuisance
process, ecological inference from a record model that omits that process is not
comparable to inference from a model that explicitly absorbs it: correcting the
held-out occurrence target cannot undo coefficient confounding that already
entered the fitted ecological response.

This module therefore implements a specification gate, not a model score. When no
replicated observation process is active, every candidate is admissible. When it
is active, a candidate is admissible for *ecological inference* only if every
frozen required nuisance predictor is explicitly declared in the candidate's
``observation_predictors``. Merely including the same column as an ordinary
"ecological" predictor does not satisfy the contract because it would still be
interpreted as part of the niche surface rather than marginalized as nuisance.

Conventional record-prediction comparators such as AUC remain outside this gate.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .niche_recovery_cv import RecoveryCandidate


@dataclass(frozen=True)
class ObservationAdmissibility:
    correction_active: bool
    required_observation_predictors: tuple[str, ...]
    admissible_candidates: tuple[str, ...]
    inadmissible_candidates: tuple[str, ...]


def observation_model_admissibility(
    candidates: Mapping[str, RecoveryCandidate],
    required_observation_predictors: Sequence[str],
    *,
    correction_active: bool,
) -> ObservationAdmissibility:
    """Return candidate names admissible for ecological inference.

    Parameters
    ----------
    candidates
        Predeclared candidate library.
    required_observation_predictors
        Frozen nuisance variables/process proxies whose observation signal was
        validated independently of candidate fitting.
    correction_active
        Species/procedure-level replicated observation gate. If false, no
        candidate restriction is applied.
    """

    required = tuple(dict.fromkeys(str(x) for x in required_observation_predictors))
    names = tuple(sorted(str(name) for name in candidates))
    if not correction_active or not required:
        return ObservationAdmissibility(
            correction_active=bool(correction_active),
            required_observation_predictors=required,
            admissible_candidates=names,
            inadmissible_candidates=(),
        )

    required_set = set(required)
    admissible: list[str] = []
    inadmissible: list[str] = []
    for name in names:
        declared = set(candidates[name].observation_predictors)
        if required_set <= declared:
            admissible.append(name)
        else:
            inadmissible.append(name)
    if not admissible:
        raise ValueError(
            "replicated observation process is active but no ecological candidate "
            f"declares all required nuisance predictors: {required}"
        )
    return ObservationAdmissibility(
        correction_active=True,
        required_observation_predictors=required,
        admissible_candidates=tuple(admissible),
        inadmissible_candidates=tuple(inadmissible),
    )
