"""Guard legibility of M5 canonical figure labels without changing frozen outcomes."""
from pathlib import Path
import ast

ROOT=Path(__file__).resolve().parents[1]
BUILDER=ROOT/"manuscript"/"figures"/"build_process_information_figures.py"

def test_figure_headroom_and_title_spacing_are_explicit():
    source=BUILDER.read_text(encoding="utf-8")
    ast.parse(source)
    assert "ax.set_ylim(0, max(denominators) * 1.19)" in source
    assert 'ax.set_title("Prospective known-truth denominator and outcomes", pad=16)' in source
    assert "ax.set_ylim(0, 1.2)" in source
    assert 'ax.set_title("Authorization across prospective known-truth worlds", pad=16)' in source
    assert "value + 0.028" in source
    assert "min(1.02" not in source

def test_graphs_still_derive_exclusively_from_canonical_metrics():
    source=BUILDER.read_text(encoding="utf-8")
    assert '"sdmr_v6_prospective_known_truth_v2_metrics.json"' not in source
    assert '"sdmr_v6_prospective_kt_v2_metrics.json"' in source
    assert 'int(counts["replaceable"])' in source
    assert 'float(metrics["positive_recovery"])' in source
    assert 'float(data["metrics"]["w7_authorization_rate"])' in source
    assert '"figure3_prospective_denominator.svg"' in source
    assert '"figure4_world_authorization.svg"' in source
