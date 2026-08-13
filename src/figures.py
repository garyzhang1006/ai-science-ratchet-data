"""Paper figures and Table 1.

fig1  five panels, marker vs generation 0-10, one line per model x regime,
      per-step fixed effects inset from results.json
fig2  Kaplan-Meier survival of the core finding, by claim class, one panel
      per regime
fig3  left: intermediation-depth distribution; right: composed expected
      retention vs depth with policy threshold line
table1  LaTeX per-step fixed effects table

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
    fig, axes = plt.subplots(1, 5, figsize=(22, 4))
    for ax, marker in zip(axes, MARKERS):
        for (model, regime), sub in df.groupby(["model", "regime"]):
            traj = sub.groupby("generation")[marker].agg(["mean", "sem"])
            style = "-" if regime == "neutral" else "--"
            short = model.split("/")[-1]
            ax.errorbar(traj.index, traj["mean"], yerr=1.96 * traj["sem"],
                        linestyle=style, marker="o", markersize=3,
                        capsize=2, label=f"{short} ({regime})")
        ax.set_xlabel("Generation")
        ax.set_title(LABELS[marker], fontsize=10)
        est = next((r for r in results["H1_per_step_drift"].get("neutral", [])
                    if r["marker"] == marker and r.get("estimate") is not None),
                   None)
        if est:
            ax.annotate(f"drift {est['estimate']:+.3f}/step\n"
                        f"p={est['p_holm']:.3g}",
                        xy=(0.05, 0.05), xycoords="axes fraction", fontsize=8)
    axes[0].legend(fontsize=6, loc="upper right")
    fig.tight_layout()
    fig.savefig(outdir / "fig1_trajectories.pdf", bbox_inches="tight")
    plt.close(fig)


def fig2(results, outdir):
    surv = pd.DataFrame(results["H2_erosion"].get("survival_rows", []))
    if surv.empty:
        print("[figures] no survival rows; skipping fig2")
        return
    regimes = sorted(surv["regime"].unique())
    fig, axes = plt.subplots(1, len(regimes), figsize=(6 * len(regimes), 4),
                             squeeze=False)
    for ax, regime in zip(axes[0], regimes):
        sr = surv[surv["regime"] == regime]
        for cls in sorted(sr["cls"].unique()):
            sc = sr[sr["cls"] == cls]
            km = KaplanMeierFitter().fit(sc["time"], sc["event"], label=cls)
            km.plot_survival_function(ax=ax, ci_show=True)
        ax.set_title(f"{regime} regime")
        ax.set_xlabel("Generation")
        ax.set_ylabel("P(core finding survives)")
        ax.set_ylim(0, 1.02)
    fig.tight_layout()
    fig.savefig(outdir / "fig2_survival.pdf", bbox_inches="tight")
    plt.close(fig)


def fig3(depths, composed, outdir):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
    dw = {int(k): v for k, v in depths["depth_weights"].items()}
    ax1.bar(list(dw.keys()), list(dw.values()), color="steelblue")
    ax1.axvline(depths["median_depth"], color="k", linestyle=":",
                label=f"median = {depths['median_depth']}")
    ax1.set_xlabel("Intermediation depth (hops)")
    ax1.set_ylabel("Consumption weight")
    ax1.legend()

    xs = np.arange(0, 11)
    for marker, v in composed["markers"].items():
        ax2.plot(xs, v["per_step_ratio"] ** xs, marker="o", markersize=3,
                 label=LABELS.get(marker, marker))
    ax2.axhline(composed["threshold"], color="r", linestyle="--",
                label=f"calibration floor {composed['threshold']}")
    if depths["median_depth"]:
        ax2.axvline(depths["median_depth"], color="k", linestyle=":")
    ax2.set_xlabel("Depth (hops)")
    ax2.set_ylabel("Expected retention")
    ax2.set_ylim(0, 1.05)
    ax2.legend(fontsize=8)
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
