from pathlib import Path
import json
import re
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
PAPER=ROOT/"manuscript"/"PROCESS_INFORMATION_MEE_SUBMISSION_V1.md"
BUNDLE=ROOT/"scripts"/"build_process_information_anonymous_review_bundle.py"


def test_mee_manuscript_has_required_initial_submission_structure():
    text=PAPER.read_text(encoding="utf-8")
    assert "## Abstract" in text
    abstract=text.split("## Abstract",1)[1].split("## 1. Introduction",1)[0]
    for n in range(1,5):
        assert re.search(rf"\n{n}\. ",abstract)
    assert "**Data/Code for peer review:**" in abstract
    assert "**Keywords:**" in abstract
    for heading in ("## 1. Introduction","## 2. Materials and Methods","## 3. Results","## 4. Discussion","## References"):
        assert heading in text


def test_mee_manuscript_is_within_word_ceiling_and_anonymous():
    text=PAPER.read_text(encoding="utf-8")
    words=re.findall(r"\b[\w'’-]+\b",text)
    assert len(words) < 8000
    lower=text.lower()
    assert "github.com/zuizui0223" not in lower
    assert "zuizui0223" not in lower
    assert "/users/" not in lower
    assert "c:\\users\\" not in lower


def test_anonymous_review_bundle_builds_without_identity_leak(tmp_path):
    out=tmp_path/"anonymous-review.zip"
    subprocess.run([sys.executable,str(BUNDLE),"--output",str(out)],check=True,cwd=ROOT)
    assert out.exists()
    with zipfile.ZipFile(out) as z:
        names=z.namelist()
        assert any(name.endswith("MANIFEST.json") for name in names)
        texts=[]
        for name in names:
            if Path(name).suffix.lower() in {".py",".json",".md",".csv",".txt"}:
                texts.append(z.read(name).decode("utf-8",errors="ignore").lower())
    joined="\n".join(texts)
    assert "zuizui0223" not in joined
    assert "github.com/zuizui0223" not in joined
