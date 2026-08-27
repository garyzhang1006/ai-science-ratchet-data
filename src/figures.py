"""Paper figures and Table 1.

fig1  five panels, marker vs generation 0-10, one line per model x regime,
      per-generation fixed effects inset from results.json
fig2  Kaplan-Meier survival of the core finding, by claim class, one panel
      per regime
fig3  left: citation-depth distribution; right: composed expected
      retention vs depth with policy threshold line
table1  LaTeX per-generation fixed effects table

Usage:
  python -m src.figures --scores results/scores.csv \
      --results results/results.json --depths results/depth_distribution.json \
      --composed results/composed.json --outdir figures/out
"""
import argparse
import json
import pathlib

import matplotlib
matplotlib.use("Agg")

# NeurIPS text width is 5.5in. Each figure below is authored at close to its
# printed width and included at 0.98\linewidth, so the scale factor is about
# one and these point sizes are the sizes that reach the page. Authoring wide
# and letting \includegraphics shrink it is what made the earlier figures
# unreadable.
COLUMN_IN = 5.4
matplotlib.rcParams.update({
    "font.size": 6.5,
    "axes.titlesize": 7.0,
    "axes.labelsize": 6.5,
    "xtick.labelsize": 6.0,
    "ytick.labelsize": 6.0,
    "legend.fontsize": 5.8,
    "lines.linewidth": 0.9,
    "axes.linewidth": 0.6,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "xtick.major.size": 2.0,
    "ytick.major.size": 2.0,
})
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd

import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
from src.io_utils import read_scores  # noqa: E402
from lifelines import KaplanMeierFitter  # noqa: E402

MARKERS = ["hedge_density", "causal_strength", "numeric_share_exact",
           "qualifier_share", "bi_entail"]
LABELS = {"hedge_density": "Hedge density (/100w)",
          "causal_strength": "Causal strength (1-5)",
          "numeric_share_exact": "Numeric fidelity (exact share)",
          "qualifier_share": "Qualifier retention",
          "bi_entail": "Bidirectional entailment"}


def fig1(df, results, outdir):
    # Two rows of three so each panel is wide enough to read at column
    # width; the sixth cell carries the shared legend.
    fig, axes = plt.subplots(2, 3, figsize=(COLUMN_IN, 2.45))
    axes = axes.ravel()
    colors = {}
    for ax, marker in zip(axes[:5], MARKERS):
        for (model, regime), sub in df.groupby(["model", "regime"]):
            traj = sub.groupby("generation")[marker].agg(["mean", "sem"])
            style = "-" if regime == "neutral" else "--"
            short = model.split("/")[-1].replace("-Instruct", "").replace("-instruct", "")
            if short not in colors:
                colors[short] = "C%d" % len(colors)
            ax.errorbar(traj.index, traj["mean"], yerr=1.96 * traj["sem"],
                        linestyle=style, marker="o", markersize=2.5,
                        capsize=2, linewidth=1.2, color=colors[short],
                        label=f"{short}, {regime}")
        ax.set_xlabel("Generation")
        ax.set_xticks(range(0, 11, 2))
        ax.set_title(LABELS[marker].replace("/100w", "per 100 words"))
    handles, labels = axes[0].get_legend_handles_labels()
    axes[5].axis("off")
    axes[5].legend(handles, labels, loc="center", frameon=False,
                   title="solid: neutral, dashed: conservative")
    fig.tight_layout()
    fig.savefig(outdir / "fig1_trajectories.pdf", bbox_inches="tight")
    plt.close(fig)


