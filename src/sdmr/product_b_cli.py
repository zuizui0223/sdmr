"""Formal Product-B entry point requiring inheritance of the full Product-A protocol."""
from __future__ import annotations

import argparse
from pathlib import Path

from .cli import _read_method_choice_values, main as benchmark_main

_RESERVED = {"--mode", "--method-choice", "--strategy", "--output-dir"}


def _validate_protocol_choice(path: str, data_specification_name: str) -> dict[str, str]:
    values = _read_method_choice_values(path)
    required = (
        "winning_data_specification",
        "winning_universe",
        "winning_strategy",
        "winning_universe_sha256",
        "winning_predictors",
    )
    missing = [key for key in required if not values.get(key, "").strip()]
    if missing:
        raise ValueError(
            "Product B requires a full Product-A protocol choice, not only a strategy/universe choice. "
            f"Missing fields: {missing}"
        )
    expected = values["winning_data_specification"].strip()
    observed = str(data_specification_name).strip()
    if expected != observed:
        raise ValueError(
            f"Product-B data specification {observed!r} does not match frozen Product-A choice {expected!r}"
        )
    return values


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run Product B only after declaring the exact Product-A data specification and passing the frozen "
            "full protocol choice. Remaining SDMR driver/universality arguments follow a standalone --."
        )
    )
    parser.add_argument("--protocol-choice", required=True, help="product_a_protocol_choice.txt from Product A")
    parser.add_argument("--data-specification-name", required=True)
    parser.add_argument("--stage", choices=("drivers", "universality"), default="drivers")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("benchmark_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)

    try:
        values = _validate_protocol_choice(args.protocol_choice, args.data_specification_name)
    except ValueError as exc:
        parser.error(str(exc))

    extra = list(args.benchmark_args)
    if extra and extra[0] == "--":
        extra = extra[1:]
    conflicts = sorted(flag for flag in _RESERVED if flag in extra)
    if conflicts:
        parser.error("Do not override frozen Product-B wrapper arguments: " + ",".join(conflicts))

    benchmark_argv = [
        "--mode", args.stage,
        "--method-choice", args.protocol_choice,
        "--output-dir", args.output_dir,
        *extra,
    ]
    code = benchmark_main(benchmark_argv)
    if code != 0:
        return int(code)

    out = Path(args.output_dir)
    (out / "product_b_protocol_contract.txt").write_text(
        "data_specification=" + values["winning_data_specification"] + "\n"
        + "universe=" + values["winning_universe"] + "\n"
        + "strategy=" + values["winning_strategy"] + "\n"
        + "universe_sha256=" + values["winning_universe_sha256"] + "\n"
        + "predictors=" + values["winning_predictors"] + "\n"
        + "product_a_occurrence_sha256=" + values.get("occurrence_sha256", "") + "\n"
        + "product_a_occurrence_feature_sha256=" + values.get("occurrence_feature_sha256", "") + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
