#!/usr/bin/env python3
"""Audit M5 submission assets against the CURRENT manuscript and sensitivity receipts.

Production-only QA: this never runs ecological models or changes scientific endpoints.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from docx import Document

NAMESPACE = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
PAPER_ANCHORS = (
    "71/80",
    "0/700",
    "16/300",
    "10/50",
    "0/12 to 4/12",
    "1/3",
    "OpenAI ChatGPT",
    "neither field validation nor a new pass of the original M5 gates",
)
BUNDLE_FILES = (
    "manuscript/PROCESS_INFORMATION_KNOWN_TRUTH_SENSITIVITY_SI_V1.md",
    "manuscript/PROCESS_INFORMATION_EMPIRICAL_ATTEMPTS_SI_V1.md",
    "results/sdmr_nonlinear_effort_v2_prospective_result.json",
    "results/sdmr_v6_prospective_kt_v2_metrics.json",
)

def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def audit(root: Path, source: Path, revision: str) -> dict:
    paper = source.read_text(encoding="utf-8")
    docx_path = root / "anonymous_process_information_mee_manuscript.docx"
    bundle_path = root / "anonymous_process_information_review_bundle.zip"
    if not docx_path.exists() or not bundle_path.exists():
        raise ValueError("Missing anonymous DOCX or reviewer bundle")

    doc = Document(docx_path)
    text = "\n".join(p.text for p in doc.paragraphs)
    for anchor in PAPER_ANCHORS:
        if anchor not in paper:
            raise ValueError(f"Current manuscript missing scientific boundary: {anchor!r}")
        if anchor not in text:
            raise ValueError(f"Rendered DOCX is stale or omitted: {anchor!r}")
    if "Article type: Research Article" in text or "Target: Methods in Ecology and Evolution" in text:
        raise ValueError("Anonymous DOCX contains internal manuscript routing metadata")
    if doc.core_properties.author or doc.core_properties.last_modified_by:
        raise ValueError("DOCX core metadata contains an author name")

    with zipfile.ZipFile(docx_path) as z:
        xml = ET.fromstring(z.read("word/document.xml"))
        continuous = xml.find(".//w:sectPr/w:lnNumType", NAMESPACE)
        if continuous is None:
            raise ValueError("DOCX continuous line numbers are absent")
        if continuous.attrib.get(f"{{{NAMESPACE['w']}}}restart") != "continuous":
            raise ValueError("DOCX line-number restart mode changed")
        footer_names = [name for name in z.namelist() if re.fullmatch(r"word/footer\d+.xml", name)]
        if not footer_names or not any(b"PAGE" in z.read(name) for name in footer_names):
            raise ValueError("DOCX page number field is missing")

    expected = {
        f"figure{n}_{name}.{ext}"
        for n, name in (
            (1, "process_information_closure"),
            (2, "known_truth_worlds"),
            (3, "prospective_denominator"),
            (4, "world_authorization"),
        )
        for ext in ("svg", "png")
    }
    for filename in expected:
        file = root / "figures" / filename
        if not file.exists() or file.stat().st_size < 1000:
            raise ValueError(f"Missing or incomplete figure: {filename}")
        if file.suffix == ".png" and not file.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError(f"Invalid PNG signature: {filename}")

    with zipfile.ZipFile(bundle_path) as z:
        names = z.namelist()
        def member(rel: str) -> str:
            matches = [name for name in names if name.endswith("/" + rel)]
            if len(matches) != 1:
                raise ValueError(f"Reviewer bundle missing or duplicate item: {rel}")
            return matches[0]
        for rel in BUNDLE_FILES:
            member(rel)
        si = z.read(member(BUNDLE_FILES[0])).decode("utf-8")
        if "4/12" not in si or "1/3" not in si or "0/75" not in si:
            raise ValueError("Reviewer SI does not include the nonlinear/effort sensitivity")
        reviewers = z.read(member("README_REVIEWERS.md")).decode("utf-8")
        if "OpenAI ChatGPT" not in reviewers:
            raise ValueError("Reviewer bundle missing transparent AI-use disclosure")
        for name in names:
            if not name.endswith((".md", ".txt", ".json", ".csv", ".py")):
                continue
            text_file = z.read(name).decode("utf-8", errors="replace").lower()
            if "zuizui0223" in text_file or "github.com/zuizui0223" in text_file:
                raise ValueError(f"Identity leaked into anonymous bundle: {name}")

    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Expected an exact Git source revision")
    words = re.findall(r"\b[\w'’-]+\b", paper)
    abstract = paper.split("## Abstract", 1)[1].split("## 1. Introduction", 1)[0]
    abstract_words = re.findall(r"\b[\w'’-]+\b", abstract)
    if len(words) >= 8000 or len(abstract_words) >= 350:
        raise ValueError("MEE word ceiling exceeded")
    if "zuizui0223" in paper.lower():
        raise ValueError("Public author username in anonymous manuscript")

    return {
        "program": "m5-current-source-submission-audit-v2",
        "git_revision": revision,
        "current_manuscript_sha256": checksum(source),
        "docx_sha256": checksum(docx_path),
        "review_bundle_sha256": checksum(bundle_path),
        "manuscript_words": len(words),
        "abstract_words": len(abstract_words),
        "science_boundary_anchors_verified": list(PAPER_ANCHORS),
        "updated_sensitivity_in_docx": True,
        "updated_sensitivity_in_anonymous_bundle": True,
        "double_anonymous_checks_passed": True,
        "continuous_line_numbers_present": True,
        "figure_svg_and_png_count": len(expected),
        "files": [
            {"path": str(p.relative_to(root)), "sha256": checksum(p)}
            for p in sorted((root / "figures").glob("*"))
            if p.suffix.lower() in {".svg", ".png"}
        ],
        "does_not_reopen_known_truth_or_empirical_denominators": True,
    }

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--revision", required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    result = audit(args.root, args.source, args.revision)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
