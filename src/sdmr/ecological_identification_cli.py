"""Command-line interface for the high-level ecological-identification workflow."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from collections.abc import Sequence

import pandas as pd

from .ecological_identification_io import (
    export_prepared_ecological_identification_study,
    load_prepared_ecological_identification_study,
)
from .ecological_identification_workflow import (
    EcologicalIdentificationConfig,
    ProcessRegistryReviewRequired,
    prepare_ecological_identification_study,
)


def _csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


def _predictor_list(value: str | None) -> tuple[str, ...] | None:
    if value is None:
        return None
    values = tuple(x.strip() for x in value.split(",") if x.strip())
    if not values:
        raise argparse.ArgumentTypeError("--predictors must contain at least one name")
    return values


def _config_from_args(args: argparse.Namespace) -> EcologicalIdentificationConfig:
    return EcologicalIdentificationConfig(
        id_col=args.id_col,
        lon_col=args.lon_col,
        lat_col=args.lat_col,
        outer_n_blocks=args.outer_blocks,
        answer_check_fraction=args.answer_fraction,
        outer_random_state=args.outer_seed,
        inner_n_blocks=args.inner_blocks,
        inner_n_splits=args.inner_splits,
        inner_random_state=args.inner_seed,
        chance_score=args.chance_score,
        minimum_margin=args.minimum_margin,
        sem_multiplier=args.sem_multiplier,
    )


def _prepare(args: argparse.Namespace) -> int:
    occurrences = _csv(args.occurrences)
    metadata = _csv(args.predictor_metadata)
    rules = _csv(args.classification_rules) if args.classification_rules else None
    predictors = _predictor_list(args.predictors)
    config = _config_from_args(args)
    try:
        study = prepare_ecological_identification_study(
            occurrences,
            metadata,
            classification_rules=rules,
            predictors=predictors,
            config=config,
        )
    except ProcessRegistryReviewRequired as exc:
        root = Path(args.output_dir)
        root.mkdir(parents=True, exist_ok=True)
        review_path = root / "registry_review_required.csv"
        exc.proposal.to_csv(review_path, index=False)
        print(f"PROCESS_REGISTRY_REVIEW_REQUIRED={review_path}")
        print(str(exc))
        return 2

    root = Path(args.output_dir)
    manifest = export_prepared_ecological_identification_study(study, root)
    (root / "model_pool_ids.txt").write_text(
        "\n".join(study.model_pool_ids) + "\n",
        encoding="utf-8",
    )
    (root / "answer_check_ids.txt").write_text(
        "\n".join(study.answer_check_ids) + "\n",
        encoding="utf-8",
    )
    print(f"PREPARED_STUDY={manifest}")
    print(f"MODEL_POOL_N={len(study.model_pool_ids)}")
    print(f"ANSWER_CHECK_N={len(study.answer_check_ids)}")
    return 0


def _fit(args: argparse.Namespace) -> int:
    study = load_prepared_ecological_identification_study(args.prepared_dir)
    occurrence_features = _csv(args.occurrence_features)
    background_features = _csv(args.background_features)
    fit = study.fit(occurrence_features, background_features)

    root = Path(args.output_dir)
    manifest = fit.export_audit_bundle(root)
    print(f"FIT_AUDIT={manifest}")
    print(f"SELECTION_RECEIPT={fit.selection_receipt}")
    print(fit.process_summary.to_string(index=False))

    if args.answer_background:
        answer_background = _csv(args.answer_background)
        answer = fit.evaluate_answer_check(
            occurrence_features,
            answer_background,
        )
        answer_path = root / "answer_check.json"
        answer_path.write_text(
            json.dumps(answer, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"ANSWER_CHECK={answer_path}")
    return 0


def _add_common_config(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--id-col", default="occurrence_id")
    parser.add_argument("--lon-col", default="longitude")
    parser.add_argument("--lat-col", default="latitude")
    parser.add_argument("--outer-blocks", type=int, default=8)
    parser.add_argument("--answer-fraction", type=float, default=0.20)
    parser.add_argument("--outer-seed", type=int, default=42)
    parser.add_argument("--inner-blocks", type=int, default=8)
    parser.add_argument("--inner-splits", type=int, default=4)
    parser.add_argument("--inner-seed", type=int, default=73)
    parser.add_argument("--chance-score", type=float, default=0.50)
    parser.add_argument("--minimum-margin", type=float, default=0.01)
    parser.add_argument("--sem-multiplier", type=float, default=1.0)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sdmr-identify",
        description=(
            "Prospective ecological-identification workflow with sealed occurrence "
            "answer-check and process-information knockouts."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser(
        "prepare",
        help="freeze occurrence roles and process registry before model fitting",
    )
    prepare.add_argument("--occurrences", required=True)
    prepare.add_argument("--predictor-metadata", required=True)
    prepare.add_argument("--classification-rules")
    prepare.add_argument("--predictors")
    prepare.add_argument("--output-dir", required=True)
    _add_common_config(prepare)
    prepare.set_defaults(func=_prepare)

    fit = sub.add_parser(
        "fit",
        help="fit a previously prepared study using model-pool data only",
    )
    fit.add_argument("--prepared-dir", required=True)
    fit.add_argument("--occurrence-features", required=True)
    fit.add_argument("--background-features", required=True)
    fit.add_argument("--answer-background")
    fit.add_argument("--output-dir", required=True)
    fit.set_defaults(func=_fit)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
