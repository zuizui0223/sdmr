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
  "evidence/mee_real_v5_receipts/README_EVIDENCE.md",
  "evidence/mee_real_v5_receipts/sdmr_fresh_empirical_v5_model_pool_diagnostic.json",
  "evidence/mee_real_v5_receipts/sdmr_fresh_empirical_v5_model_pool_terminal_decision.json",
  "evidence/mee_real_v5_receipts/sdmr_fresh_empirical_v5_sealed_promotion_result.json",
  "evidence/mee_real_v5_receipts/sdmr_fresh_empirical_v5_sealed_postterminal_receipt.json",
  "tests/test_process_id_permutation_gate.py",
  "tests/test_process_id_scoped_pipeline_v6.py",
  "tests/test_process_id_prospective_kt_gate.py",
]

FORBIDDEN_PATTERNS=[
  r"zuizui0223",
  r"github\.com/zuizui0223",
  r"@tohoku\.ac\.jp",
  r"/Users/",
  r"C:\\Users\\",
]

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
            manifest.append({"path":rel,"sha256":sha256(dst)})
        readme=root/"README_REVIEWERS.md"
        readme.write_text(
            "# Anonymous reviewer bundle\n\n"
            "This bundle contains the frozen method implementation, prospective known-truth "
            "contract, canonical metrics receipt, focused tests, real-data applicability disclosures, compact immutable terminal receipts and terminal result note used "
            "by the submitted manuscript. Git history and repository metadata are intentionally "
            "excluded for double-anonymous review.\n",
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
