#!/usr/bin/env python3
"""Build a double-anonymous peer-review bundle for the M5 process-information paper."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

INCLUDE=[
  "src/sdmr/process_id/evidence.py",
  "src/sdmr/candidate_outer_fold_evidence.py",
  "src/sdmr/process_exclusion_certificate.py",
  "src/sdmr/process_information_closure.py",
  "src/sdmr/process_id/taxonomy.py",
  "src/sdmr/process_id/known_truth/worlds.py",
  "src/sdmr/process_id/known_truth/integration_v5.py",
  "src/sdmr/process_id/known_truth/prospective_kt.py",
  "src/sdmr/process_id/states.py",
  "src/sdmr/process_id/hgb_profiles.py",
  "src/sdmr/process_id/known_truth/permutation_gate.py",
  "src/sdmr/process_id/known_truth/scoped_pipeline_v6.py",
  "src/sdmr/process_id/known_truth/integration_v6.py",
  "configs/sdmr_v6_prospective_kt_v2.json",
  "results/sdmr_v6_prospective_kt_v2_metrics.json",
  "docs/SDMR_V6_PROSPECTIVE_KT_V2_RESULT.md",
  "manuscript/PROCESS_INFORMATION_EMPIRICAL_SCOPE_LEDGER.md",
  "manuscript/PROCESS_INFORMATION_EMPIRICAL_ATTEMPTS_SI_V1.md",
  "evidence/mee_real_v5_receipts/sdmr_fresh_empirical_v5_model_pool_diagnostic.json",
  "evidence/mee_real_v5_receipts/sdmr_fresh_empirical_v5_model_pool_terminal_decision.json",
  "evidence/mee_real_v5_receipts/sdmr_fresh_empirical_v5_sealed_promotion_result.json",
  "evidence/mee_real_v5_receipts/sdmr_fresh_empirical_v5_sealed_postterminal_receipt.json",
  "tests/test_process_id_permutation_gate.py",
  "tests/test_process_id_scoped_pipeline_v6.py",
  "tests/test_process_id_prospective_kt_gate.py",
]

FORBIDDEN_PATTERNS=[
  r"\b[a-f0-9]{40}\b",  # Git commit IDs can reveal author and repository
  r"(?<![0-9])[0-9]{11}(?![0-9])",  # run/artifact IDs are not for anonymous review
  r"zuizui0223",
  r"github\.com/zuizui0223",
  r"@tohoku\.ac\.jp",
  r"/Users/",
  r"C:\\Users\\",
]

# Only reviewer-facing copies are redacted. Archived source receipts stay byte-identical.
REVIEW_RECEIPTS={
  "results/sdmr_v6_prospective_kt_v2_metrics.json",
  "evidence/mee_real_v5_receipts/sdmr_fresh_empirical_v5_model_pool_diagnostic.json",
  "evidence/mee_real_v5_receipts/sdmr_fresh_empirical_v5_model_pool_terminal_decision.json",
  "evidence/mee_real_v5_receipts/sdmr_fresh_empirical_v5_sealed_promotion_result.json",
  "evidence/mee_real_v5_receipts/sdmr_fresh_empirical_v5_sealed_postterminal_receipt.json",
}
PROVENANCE_KEYS={
  "source", "queued_sealed_runs", "workflow_run", "workflow_head",
  "artifact_id", "artifact_digest", "terminal_freeze_commit",
  "authoritative_run", "authoritative_head", "authoritative_artifact_id",
  "authoritative_artifact_digest", "superseded_run", "superseded_head",
  "superseded_artifact_id", "superseded_artifact_digest",
}
REVIEW_TEXT_PROVENANCE_LINES={
  "docs/SDMR_V6_PROSPECTIVE_KT_V2_RESULT.md": (
    "- workflow run:", "- workflow head:", "- artifact id:", "- artifact digest:"
  ),
  "manuscript/PROCESS_INFORMATION_EMPIRICAL_SCOPE_LEDGER.md": (
    "Authoritative known-truth run:", "Model-pool source run:",
    "Supplementary sealed authoritative run:"
  ),
}

def _remove_provenance(value):
    if isinstance(value,dict):
        return {key:_remove_provenance(item) for key,item in value.items()
                if key not in PROVENANCE_KEYS}
    if isinstance(value,list):
        return [_remove_provenance(item) for item in value]
    return value

def anonymize_review_copy(rel:str,dst:Path)->None:
    if rel in REVIEW_RECEIPTS:
        original=json.loads(dst.read_text(encoding="utf-8"))
        dst.write_text(json.dumps(_remove_provenance(original),indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    if rel in REVIEW_TEXT_PROVENANCE_LINES:
        starts=REVIEW_TEXT_PROVENANCE_LINES[rel]
        lines=[line for line in dst.read_text(encoding="utf-8").splitlines()
               if not line.startswith(starts)]
        dst.write_text("\n".join(lines)+"\n",encoding="utf-8")

def sha256(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)/"anonymous_process_information_review_bundle"
        root.mkdir()
        manifest=[]
        for rel in INCLUDE:
            src=ROOT/rel
            if not src.exists():
                raise SystemExit(f"missing required review file: {rel}")
            dst=root/rel
            dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(src,dst)
            anonymize_review_copy(rel,dst)
            manifest.append({"path":rel,"sha256":sha256(dst)})
        # Review-specific inert package initializers avoid loading unrelated
        # modules from the much larger source repository. Scientific modules above
        # remain verbatim copies (except provenance-only JSON/Markdown redaction).
        for rel in ("src/sdmr/__init__.py","src/sdmr/process_id/__init__.py",
                    "src/sdmr/process_id/known_truth/__init__.py"):
            target=root/rel
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text('"""Review-only minimal namespace, no package side effects."""\n',encoding="utf-8")
            manifest.append({"path":rel,"sha256":sha256(target)})
        req=root/"REQUIREMENTS_REVIEWERS.txt"
        req.write_text("numpy>=1.24\npandas>=2.0\nscikit-learn>=1.3\npytest>=8\n",encoding="utf-8")
        manifest.append({"path":"REQUIREMENTS_REVIEWERS.txt","sha256":sha256(req)})
        readme=root/"README_REVIEWERS.md"
        readme.write_text(
            "# Anonymous reviewer bundle\n\n"
            "The primary prospective known-truth metrics and the later FAILED real-plant v5 "
            "decision receipts are included for scientific audit. Model source files and "
            "focused tests are supplied without Git history.\n\n"
            "To run the three focused tests: install REQUIREMENTS_REVIEWERS.txt, "
            "then from this directory set PYTHONPATH=src and run "
            "python -m pytest -q tests/test_process_id_permutation_gate.py "
            "tests/test_process_id_scoped_pipeline_v6.py "
            "tests/test_process_id_prospective_kt_gate.py. The three small "
            "review-only __init__.py files deliberately omit unrelated package imports.\n\n"
            "For double-anonymous review only, run IDs, Git heads and archive artifact "
            "identifiers are removed from the copies in this ZIP. Frozen result counts, "
            "scores, confidence intervals, refusal decisions and learner diagnostics "
            "remain intact. Unredacted source receipts are retained outside this review "
            "bundle and can be verified after anonymized review.\n\n"
            "These compact receipts are not a rerunnable real-data fit: GBIF inputs, "
            "environmental rasters and fitted models are not bundled. The original "
            "failed empirical promotion remains closed and cannot be reinterpreted "
            "using post-terminal predictive scores.\n",
            encoding="utf-8",
        )
        manifest.append({"path":"README_REVIEWERS.md","sha256":sha256(readme)})
        (root/"MANIFEST.json").write_text(json.dumps({"files":manifest},indent=2)+"\n",encoding="utf-8")

        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() in {".py",".json",".md",".csv",".txt"}:
                text=path.read_text(encoding="utf-8",errors="ignore")
                for pattern in FORBIDDEN_PATTERNS:
                    if re.search(pattern,text,re.I):
                        raise SystemExit(f"identity/path leak in {path.relative_to(root)}: {pattern}")

        args.output.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(args.output,"w",compression=zipfile.ZIP_DEFLATED) as z:
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    z.write(path,path.relative_to(root.parent))
    print(args.output)

if __name__=="__main__":
    main()
