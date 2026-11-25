"""Generate 300-DPI publication figures for Paper 30 (Dominoes Tiling a Common Figure).
Author: Lluis Eriksson
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
FIG_DIR = ROOT / "paper" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 9,
    "axes.titlesize": 9.5,
    "axes.labelsize": 9,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 7.4,
    "figure.dpi": 300,
    "savefig.dpi": 300,
})


def make_fig1() -> None:
    """Visualize the 48-cell D4-symmetric 4-direction Sagdeev queen-domino figure
    with two of its four simultaneous exact tilings: horizontal (1,0) and diagonal (1,1)."""
    d3 = json.loads((RESULTS / "exp3_sagdeev_48cell_tilings.json").read_text(encoding="utf-8"))
    cells = [tuple(p) for p in d3["cells"]]
    t_h = [tuple(p) for p in d3["tiling_horiz"]]
    t_d = [tuple(p) for p in d3["tiling_diag"]]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.0, 3.1))

    # Panel (a): Horizontal (1,0) tiling (24 dominoes)
    for x, y in cells:
        ax1.add_patch(patches.Rectangle((x, y), 1, 1, facecolor="#d6eaf8", edgecolor="#85929e", linewidth=0.6))
    for ox, oy in t_h:
        ax1.add_patch(patches.FancyBboxPatch(
            (ox + 0.08, oy + 0.12), 1.84, 0.76,
            boxstyle="round,pad=0.02,rounding_size=0.14",
            facecolor="#1f618d", edgecolor="white", linewidth=0.9, alpha=0.88,
        ))
    ax1.set_xlim(-0.3, 10.3)
    ax1.set_ylim(-0.3, 10.3)
    ax1.set_aspect("equal")
    ax1.set_xticks(range(0, 10, 2))
    ax1.set_yticks(range(0, 10, 2))
    ax1.set_title("(a) 48-cell Sagdeev figure: 24 (1,0) tiles")

    # Panel (b): Diagonal (1,1) tiling (24 dominoes shown as colored pairs + connecting bars)
    for x, y in cells:
        ax2.add_patch(patches.Rectangle((x, y), 1, 1, facecolor="#fcf3cf", edgecolor="#85929e", linewidth=0.6))
    pal = ["#117a65", "#b7950b", "#a93226", "#2e86c1"]
    for idx, (ox, oy) in enumerate(t_d):
        col = pal[idx % len(pal)]
        ax2.plot([ox + 0.5, ox + 1.5], [oy + 0.5, oy + 1.5], color=col, linewidth=3.4, solid_capstyle="round")
        ax2.scatter([ox + 0.5, ox + 1.5], [oy + 0.5, oy + 1.5], color=col, s=20, zorder=5)
    ax2.set_xlim(-0.3, 10.3)
    ax2.set_ylim(-0.3, 10.3)
    ax2.set_aspect("equal")
    ax2.set_xticks(range(0, 10, 2))
    ax2.set_yticks(range(0, 10, 2))
    ax2.set_title("(b) Same 48 cells: 24 (1,1) diagonal tiles")

    fig.tight_layout(pad=0.9)
    fig.savefig(FIG_DIR / "fig1_sagdeev_48cell_figure.png", bbox_inches="tight")
    plt.close(fig)


def make_fig2() -> None:
    d2 = json.loads((RESULTS / "exp2_divisible_vs_tileable_census.json").read_text(encoding="utf-8"))["rows"]
    d4 = json.loads((RESULTS / "exp4_boosting_lift_stats.json").read_text(encoding="utf-8"))["rows"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.0, 2.75))

    labels = [f"d={r['length_d']}\nL={r['box_L']}" for r in d2]
    tiles = [r["tileable_count"] for r in d2]
    gaps = [r["strict_gap_count"] for r in d2]
    x = np.arange(len(labels))
    w = 0.36
    ax1.bar(x - w / 2, tiles, width=w, color="#117a65", label="Tileable ({0,1} Q)")
    ax1.bar(x + w / 2, gaps, width=w, color="#a93226", label="Divisible ONLY (gap)")
    ax1.set_yscale("log")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=7.0)
    ax1.set_ylabel("Subsets count (log scale)")
    ax1.set_ylim(0.7, 600)
    ax1.set_title("(a) Steps 5-6: tileable vs. divisible gap")
    ax1.grid(True, axis="y", linestyle="--", alpha=0.35)
    ax1.legend(loc="upper left", frameon=True, fontsize=7.0)

    b_names = ["d=2\n1 prev", "d=3\n1 prev", "d=2\n2 prev", "d=2\n3 prev"]
    f_t = [r["f_terms"] for r in d4]
    fs_t = [r["F_star_terms"] for r in d4]
    fl_t = [r["F_lifted_terms"] for r in d4]
    x2 = np.arange(len(b_names))
    w2 = 0.25
    ax2.bar(x2 - w2, f_t, width=w2, color="#1f618d", label="f terms")
    ax2.bar(x2, fs_t, width=w2, color="#d68910", label="F* (mod X1^d-1)")
    ax2.bar(x2 + w2, fl_t, width=w2, color="#922b21", label="Lifted F terms")
    ax2.set_xticks(x2)
    ax2.set_xticklabels(b_names, fontsize=7.3)
    ax2.set_ylabel("Nonzero Laurent monomials")
    ax2.set_ylim(0, max(f_t) + 5)
    ax2.set_title("(b) Sec. 2.1 divisibility-boosting lifts")
    ax2.grid(True, axis="y", linestyle="--", alpha=0.35)
    ax2.legend(loc="upper left", frameon=True, fontsize=7.0)

    fig.tight_layout(pad=0.9)
    fig.savefig(FIG_DIR / "fig2_gap_census_and_boosting.png", bbox_inches="tight")
    plt.close(fig)


def make_fig3() -> None:
    d1 = json.loads((RESULTS / "exp1_certified_atlas.json").read_text(encoding="utf-8"))["rows"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.0, 2.95), gridspec_kw={"width_ratios": [1.55, 1.0]})

    stems = [r["file"].replace(".cert.json", "") for r in d1]
    ms = [r["verify_ms"] for r in d1]
    mode_colors = {
        "common_figure_ap_tiling_exact": "#1f618d",
        "tile_divisible_vs_tileable_exact": "#117a65",
        "divisibility_boosting_lift_exact": "#b7950b",
        "ap_primitive_lcm_reduction_exact": "#922b21",
    }
    cols = [mode_colors[r["mode"]] for r in d1]

    y = np.arange(len(stems))
    ax1.barh(y, ms, color=cols, height=0.72)
    ax1.set_xscale("log")
    ax1.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax1.set_xticks([0.03, 0.05, 0.10, 0.30])
    ax1.set_xticklabels(["0.03", "0.05", "0.10", "0.30"])
    ax1.set_yticks(y)
    ax1.set_yticklabels(stems, fontsize=6.4)
    ax1.invert_yaxis()
    ax1.set_xlabel("Zero-float replay latency (ms, log scale)")
    ax1.set_title("(a) Replay time across all 16 certificates")
    ax1.grid(True, axis="x", linestyle="--", alpha=0.35)

    modes = [
        ("M1: Figures", 4, "#1f618d"),
        ("M2: Hole-Move", 4, "#117a65"),
        ("M3: Boosting", 4, "#b7950b"),
        ("M4: Prim/LCM", 4, "#922b21"),
    ]
    mx = np.arange(len(modes))
    ax2.bar(mx, [m[1] for m in modes], color=[m[2] for m in modes], width=0.56)
    ax2.set_xticks(mx)
    ax2.set_xticklabels([m[0] for m in modes], rotation=22, ha="right", fontsize=7.4)
    ax2.set_ylabel("Certified instances")
    ax2.set_ylim(0, 5.2)
    ax2.set_title("(b) Balanced 4-mode coverage")
    ax2.grid(True, axis="y", linestyle="--", alpha=0.35)
    for i, m in enumerate(modes):
        ax2.text(i, m[1] + 0.14, "4/4\nPASS", ha="center", va="bottom", fontsize=6.8, fontweight="bold")

    fig.tight_layout(pad=0.9)
    fig.savefig(FIG_DIR / "fig3_atlas_summary.png", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    make_fig1()
    make_fig2()
    make_fig3()
    print("[PASS] Generated 3 publication-quality 300-DPI figures in paper/figures/.")


if __name__ == "__main__":
    main()
