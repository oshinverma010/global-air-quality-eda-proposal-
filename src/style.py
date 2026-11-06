"""Shared matplotlib style for every figure in the project.

Colours come from a validated categorical palette (blue / orange / aqua first),
a one-hue blue sequential ramp and a blue-grey-orange diverging pair, so that
figures stay readable for colour-blind readers and in greyscale print.
"""
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "figures"

# Categorical slots (fixed order, never cycled)
BLUE, ORANGE, AQUA, YELLOW, MAGENTA = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"
VIOLET, RED = "#6250d6", "#e34948"
# Ink / surface
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#8b8a85"
SURFACE, GRID = "#ffffff", "#e6e5e1"
# Wireframe greys
WF_FILL, WF_EDGE, WF_DARK = "#eceae6", "#9a9892", "#4b4a47"
# One-hue sequential ramp (light -> dark)
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]


def apply_style() -> None:
    mpl.rcParams.update({
        "figure.dpi": 100,
        "savefig.dpi": 200,
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "axes.edgecolor": MUTED,
        "axes.labelcolor": INK2,
        "axes.titlecolor": INK,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "axes.axisbelow": True,
        "xtick.color": INK2,
        "ytick.color": INK2,
        "text.color": INK,
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "legend.frameon": False,
        "axes.prop_cycle": mpl.cycler(color=[BLUE, ORANGE, AQUA, YELLOW, MAGENTA, VIOLET, RED]),
    })


def save(fig, name: str) -> Path:
    FIG_DIR.mkdir(exist_ok=True)
    path = FIG_DIR / name
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)
    return path
