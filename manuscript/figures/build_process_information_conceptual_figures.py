#!/usr/bin/env python3
"""Build manuscript Figures 1–2 from frozen process definitions, not outcomes.

Figure 1 is an explicitly schematic interpretation guide; Figure 2 lists the
eight named prospective known-truth worlds and their frozen authorization roles.
No model fitting, inference, or outcomes are read or recomputed here.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

INK = "#263342"
BORDER = "#8896a3"
PALE = "#f6f8fa"
ACCENT = "#216579"
SOFT = "#e8f2f5"
MUTED = "#586575"

WORLDS = [
    ("Unique process", "Thermal", "Distinct thermal signal in a declared predictor", "Informative"),
    ("Redundant representation", "Thermal", "Temperature and water predictors nearly coincide", "Informative"),
    ("Shared carrier", "Thermal + water", "Composite PET representation links both processes", "Informative"),
    ("Null correlated", "Thermal", "Seasonality tracks thermal signal;\ndoes not generate suitability", "Informative"),
    ("Interaction", "Thermal x water", "Suitability dominated by the thermal–water product", "Informative"),
    ("Observation confounded", "Thermal", "Sampling effort covaries with temperature", "Report-only"),
    ("Omitted driver", "Hidden driver", "Suitability driver is outside declared predictors", "Null control"),
    ("Geographic shift", "Thermal", "Elevation proxy reverses sign outside model pool", "Informative"),
]


def rounded(ax, x: float, y: float, w: float, h: float, label: str,
            *, face: str = "white", edge: str = BORDER, size: float = 11,
            weight: str = "normal", text_color: str = INK) -> None:
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.03,rounding_size=0.09",
        linewidth=0.95, edgecolor=edge, facecolor=face,
    ))
    ax.text(x + w / 2, y + h / 2, label, fontsize=size,
            color=text_color, ha="center", va="center", fontweight=weight)


def arrow(ax, x1: float, y1: float, x2: float, y2: float) -> None:
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2),
                                 arrowstyle="-|>", mutation_scale=11,
                                 color=MUTED, linewidth=1.25,
                                 shrinkA=3, shrinkB=4))


def base_figure(width: float, height: float, xmax: float, ymax: float):
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "svg.fonttype": "none",   # editable/searchable vector text
        "axes.unicode_minus": False,
    })
    fig, ax = plt.subplots(figsize=(width, height))
    fig.patch.set_facecolor("white")
    ax.set(xlim=(0, xmax), ylim=(0, ymax))
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    return fig, ax


def figure1(output: Path) -> None:
    fig, ax = base_figure(13.2, 7.25, 13.2, 7.25)
    ax.text(0.30, 6.79, "A  Declared carrier registry",
            fontsize=12, color=INK, fontweight="bold")
    ax.text(6.10, 6.79, "B  Information-state decision rules", fontsize=12,
            color=INK, fontweight="bold")
    ax.plot([5.83, 5.83], [0.75, 6.48], color="#d4dde4", lw=1)

    predictors = [
        ("Temperature (T)", 5.65),
        ("Elevation proxy (E)", 4.70),
        ("Shared PET (P)", 3.75),
        ("Water (W)", 2.80),
    ]
    for label, y in predictors:
        rounded(ax, 0.42, y, 2.08, 0.65, label, face=PALE, size=10.5)
    rounded(ax, 3.60, 4.73, 1.88, 0.70, "Thermal", face=SOFT, edge=ACCENT,
            weight="bold", size=11)
    rounded(ax, 3.60, 2.98, 1.88, 0.70, "Water", face=SOFT, edge=ACCENT,
            weight="bold", size=11)
    for coords in [
        (2.50, 5.97, 3.60, 5.15),
        (2.50, 5.02, 3.60, 5.08),
        (2.50, 4.08, 3.60, 4.98),
        (2.50, 4.08, 3.60, 3.43),
        (2.50, 3.12, 3.60, 3.36),
    ]:
        arrow(ax, *coords)
    rounded(ax, 0.38, 1.26, 5.28, 1.12,
            "Drop T only: E and P remain.\n"
            "Thermal-closure knockout: remove {T, E, P}.\n"
            "Deleting T alone cannot certify a thermal process state.",
            face="white", edge=BORDER, size=9.9)
    ax.text(0.46, 0.84, "Registry links are declared assumptions, not verified causes.",
            color=MUTED, fontsize=9.4)

    rules = [
        ("Full information system fails adequacy gate", "Unavailable"),
        ("Routes incomplete, intervals uncertain,\nor closures structurally inseparable", "Unresolved"),
        ("At least one adequate process-free\nroute is noninferior", "Replaceable"),
        ("All complete routes lose information;\na process-free route remains adequate", "Contributory"),
        ("All complete routes lose information;\nno process-free route remains adequate", "Required"),
    ]
    for i, (condition, state) in enumerate(rules):
        y = 5.84 - i * 1.02
        rounded(ax, 6.15, y, 4.30, 0.81, condition,
                face=PALE, size=10.6)
        arrow(ax, 10.49, y + 0.40, 10.72, y + 0.40)
        rounded(ax, 10.75, y, 2.02, 0.81, state,
                face=SOFT if state not in ("Unresolved", "Unavailable") else "white",
                edge=ACCENT if state not in ("Unresolved", "Unavailable") else BORDER,
                weight="bold", size=10.8)
    ax.text(6.16, 0.73,
            "Positive states require complete, interval-separated comparisons.\n"
            "These are information states within the frozen model, not physiological mechanisms.",
            color=MUTED, fontsize=9.25, ha="left")
    fig.savefig(output, format="svg", bbox_inches="tight", pad_inches=0.16)
    fig.savefig(output.with_suffix(".png"), format="png", dpi=170, bbox_inches="tight", pad_inches=0.16)
    plt.close(fig)


def figure2(output: Path) -> None:
    fig, ax = base_figure(13.25, 7.45, 13.25, 7.45)
    ax.text(0.30, 7.02, "Eight prospective known-truth world families",
            color=INK, fontsize=14, fontweight="bold")
    ax.text(0.30, 6.70,
            "Frozen world definitions and authorization roles; no outcome-dependent selection",
            fontsize=9.6, color=MUTED)

    x = (0.32, 2.92, 5.22, 11.37, 12.95)
    cols = ("World", "Generating signal", "Representation / observation challenge", "Role")
    head_y, head_h = 5.89, 0.62
    ax.add_patch(Rectangle((x[0], head_y), x[-1]-x[0], head_h,
                           linewidth=0, facecolor=SOFT))
    for i, label in enumerate(cols):
        ax.text(x[i] + 0.12, head_y + head_h/2, label,
                ha="left", va="center", fontsize=10.75,
                fontweight="bold", color=INK)
    row_h = 0.60
    for i, (name, process, challenge, role) in enumerate(WORLDS):
        y = head_y - (i + 1) * row_h
        if i % 2:
            ax.add_patch(Rectangle((x[0], y), x[-1]-x[0], row_h,
                                   facecolor=PALE, linewidth=0))
        label_size = 9.85 if len(name) > 18 else 10.2
        ax.text(x[0]+0.12, y + row_h/2, name, color=INK,
                fontsize=label_size, va="center", ha="left")
        ax.text(x[1]+0.12, y + row_h/2, process, color=INK,
                fontsize=10.1, va="center", ha="left")
        ax.text(x[2]+0.12, y + row_h/2, challenge, color=INK,
                fontsize=9.70, va="center", ha="left")
        ax.text(x[3]+0.12, y + row_h/2, role, color=ACCENT if role=="Informative" else INK,
                fontsize=10.0, va="center", ha="left",
                fontweight="bold" if role!="Informative" else "normal")
        ax.plot([x[0], x[-1]], [y, y], color="#dce4e9", linewidth=0.7)
    for v in x[1:-1]:
        ax.plot([v, v], [head_y - 8*row_h, head_y + head_h],
                color="#e2e8ed", linewidth=0.7)
    ax.text(0.36, 0.48,
            "Six informative controls enter the full-system authorization gate;\n"
            "observation confounding is report-only, and omitted-driver is the null.",
            fontsize=10, color=MUTED)
    fig.savefig(output, format="svg", bbox_inches="tight", pad_inches=0.16)
    fig.savefig(output.with_suffix(".png"), format="png", dpi=170, bbox_inches="tight", pad_inches=0.16)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    figure1(args.output_dir/"figure1_process_information_closure.svg")
    figure2(args.output_dir/"figure2_known_truth_worlds.svg")
    print(args.output_dir)


if __name__ == "__main__":
    main()
