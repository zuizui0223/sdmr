"""Fail-closed reporting QA for the Nature Product-A manuscript.

This utility checks manuscript presentation only. It does not read scientific
artifacts, rerun Product A, or alter any endpoint.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


ABSTRACT_LIMIT = 200
MAIN_TEXT_LIMIT = 3500
REQUIRED_RESULT_HEADINGS = (
    "Prediction and stable surfaces did not identify process truth",
    "Model-set sharpening could create false necessity",
    "Falsification-first identification became safe and sharp",
    "Fresh occurrence data revealed observational equivalence",
)
PLACEHOLDER_PATTERNS = (
    r"\bTODO\b",
    r"\bTBD\b",
    r"\[Corresponding author\]",
    r"\[Author",
    r"\[Affiliation",
    r"\[verify[^\]]*\]",
    r"XX+",
    r"INSERT",
)
FORBIDDEN_CLAIM_PATTERNS = (
    r"AUC (?:is|was) (?:the )?ecological truth",
    r"fundamental niche (?:was|is) recovered",
    r"causal physiological driver (?:was|is) identified",
    r"v2\.8\.4.*not[_ -]?tested",
)


def words(text: str) -> list[str]:
    text = re.sub(r"`[^`]+`", " ", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\[[0-9,–\- ]+\]", " ", text)
    return re.findall(r"\b[\w’'-]+\b", text, flags=re.UNICODE)


def strip_markdown_headings(text: str) -> str:
    return "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    )


def parse_article(text: str) -> tuple[str, str]:
    marker = "## Abstract"
    if marker not in text:
        raise ValueError("missing '## Abstract'")
    after = text.split(marker, 1)[1].lstrip("\n")
    abstract, sep, remainder = after.partition("\n\n")
    if not sep or not abstract.strip():
        raise ValueError("abstract must be one non-empty paragraph immediately after heading")

    reference_markers = (
        "\n## References",
        "\n## Nature-format production notes",
    )
    main = remainder
    cut = len(main)
    for ref_marker in reference_markers:
        idx = main.find(ref_marker)
        if idx >= 0:
            cut = min(cut, idx)
    main = main[:cut]
    return abstract.strip(), main.strip()


def check_article(path: Path) -> dict[str, int]:
    text = path.read_text(encoding="utf-8")
    abstract, main = parse_article(text)
    abstract_n = len(words(abstract))
    main_n = len(words(strip_markdown_headings(main)))

    errors: list[str] = []
    if abstract_n > ABSTRACT_LIMIT:
        errors.append(f"abstract word count {abstract_n} > {ABSTRACT_LIMIT}")
    if main_n > MAIN_TEXT_LIMIT:
        errors.append(f"main-text word count {main_n} > {MAIN_TEXT_LIMIT}")

    for heading in REQUIRED_RESULT_HEADINGS:
        if f"### {heading}" not in text:
            errors.append(f"missing Results subheading: {heading}")

    if "## Discussion" not in text:
        errors.append("missing Discussion heading")
    else:
        discussion = text.split("## Discussion", 1)[1]
        for marker in ("\n## References", "\n## Nature-format production notes"):
            if marker in discussion:
                discussion = discussion.split(marker, 1)[0]
        if re.search(r"(?m)^###\s+", discussion):
            errors.append("Discussion contains a level-3 topical subheading")

    # Nature-style introduction is intentionally unheaded.
    pre_results = text.split("## Results", 1)[0] if "## Results" in text else text
    if re.search(r"(?m)^##\s+Introduction\s*$", pre_results):
        errors.append("Introduction should be unheaded")

    for pattern in PLACEHOLDER_PATTERNS:
        hits = re.findall(pattern, text, flags=re.IGNORECASE)
        if hits:
            errors.append(f"placeholder pattern {pattern!r}: {hits[:3]}")

    for pattern in FORBIDDEN_CLAIM_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL):
            errors.append(f"forbidden/overstated claim pattern matched: {pattern!r}")

    # Frozen headline facts expected in the Article text.
    required_tokens = (
        "0.9889",
        "0.9833",
        "38/60",
        "50/60",
        "108/108",
        "empirical_confirmation_not_supported",
        "not_promoted",
    )
    for token in required_tokens:
        if token not in text:
            errors.append(f"missing frozen headline token: {token}")

    print(f"abstract_words={abstract_n}")
    print(f"main_text_words={main_n}")
    if errors:
        print("FORMAT_QA=FAIL")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(2)
    print("FORMAT_QA=PASS")
    return {"abstract_words": abstract_n, "main_text_words": main_n}


def check_submission_metadata(paths: list[Path]) -> None:
    errors: list[str] = []
    for path in paths:
        if not path.exists():
            errors.append(f"missing metadata file: {path}")
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in PLACEHOLDER_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE):
                errors.append(f"{path}: unresolved placeholder {pattern!r}")
    if errors:
        print("METADATA_QA=INCOMPLETE")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(3)
    print("METADATA_QA=PASS")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--article",
        type=Path,
        default=Path("docs/product_a_nature_ecology_evolution_article_draft.md"),
    )
    p.add_argument("--check-metadata", action="store_true")
    p.add_argument(
        "--metadata-file",
        action="append",
        type=Path,
        default=[],
        help="Files such as cover letter / author metadata to scan for placeholders.",
    )
    args = p.parse_args()
    check_article(args.article)
    if args.check_metadata:
        check_submission_metadata(args.metadata_file)


if __name__ == "__main__":
    main()