def fig2(results, outdir):
    surv = pd.DataFrame(results["H2_erosion"].get("survival_rows", []))
    if surv.empty:
        print("[figures] no survival rows; skipping fig2")
        return
    # Neutral first, matching Table 1's column order and the order the
    # Results section discusses them in; alphabetical put conservative first.
    _order = {"neutral": 0, "conservative": 1}
    regimes = sorted(surv["regime"].unique(),
                     key=lambda r: (_order.get(r, 99), r))
    fig, axes = plt.subplots(1, len(regimes), figsize=(COLUMN_IN, 1.6),
                             squeeze=False)
    for ax, regime in zip(axes[0], regimes):
        sr = surv[surv["regime"] == regime]
        for cls in sorted(sr["cls"].unique()):
            sc = sr[sr["cls"] == cls]
            km = KaplanMeierFitter().fit(sc["time"], sc["event"], label=cls)
            km.plot_survival_function(ax=ax, ci_show=True)
        ax.set_title(f"{regime} regime")
        ax.set_xlabel("Generation")
        ax.set_xticks(range(0, 11, 2))
        ax.set_ylabel("P(core finding survives)")
        ax.set_ylim(0, 1.02)
    fig.tight_layout()
    fig.savefig(outdir / "fig2_survival.pdf", bbox_inches="tight")
    plt.close(fig)


def fig3(depths, composed, outdir):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(COLUMN_IN, 1.62))
    dw = {int(k): v for k, v in depths["depth_weights"].items()}
    ax1.bar(list(dw.keys()), list(dw.values()), color="steelblue")
    ax1.axvline(depths["median_depth"], color="k", linestyle=":",
                label=f"median = {depths['median_depth']}")
    ax1.set_xticks(sorted(dw))
    ax1.set_xlabel("Citation depth (hops)")
    ax1.set_ylabel("Citation weight")
    ax1.legend()

    for marker, v in composed["markers"].items():
        curve = v["retention_curve"]
        ax2.plot(np.arange(len(curve)), curve, marker="o", markersize=3,
                 label=LABELS.get(marker, marker))
    ax2.axhline(composed["threshold"], color="r", linestyle="--",
                label=f"calibration floor {composed['threshold']}")
    if depths["median_depth"]:
        ax2.axvline(depths["median_depth"], color="k", linestyle=":")
    ax2.set_xlabel("Citation depth (hops)")
    ax2.set_xticks(range(0, 11, 2))
    ax2.set_ylabel("Retention vs source")
    ax2.axhline(1.0, color="gray", linewidth=0.6)
    ax2.set_ylim(bottom=0)
    ax2.legend()
    fig.tight_layout()
    fig.savefig(outdir / "fig3_composition.pdf", bbox_inches="tight")
    plt.close(fig)


def table1(results, outdir):
    lines = [
        r"\begin{tabular}{lccc}", r"\toprule",
        r"Marker & Neutral regime & Conservative regime & H1 verdict \\",
        r"\midrule",
    ]
    neutral = {r["marker"]: r for r in
               results["H1_per_step_drift"].get("neutral", [])}
    cons = {r["marker"]: r for r in
            results["H1_per_step_drift"].get("conservative", [])}

    def cell(r):
        if not r or r.get("estimate") is None:
            return "--"
        stars = ("***" if r["p_holm"] < 0.001 else
                 "**" if r["p_holm"] < 0.01 else
                 "*" if r["p_holm"] < 0.05 else "")
        return f"${r['estimate']:+.4f}$ ({r['se']:.4f}){stars}"

    for m in MARKERS:
        n, c = neutral.get(m), cons.get(m)
        verdict = (n or {}).get("h1_verdict", "--")
        lines.append(f"{LABELS[m]} & {cell(n)} & {cell(c)} & {verdict} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (outdir / "table1.tex").write_text("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scores", default="results/scores.csv")
    ap.add_argument("--results", default="results/results.json")
    ap.add_argument("--depths", default="results/depth_distribution.json")
    ap.add_argument("--composed", default="results/composed.json")
    ap.add_argument("--outdir", default="figures/out")
    args = ap.parse_args()

    outdir = pathlib.Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    df = read_scores(args.scores)
    results = json.load(open(args.results))
    fig1(df, results, outdir)
    fig2(results, outdir)
    if pathlib.Path(args.depths).exists() and pathlib.Path(args.composed).exists():
        fig3(json.load(open(args.depths)), json.load(open(args.composed)),
             outdir)
    else:
        print("[figures] depth/composed files missing; skipping fig3")
    table1(results, outdir)
    print(f"[figures] wrote figures + table1 -> {outdir}")


if __name__ == "__main__":
    main()
