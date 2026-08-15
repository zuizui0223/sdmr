#!/usr/bin/env python3
"""CLI wrapper for leakage-safe Product-A stability aggregation."""
from __future__ import annotations

import argparse
from pathlib import Path

from sdmr.stability_aggregate import aggregate_leakage_safe_stability


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parts-root", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    aggregate_leakage_safe_stability(Path(args.parts_root), Path(args.output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
