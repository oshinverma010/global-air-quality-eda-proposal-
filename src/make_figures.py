"""Draws the planning diagrams for the proposal using matplotlib only:
workflow flowchart, cleaning decision flowchart, Gantt chart and four wireframes.

Run from the project root:  python src/make_figures.py
Numbers quoted inside the cleaning flowchart are read from the profiling summary
(data/processed/profiling/profiling_summary.json) produced by src/profile_data.py.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon, Rectangle, Circle, FancyArrowPatch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import style  # noqa: E402
from style import (BLUE, ORANGE, AQUA, INK, INK2, MUTED, WF_FILL, WF_EDGE, WF_DARK, SEQ)

ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "data" / "processed" / "profiling" / "profiling_summary.json"

# group colours (tints for fills, full colour for edges / stripes)
GROUPS = {
    "data": (BLUE, "#e8f1fc"),
    "analysis": (AQUA, "#e3f6ee"),
    "comms": (ORANGE, "#fdebe3"),
}


# ----------------------------------------------------------------------------- helpers
def canvas(w, h, figsize):
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_xlim(0, w)
    ax.set_ylim(h, 0)  # y measured from the top
    ax.set_aspect("equal")
    ax.axis("off")
    fig.subplots_adjust(left=0.01, right=0.99, top=0.97, bottom=0.01)
    return fig, ax


def rbox(ax, x, y, w, h, fc="white", ec=INK2, lw=1.4, r=1.2, ls="-", z=2):
    p = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}",
                       fc=fc, ec=ec, lw=lw, ls=ls, zorder=z)
    ax.add_patch(p)
    return p


def txt(ax, x, y, s, size=9, weight="normal", color=INK, ha="center", va="center", style_="normal", z=5, **kw):
    return ax.text(x, y, s, fontsize=size, fontweight=weight, color=color, ha=ha, va=va,
                   fontstyle=style_, zorder=z, **kw)


def arrow(ax, p1, p2, color=INK2, lw=1.5, rad=0.0, z=3, ls="-"):
    a = FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=13, color=color, lw=lw,
                        connectionstyle=f"arc3,rad={rad}", zorder=z, ls=ls, shrinkA=0, shrinkB=0)
    ax.add_patch(a)


def poly_arrow(ax, pts, color=INK2, lw=1.5, z=3):
    xs, ys = zip(*pts[:-1])
    ax.plot(xs + (pts[-1][0],), ys + (pts[-1][1],), color=color, lw=lw, zorder=z, solid_capstyle="butt",
            alpha=0)  # invisible helper to keep limits
    for a, b in zip(pts[:-2], pts[1:-1]):
        ax.plot([a[0], b[0]], [a[1], b[1]], color=color, lw=lw, zorder=z, solid_capstyle="round")
    arrow(ax, pts[-2], pts[-1], color=color, lw=lw, z=z)


def diamond(ax, cx, cy, w, h, fc="white", ec=INK2, lw=1.4):
    ax.add_patch(Polygon([(cx, cy - h / 2), (cx + w / 2, cy), (cx, cy + h / 2), (cx - w / 2, cy)],
                         closed=True, fc=fc, ec=ec, lw=lw, zorder=2))


def badge(ax, x, y, n, fc=BLUE, size=8.5, r=1.9):
    ax.add_patch(Circle((x, y), r, fc=fc, ec="white", lw=1.2, zorder=6))
    txt(ax, x, y, str(n), size=size, weight="bold", color="white", z=7)


def hatch_placeholder(ax, x, y, w, h, label="", fc=WF_FILL, ec=WF_EDGE, size=9, cross=True):
    ax.add_patch(Rectangle((x, y), w, h, fc=fc, ec=ec, lw=1.2, zorder=2))
    if cross:
        ax.plot([x, x + w], [y, y + h], color=ec, lw=0.7, zorder=2.5, alpha=0.7)
        ax.plot([x, x + w], [y + h, y], color=ec, lw=0.7, zorder=2.5, alpha=0.7)
    if label:
        ax.text(x + w / 2, y + h / 2, label, fontsize=size, color=WF_DARK, ha="center", va="center", zorder=4,
                bbox=dict(fc=WF_FILL, ec="none", pad=6))


# ----------------------------------------------------------------------------- 1. workflow
def workflow():
    fig, ax = canvas(200, 126, (13, 8.2))
    txt(ax, 2, 4, "End-to-end workflow: CO2 emissions and economic development", size=14, weight="bold",
        ha="left")
    txt(ax, 2, 10, "Eight stages, three families of work; every stage produces a named, checkable output",
        size=9.5, color=INK2, ha="left")

    stages = [
        ("1", "Acquisition", "data", ["Download OWID CSV", "Call World Bank API (5 indicators)", "Store untouched in data/raw"],
         "raw files + download log"),
        ("2", "Validation", "data", ["Shape, dtypes, duplicates", "Missingness and coverage", "ISO3 key audit across sources"],
         "profiling tables + figures"),
        ("3", "Cleaning", "data", ["Drop aggregates to own table", "Patch / exclude unmatched keys", "Gap rules, outlier flags"],
         "clean country-year panel"),
        ("4", "Transformation", "analysis", ["Merge on ISO3 + year", "Log, growth, decoupling features", "Income / region groups"],
         "analysis-ready dataset"),
        ("5", "Exploration (EDA)", "analysis", ["Univariate and bivariate views", "Correlation, panel trends", "Rank-based tests, outliers"],
         "findings log"),
        ("6", "Visualization", "comms", ["One chart per question", "Colour-blind-safe palette", "Static figures + filters"],
         "figure set (PNG, 200 dpi)"),
        ("7", "Insights", "comms", ["Answer each key question", "State limits and caveats", "Separate fact from inference"],
         "insight summary"),
        ("8", "Reporting", "comms", ["Assemble report + README", "Reproducibility check", "Peer / self review"],
         "final report + repo"),
    ]
    bw, bh = 40, 34
    xs = [6 + i * 48.5 for i in range(4)]
    ys = [24, 76]
    pos = {}
    for i, (n, title, grp, lines, out) in enumerate(stages):
        x, y = xs[i % 4], ys[i // 4]
        pos[i] = (x, y)
        ec, tint = GROUPS[grp]
        rbox(ax, x, y, bw, bh, fc="white", ec=ec, lw=2)
        ax.add_patch(FancyBboxPatch((x, y), bw, 8.5, boxstyle="round,pad=0,rounding_size=1.2", fc=tint, ec=ec, lw=2, zorder=2.2))
        ax.add_patch(Rectangle((x + 0.8, y + 6), bw - 1.6, 2.4, fc=tint, ec="none", zorder=2.3))
        badge(ax, x + 5, y + 4.3, n, fc=ec)
        txt(ax, x + 10, y + 4.3, title, size=10.5, weight="bold", ha="left")
        for k, line in enumerate(lines):
            txt(ax, x + 3.5, y + 13.5 + k * 5.4, "• " + line, size=8.2, ha="left", color=INK)
        ax.plot([x + 2, x + bw - 2], [y + 27.2, y + 27.2], color=GRID_C, lw=1, zorder=3)
        txt(ax, x + bw / 2, y + 30.8, "Output: " + out, size=8, style_="italic", color=INK2)
    # arrows within rows
    for row in (0, 1):
        for c in range(3):
            i = row * 4 + c
            x, y = pos[i]
            arrow(ax, (x + bw + 0.4, y + bh / 2), (x + 48.5 - 0.4, y + bh / 2), lw=2)
    # elbow 4 -> 5
    x4, y4 = pos[3]
    x5, y5 = pos[4]
    poly_arrow(ax, [(x4 + bw / 2, y4 + bh + 0.5), (x4 + bw / 2, 67), (x5 + bw / 2, 67), (x5 + bw / 2, y5 - 0.5)], lw=2)
    # feedback 7 -> 5
    x7, y7 = pos[6]
    y_fb = y7 + bh + 7
    poly_arrow(ax, [(x7 + bw / 2, y7 + bh + 0.5), (x7 + bw / 2, y_fb), (x5 + bw / 2, y_fb), (x5 + bw / 2, y5 + bh + 0.8)],
               color=ORANGE, lw=1.8)
    txt(ax, (x5 + x7) / 2 + bw / 2, y_fb + 3.2, "iterate: new questions or data issues send the analysis back to EDA",
        size=8.3, color=INK2, style_="italic")
    # legend
    lx = 6
    for k, (g, lab) in enumerate([("data", "Data preparation"), ("analysis", "Analysis"), ("comms", "Communication")]):
        ec, tint = GROUPS[g]
        ax.add_patch(Rectangle((lx + k * 38, 15), 4.5, 3.2, fc=tint, ec=ec, lw=1.6, zorder=2))
        txt(ax, lx + k * 38 + 6.5, 16.6, lab, size=8.5, ha="left", color=INK2)
    style.save(fig, "fig_workflow_flowchart.png")


# ----------------------------------------------------------------------------- 2. cleaning
def cleaning():
    S = json.loads(SUMMARY.read_text(encoding="utf-8"))
    o, w, j = S["owid"], S["worldbank"], S["join"]
    fig, ax = canvas(150, 232, (10.5, 16.2))
    txt(ax, 2, 4, "Data cleaning decision flowchart", size=14, weight="bold", ha="left")
    txt(ax, 2, 10, "Green notes show what the preliminary profiling actually found at each decision point",
        size=9, color=INK2, ha="left")
    sx, bx = 40, 112  # spine x, branch x
    dw, dh = 54, 20

    def term(y, label):
        rbox(ax, sx - 37, y - 5, 74, 10, fc="#e8f1fc", ec=BLUE, lw=2, r=5)
        txt(ax, sx, y, label, size=9.5, weight="bold")

    def proc(y, label, h=14):
        rbox(ax, sx - 30, y - h / 2, 60, h, fc="white", ec=INK2)
        txt(ax, sx, y, label, size=8.8)

    def dec(y, label):
        diamond(ax, sx, y, dw + 8, dh + 2, fc="#fff8e6", ec=YELLOW_EDGE, lw=1.8)
        txt(ax, sx, y, label, size=8.4, weight="bold")

    def side(y, label, h=19, note=None):
        rbox(ax, bx - 31, y - h / 2, 62, h, fc="white", ec=INK2)
        txt(ax, bx, y - (2.2 if note else 0), label, size=8.2)
        if note:
            txt(ax, bx, y + h / 2 - 3.6, note, size=7.6, color="#0b6b4a", style_="italic")

    def yes(y_from, y_to_text_y, label="Yes"):
        arrow(ax, (sx + (dw + 8) / 2, y_from), (bx - 31, y_from), lw=1.6)
        txt(ax, sx + (dw + 8) / 2 + 3.6, y_from - 2.4, label, size=8.3, weight="bold", color=INK2)

    def no(y_from, y_to, label="No"):
        arrow(ax, (sx, y_from), (sx, y_to), lw=1.6)
        txt(ax, sx + 3.5, (y_from + y_to) / 2, label, size=8.3, weight="bold", color=INK2, ha="left")

    ys = [22, 42, 70, 101, 133, 165, 197, 222]
    term(ys[0], "Raw OWID CSV + World Bank API tables")
    arrow(ax, (sx, ys[0] + 5), (sx, ys[1] - 7), lw=1.6)
    proc(ys[1], "Type and schema checks\nyear → int, ISO → 3-letter string, values → numeric", 14)
    arrow(ax, (sx, ys[1] + 7), (sx, ys[2] - 11), lw=1.6)

    dec(ys[2], "Duplicate\n(country, year)?")
    yes(ys[2], 0)
    side(ys[2], "Keep one row per key (latest\nrelease wins); log the count",
         note=f"Found: {o['duplicate_country_year']} in OWID, "
              f"{w['duplicate_rows_entity_year_indicator']} in World Bank")
    no(ys[2] + 11, ys[3] - 11)

    dec(ys[3], "Row is a non-country\nentity?")
    yes(ys[3], 0)
    side(ys[3], "Move to a separate aggregates table;\nuse only as benchmarks (e.g. World)",
         note=f"Found: {o['n_non_country_entities']} OWID entities, {w['n_aggregates']} World Bank aggregates")
    no(ys[3] + 11, ys[4] - 11)

    dec(ys[4], "ISO3 code found\nin both sources?")
    arrow(ax, (sx + (dw + 8) / 2, ys[4]), (bx - 31, ys[4]), lw=1.6)
    txt(ax, sx + (dw + 8) / 2 + 3.6, ys[4] - 2.4, "No", size=8.3, weight="bold", color=INK2)
    side(ys[4], "Patch with a small crosswalk (e.g. Kosovo)\nor exclude and list in the cleaning log",
         note=f"Found: {j['owid_unmatched_n']} OWID-only, {j['wb_unmatched_n']} World Bank-only ISO codes")
    no(ys[4] + 11, ys[5] - 11, "Yes")

    dec(ys[5], "Missing value in\nthe 1990-2022 window?")
    yes(ys[5], 0)
    side(ys[5], "Outcome / key driver (CO2, GDP pc): leave\nmissing, drop from paired models.\nCovariate, gap ≤ 3 yrs: interpolate in-country.\nLonger gaps: keep NaN and flag",
         h=27, note=f"Found: CO2 {o['window_co2_pct_missing']}%, OWID GDP {o['window_gdp_pct_missing']}%,\nWB GDP pc {w['window_pct_missing_by_indicator']['gdp_per_capita_const2015usd']}% missing")
    no(ys[5] + 11, ys[6] - 11)

    dec(ys[6], "Value impossible\nor extreme?")
    yes(ys[6], 0)
    side(ys[6], "Impossible (negative CO2, share > 100):\nset to NaN + log.  Extreme but valid\n(Qatar): keep; use log scale / robust stats",
         h=27, note=f"Found: 0 impossible values; log10 outliers in 2022 CO2/cap: "
                    f"{o['outliers_co2_per_capita_2022_log']['n_outliers']}")
    no(ys[6] + 11, ys[7] - 5.5)
    term(ys[7], "Clean country-year panel + cleaning log")
    style.save(fig, "fig_cleaning_flowchart.png")


YELLOW_EDGE = "#c98500"
GRID_C = "#d9d7d2"


# ----------------------------------------------------------------------------- 3. gantt
def gantt():
    phases = [
        ("1  Planning and scoping", 3, "data", "Scope, questions, repo set-up"),
        ("2  Acquisition and validation", 4, "data", "Download, profile, key audit"),
        ("3  Cleaning and harmonisation", 6, "data", "Rules coded, cleaning log"),
        ("4  Transformation and features", 4, "analysis", "Merged panel, derived metrics"),
        ("5  Exploratory analysis", 6, "analysis", "Univariate to multivariate, tests"),
        ("6  Visualization build", 4, "comms", "Final figures, wireframes to charts"),
        ("7  Insight synthesis", 2, "comms", "Answer each key question"),
        ("8  Reporting and review", 3, "comms", "Write-up, README, repro check"),
    ]
    assert sum(p[1] for p in phases) == 32
    style.apply_style()
    fig, ax = plt.subplots(figsize=(12.5, 6.4))
    start = 0
    n = len(phases)
    for i, (name, hrs, grp, desc) in enumerate(phases):
        ec, tint = GROUPS[grp]
        y = n - 1 - i
        ax.barh(y, hrs, left=start, height=0.62, color=ec, edgecolor="white", lw=1.5, zorder=3)
        ax.text(start + hrs / 2, y, f"{hrs} h", ha="center", va="center", color="white", fontweight="bold",
                fontsize=10, zorder=4)
        ax.text(start + hrs + 0.3, y, desc, ha="left", va="center", fontsize=8.6, color=INK2, zorder=4)
        start += hrs
    ends = np.cumsum([p[1] for p in phases])
    for h, lab, idx in [(7, "M1  data validated", 1), (17, "M2  analysis-ready data", 3),
                        (27, "M3  figures final", 5), (32, "M4  report submitted", 7)]:
        y = n - 1 - idx
        ax.plot([h], [y - 0.52], marker="D", ms=8, color=INK, mec="white", zorder=5)
        ax.text(h + 0.45, y - 0.52, lab, fontsize=8, va="center", color=INK, zorder=5)
    # milestone key in the legend
    ax.set_yticks(range(n), [p[0] for p in phases][::-1], fontsize=10)
    ax.set_xlim(0, 38.5)
    ax.set_ylim(-0.8, n - 0.35)
    ax.set_xticks(range(0, 33, 4))
    ax.set_xlabel("Cumulative working hours (total = 32 h; about 8 h per week over four weeks)")
    for wk, x in enumerate([0, 8, 16, 24]):
        ax.axvspan(x, x + 8, ymin=0, ymax=1, color=("#f5f4f1" if wk % 2 == 0 else "white"), zorder=0)
        ax.text(x + 4, n - 0.42, f"Week {wk + 1}", ha="center", va="bottom", fontsize=9, color=INK2, fontweight="bold")
    ax.grid(axis="x", color=style.GRID, zorder=1)
    ax.grid(axis="y", visible=False)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    handles = [Rectangle((0, 0), 1, 1, color=GROUPS[g][0]) for g in ("data", "analysis", "comms")]
    from matplotlib.lines import Line2D
    handles.append(Line2D([0], [0], marker="D", color="none", markerfacecolor=INK, markeredgecolor="white", ms=8))
    ax.legend(handles, ["Data preparation", "Analysis", "Communication", "Milestone (M1 hour 7, M2 hour 17, M3 hour 27, M4 hour 32)"],
              loc="upper center", bbox_to_anchor=(0.45, -0.14), ncol=4, fontsize=8.6, handlelength=1.4)
    ax.set_title("Project timeline: eight phases, 32 hours", pad=22)
    style.save(fig, "fig_timeline_gantt.png")


# ----------------------------------------------------------------------------- wireframes
def frame(title, subtitle, figsize=(13, 7.8)):
    fig, ax = canvas(160, 96, figsize)
    ax.add_patch(Rectangle((0, 0), 160, 96, fc="white", ec=WF_EDGE, lw=1.8, zorder=1))
    ax.add_patch(Rectangle((0, 0), 160, 7, fc=WF_DARK, ec=WF_DARK, zorder=2))
    txt(ax, 3, 3.5, title, size=11, weight="bold", color="white", ha="left")
    txt(ax, 157, 3.5, "WIREFRAME  •  not real data", size=8, color="#d8d6d1", ha="right")
    txt(ax, 3, 11, subtitle, size=8.8, color=INK2, ha="left", style_="italic")
    return fig, ax


def dropdown(ax, x, y, w, label, h=5):
    ax.add_patch(Rectangle((x, y), w, h, fc="white", ec=WF_EDGE, lw=1.1, zorder=2))
    txt(ax, x + 1.5, y + h / 2, label, size=7.8, color=WF_DARK, ha="left")
    ax.add_patch(Polygon([(x + w - 4, y + h / 2 - 0.7), (x + w - 2, y + h / 2 - 0.7), (x + w - 3, y + h / 2 + 0.9)],
                         closed=True, fc=WF_DARK, ec="none", zorder=3))


def slider(ax, x, y, w, label, lo=0.15, hi=0.85):
    txt(ax, x, y - 2.4, label, size=7.8, color=WF_DARK, ha="left")
    ax.plot([x, x + w], [y + 1.5, y + 1.5], color=WF_EDGE, lw=2.5, zorder=2, solid_capstyle="round")
    ax.plot([x + lo * w, x + hi * w], [y + 1.5, y + 1.5], color=WF_DARK, lw=2.5, zorder=3, solid_capstyle="round")
    for f in (lo, hi):
        ax.add_patch(Circle((x + f * w, y + 1.5), 1.2, fc="white", ec=WF_DARK, lw=1.4, zorder=4))


def key_strip(ax, items, y=89.5):
    ax.add_patch(Rectangle((0, y - 2.8), 160, 9.3, fc="#f5f4f1", ec="none", zorder=1.5))
    n = len(items)
    for k, s in enumerate(items):
        x = 3 + k * (154 / n)
        badge(ax, x + 1.8, y + 0.6, k + 1, r=1.7, size=7.5)
        txt(ax, x + 4.6, y + 0.6, s, size=7.6, ha="left", color=INK)


def wireframe_1():
    fig, ax = frame("Page 1  Global overview", "Answers: how fast are emissions growing, and which income groups drive the trend?")
    # filter bar
    ax.add_patch(Rectangle((3, 14), 154, 9, fc=WF_FILL, ec=WF_EDGE, lw=1, zorder=2))
    slider(ax, 8, 18.6, 40, "Year range  1990 – 2022")
    dropdown(ax, 55, 15.8, 30, "Region: All")
    dropdown(ax, 90, 15.8, 30, "Income group: All")
    dropdown(ax, 125, 15.8, 29, "Unit: total / per capita")
    badge(ax, 4, 14, 1)
    # KPI cards
    kpis = ["Global CO2, latest year\n[ value ] Gt", "CO2 per person\n[ value ] t", "Change since 1990\n[ +/- % ]", "Countries with data\n[ n ] of 218"]
    for i, k in enumerate(kpis):
        x = 3 + i * 38.9
        rbox(ax, x, 26, 36.5, 15, fc="white", ec=WF_EDGE, lw=1.3, r=1)
        txt(ax, x + 18.2, 30.6, k.split("\n")[0], size=8, color=INK2)
        txt(ax, x + 18.2, 36.6, k.split("\n")[1], size=11, weight="bold", color=WF_DARK)
    badge(ax, 4, 26, 2)
    # main trend chart
    rbox(ax, 3, 44, 92, 42, fc="white", ec=WF_EDGE, lw=1.3, r=1)
    txt(ax, 6, 48, "Total CO2 by income group, 1990-2022", size=9, weight="bold", ha="left")
    ax.plot([9, 9, 92], [53, 82, 82], color=WF_DARK, lw=1.2, zorder=3)
    xs = np.linspace(11, 91, 40)
    rng = np.random.default_rng(3)
    for base, rise, c in [(72, 0.16, "#4b4a47"), (76, 0.085, "#8f8d87"), (79, 0.035, "#b9b7b0"), (81, 0.02, "#d0cec8")]:
        ys_ = base - (xs - 11) * rise + rng.normal(0, 0.18, len(xs))
        ax.plot(xs, ys_, color=c, lw=2, zorder=3)
    txt(ax, 50, 84.4, "year", size=7.5, color=INK2)
    for k, lab in enumerate(["High", "Upper-mid", "Lower-mid", "Low"]):
        ax.plot([42 + k * 13, 45 + k * 13], [51.5, 51.5], color=["#4b4a47", "#8f8d87", "#b9b7b0", "#d0cec8"][k], lw=2.5, zorder=3)
        txt(ax, 45.8 + k * 13, 51.5, lab, size=6.6, ha="left", color=INK2)
    badge(ax, 4, 44, 3)
    # stacked area by source
    rbox(ax, 99, 44, 58, 42, fc="white", ec=WF_EDGE, lw=1.3, r=1)
    txt(ax, 102, 48, "Emissions by fuel source (share)", size=9, weight="bold", ha="left")
    xs2 = np.linspace(104.5, 154, 40)
    t = (xs2 - 104.5) / 49.5
    shares = [0.30 + 0.06 * t, 0.30 - 0.03 * t, 0.16 + 0.05 * t, 0.24 - 0.08 * t]  # coal, oil, gas, other (illustrative only)
    fills = ["#4b4a47", "#8f8d87", "#b9b7b0", "#d0cec8"]
    bottom = np.zeros_like(xs2)
    for sh, c in zip(shares, fills):
        top = bottom + sh * 26
        ax.fill_between(xs2, 82 - bottom, 82 - top, color=c, zorder=2.5, lw=0)
        bottom = top
    ax.plot([104, 104, 154], [53, 82, 82], color=WF_DARK, lw=1.2, zorder=3)
    for k, lab in enumerate(["Coal", "Oil", "Gas", "Other"]):
        ax.add_patch(Rectangle((104 + k * 13, 49.7), 2.4, 2.4, fc=["#4b4a47", "#8f8d87", "#b9b7b0", "#d0cec8"][k], ec="none", zorder=3))
        txt(ax, 107.4 + k * 13, 50.9, lab, size=6.6, ha="left", color=INK2)
    badge(ax, 100, 44, 4)
    key_strip(ax, ["Global filters apply to every chart", "KPI tiles: one number each + change", "Line chart: ordered greys + legend (colour later)",
                   "Area chart: composition, not magnitude"])
    style.save(fig, "fig_wireframe_1.png")


def wireframe_2():
    fig, ax = frame("Page 2  Correlation explorer", "Answers: which drivers move together with CO2 per capita, and is the link linear or only monotonic?")
    # left: controls
    rbox(ax, 3, 14, 30, 72, fc=WF_FILL, ec=WF_EDGE, lw=1.2, r=1)
    txt(ax, 6, 18, "Controls", size=9, weight="bold", ha="left")
    dropdown(ax, 6, 22, 24, "Method: Spearman")
    dropdown(ax, 6, 30, 24, "Year: 2022")
    dropdown(ax, 6, 38, 24, "Group: All countries")
    txt(ax, 6, 48, "Variables", size=8, color=INK2, ha="left")
    for k, lab in enumerate(["CO2 per capita", "GDP per capita", "Energy per capita", "Industry % GDP", "Urban population %", "Coal share of CO2"]):
        ax.add_patch(Rectangle((6, 51 + k * 5.2), 2.4, 2.4, fc="white", ec=WF_DARK, lw=1.1, zorder=3))
        ax.plot([6.3, 7.1, 8.2], [52.4 + k * 5.2, 53.3 + k * 5.2, 51.3 + k * 5.2], color=WF_DARK, lw=1.1, zorder=4)
        txt(ax, 10, 52.2 + k * 5.2, lab, size=7.6, ha="left", color=INK)
    badge(ax, 4, 14, 1)
    # heatmap grid
    gx, gy, cs = 52, 24, 9.2
    n = 6
    rbox(ax, 36, 14, 77, 72, fc="white", ec=WF_EDGE, lw=1.2, r=1)
    txt(ax, 39, 18, "Correlation matrix (diverging scale, grey = 0)", size=9, weight="bold", ha="left")
    rng = np.random.default_rng(7)
    M = rng.uniform(-0.2, 0.9, (n, n))
    M = (M + M.T) / 2
    np.fill_diagonal(M, 1.0)
    for r_ in range(n):
        for c_ in range(n):
            v = M[r_, c_]
            g = 0.93 - 0.55 * abs(v)
            ax.add_patch(Rectangle((gx + c_ * cs, gy + r_ * cs), cs - 0.5, cs - 0.5, fc=(g, g, g), ec="white", lw=0.5, zorder=2))
            txt(ax, gx + c_ * cs + cs / 2, gy + r_ * cs + cs / 2, "r" if r_ != c_ else "1", size=7.2,
                color=("white" if abs(v) > 0.6 else WF_DARK), style_="italic")
    for k in range(n):
        txt(ax, gx + k * cs + cs / 2, gy - 3, f"V{k + 1}", size=7.2, color=INK2)
        txt(ax, gx - 3, gy + k * cs + cs / 2, f"V{k + 1}", size=7.2, color=INK2, ha="right")
    # colour bar
    for k in range(30):
        g = 0.93 - 0.55 * abs(k - 15) / 15
        ax.add_patch(Rectangle((gx + k * 1.8, 82), 1.8, 2.2, fc=(g, g, g), ec="none", zorder=2))
    txt(ax, gx - 1, 83, "-1", size=7, ha="right", color=INK2)
    txt(ax, gx + 54 + 1, 83, "+1", size=7, ha="left", color=INK2)
    badge(ax, 37, 14, 2)
    # right: scatter-matrix thumbnail + insight box
    rbox(ax, 116, 14, 41, 34, fc="white", ec=WF_EDGE, lw=1.2, r=1)
    txt(ax, 118.5, 18, "Pair preview (click a cell)", size=8.4, weight="bold", ha="left")
    for _ in range(26):
        ax.add_patch(Circle((rng.uniform(121, 152), rng.uniform(24, 43)), 0.8, fc="#8f8d87", ec="none", zorder=3))
    ax.plot([121, 154], [43, 25], color=WF_DARK, lw=1.5, zorder=4)
    badge(ax, 117, 14, 3)
    rbox(ax, 116, 51, 41, 35, fc=WF_FILL, ec=WF_EDGE, lw=1.2, r=1)
    txt(ax, 118.5, 55, "Reading guide", size=8.6, weight="bold", ha="left")
    for k, s in enumerate(["Strongest pair: [ V_a, V_b ]", "Weakest pair:   [ V_c, V_d ]", "Pearson vs Spearman gap", "flags non-linear links", "Click a cell: scatter + n"]):
        txt(ax, 118.5, 61 + k * 4.8, s, size=7.6, ha="left", color=INK)
    badge(ax, 117, 51, 4)
    key_strip(ax, ["Method and year toggles", "Heatmap: diverging blue-grey-orange", "Linked scatter for the selected pair", "Plain-language reading guide"])
    style.save(fig, "fig_wireframe_2.png")


def wireframe_3():
    fig, ax = frame("Page 3  Geography and rankings", "Answers: where are emissions per person highest, and who has changed most since 1990?")
    ax.add_patch(Rectangle((3, 14), 154, 9, fc=WF_FILL, ec=WF_EDGE, lw=1, zorder=2))
    dropdown(ax, 6, 15.8, 38, "Metric: CO2 per capita")
    dropdown(ax, 49, 15.8, 28, "Year: 2022")
    dropdown(ax, 82, 15.8, 34, "Compare with: 1990")
    dropdown(ax, 121, 15.8, 33, "Region: World")
    badge(ax, 4, 14, 1)
    # map
    hatch_placeholder(ax, 3, 26, 96, 50, "Choropleth map\n(one-hue sequential blues,\ngrey = no data)", size=9)
    for k in range(7):
        ax.add_patch(Rectangle((8 + k * 4, 69.5), 4, 2.4, fc=SEQ[k], ec="none", zorder=4))
    txt(ax, 7.5, 67.6, "low", size=6.8, ha="left", color=INK2)
    txt(ax, 36, 67.6, "high", size=6.8, ha="right", color=INK2)
    badge(ax, 4, 26, 2)
    # time slider
    slider(ax, 8, 82.5, 88, "Time slider (animate years)", lo=0.0, hi=0.78)
    badge(ax, 4, 78.8, 3)
    # top-N bars
    rbox(ax, 103, 26, 54, 38, fc="white", ec=WF_EDGE, lw=1.3, r=1)
    txt(ax, 106, 30, "Top 10 by selected metric", size=9, weight="bold", ha="left")
    for k in range(10):
        wdt = 34 - k * 2.6
        ax.add_patch(FancyBboxPatch((122, 33.5 + k * 2.9), wdt, 2.1, boxstyle="round,pad=0,rounding_size=0.5", fc="#6b6a66" if k < 3 else "#a9a7a1", ec="none", zorder=3))
        txt(ax, 120.5, 34.5 + k * 2.9, f"Country {k + 1}", size=6.6, ha="right", color=INK2)
    badge(ax, 104, 26, 4)
    # change panel
    rbox(ax, 103, 67, 54, 19, fc="white", ec=WF_EDGE, lw=1.3, r=1)
    txt(ax, 106, 71, "Biggest movers since 1990 (diverging)", size=8.6, weight="bold", ha="left")
    ax.plot([130, 130], [74, 84], color=WF_EDGE, lw=1, zorder=3)
    for k in range(4):
        ax.add_patch(Rectangle((130, 74.6 + k * 2.4), 12 - k * 2, 1.7, fc="#e8a889", ec="none", zorder=3))
        ax.add_patch(Rectangle((130 - (10 - k * 2), 74.6 + k * 2.4) if False else (130 - (11 - k * 2), 74.6 + k * 2.4), 11 - k * 2, 1.7, fc="#86b6ef", ec="none", zorder=3))
    txt(ax, 118, 85, "fell", size=6.8, color=INK2)
    txt(ax, 142, 85, "rose", size=6.8, color=INK2)
    badge(ax, 104, 67, 5)
    key_strip(ax, ["Metric, year, comparison year", "Map: sequential, never rainbow", "Time slider drives map and bars", "Top-N bars: ranked, labelled", "Diverging bars: change vs base year"])
    style.save(fig, "fig_wireframe_3.png")


def wireframe_4():
    fig, ax = frame("Page 4  Economy vs emissions", "Answers: how strongly does GDP per capita predict CO2 per capita, and does the link differ by income group?")
    # left filters
    rbox(ax, 3, 14, 30, 72, fc=WF_FILL, ec=WF_EDGE, lw=1.2, r=1)
    txt(ax, 6, 18, "Filters", size=9, weight="bold", ha="left")
    slider(ax, 6, 25, 24, "Year: 2022", lo=0.9, hi=0.9)
    dropdown(ax, 6, 33, 24, "Region: All")
    dropdown(ax, 6, 41, 24, "Income: All")
    txt(ax, 6, 51, "Axes", size=8, color=INK2, ha="left")
    for k, (lab, on) in enumerate([("Log scale", True), ("Label top 5 outliers", True), ("Size by population", False), ("Colour by income group", True)]):
        ax.add_patch(Rectangle((6, 54 + k * 5.4), 2.4, 2.4, fc="white", ec=WF_DARK, lw=1.1, zorder=3))
        if on:
            ax.plot([6.3, 7.1, 8.2], [55.4 + k * 5.4, 56.3 + k * 5.4, 54.3 + k * 5.4], color=WF_DARK, lw=1.1, zorder=4)
        txt(ax, 10, 55.2 + k * 5.4, lab, size=7.6, ha="left", color=INK)
    badge(ax, 4, 14, 1)
    # scatter
    rbox(ax, 36, 14, 80, 72, fc="white", ec=WF_EDGE, lw=1.2, r=1)
    txt(ax, 39, 18, "GDP per capita vs CO2 per capita (log-log)", size=9, weight="bold", ha="left")
    px, py, pw, ph = 46, 26, 62, 50
    ax.plot([px, px, px + pw], [py, py + ph, py + ph], color=WF_DARK, lw=1.2, zorder=3)
    rng = np.random.default_rng(11)
    xv = rng.uniform(0.03, 0.97, 70)
    yv = np.clip(0.12 + 0.75 * xv + rng.normal(0, 0.11, 70), 0.03, 0.97)
    shades = ["#4b4a47", "#8f8d87", "#b9b7b0", "#d0cec8"]
    for a, b, k in zip(xv, yv, rng.integers(0, 4, 70)):
        ax.add_patch(Circle((px + a * pw, py + ph - b * ph), 1.0, fc=shades[k], ec="white", lw=0.5, zorder=4))
    xl = np.linspace(0.02, 0.98, 20)
    ax.fill_between(px + xl * pw, py + ph - (0.12 + 0.75 * xl + 0.12) * ph, py + ph - (0.12 + 0.75 * xl - 0.12) * ph, color="#ecebe7", zorder=2.6)
    ax.plot(px + xl * pw, py + ph - (0.12 + 0.75 * xl) * ph, color=BLUE, lw=2, zorder=5)
    txt(ax, px + 40, py + ph + 4, "GDP per capita (log)", size=7.6, color=INK2)
    txt(ax, px - 5.5, py + ph / 2, "CO2 / capita\n(log)", size=7.4, color=INK2, rotation=90)
    txt(ax, px + 5, py + 4, "Regression line + 95% band", size=7.2, ha="left", color=BLUE, weight="bold")
    badge(ax, 37, 14, 2)
    # right: stats
    rbox(ax, 119, 14, 38, 34, fc="white", ec=WF_EDGE, lw=1.2, r=1)
    txt(ax, 121.5, 18, "Fit summary", size=8.8, weight="bold", ha="left")
    for k, s in enumerate(["n countries:  [ n ]", "Spearman rho:  [ r ]", "Slope (log-log):  [ b ]", "R squared:  [ value ]", "Bootstrap 95% CI:  [ lo, hi ]"]):
        txt(ax, 121.5, 24 + k * 4.6, s, size=7.6, ha="left", color=INK)
    badge(ax, 120, 14, 3)
    rbox(ax, 119, 51, 38, 35, fc=WF_FILL, ec=WF_EDGE, lw=1.2, r=1)
    txt(ax, 121.5, 55, "Hover tooltip (on point)", size=8.6, weight="bold", ha="left")
    for k, s in enumerate(["Country, income group", "GDP pc: [ value ]", "CO2 pc: [ value ]", "Residual vs fit: [ +/- ]", "Years in data: [ n ]"]):
        txt(ax, 121.5, 61 + k * 4.8, s, size=7.6, ha="left", color=INK)
    badge(ax, 120, 51, 4)
    key_strip(ax, ["Year, region, income filters", "Scatter + fitted line + band", "Statistics refresh with the filters", "Tooltip shows the residual"])
    style.save(fig, "fig_wireframe_4.png")


if __name__ == "__main__":
    style.apply_style()
    workflow()
    cleaning()
    gantt()
    wireframe_1()
    wireframe_2()
    wireframe_3()
    wireframe_4()
    print("figures written to", style.FIG_DIR)
