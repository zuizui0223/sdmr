from __future__ import annotations

import argparse

from sdmr.evaluation_contrast_aggregate import write_selector_contrast_aggregate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parts-root", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    write_selector_contrast_aggregate(args.parts_root, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
