"""Compose measured per-step drift along the OpenAlex depth distribution.

For share-type markers (hedge density, qualifier retention) the per-step
multiplicative retention ratio rho is estimated from the neutral-regime
trajectories as the mean of generation-over-generation ratios. Expected
retention at depth d is rho**d; the consumption-weighted expectation over
the depth distribution gives the state of a typically consumed claim.
Null-finding survival at depth d comes straight from the H2 survival rows.

Policy quantity: d* = max depth with expected retention >= --threshold.

Usage:
  python -m src.compose --scores results/scores.csv \
      --depths results/depth_distribution.json \
      --results results/results.json --out results/composed.json
"""
import argparse
import json
import pathlib

import numpy as np
import pandas as pd

import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
from src.io_utils import read_scores

RATIO_MARKERS = ["hedge_density", "qualifier_share"]


def per_step_ratio(df, marker):
    d = df.sort_values("generation").copy()
    g = d.groupby(["pmid", "model", "regime"])[marker]
    prev = g.shift(1)
    ratio = d[marker] / prev
    ratio = ratio.replace([np.inf, -np.inf], np.nan).dropna()
    # clip pathological single-chain explosions before averaging
    return float(ratio.clip(0, 3).mean())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scores", default="results/scores.csv")
    ap.add_argument("--depths", default="results/depth_distribution.json")
    ap.add_argument("--results", default="results/results.json")
    ap.add_argument("--out", default="results/composed.json")
    ap.add_argument("--threshold", type=float, default=0.5)
    args = ap.parse_args()

    df = read_scores(args.scores)
    neutral = df[df["regime"] == "neutral"]
    depths = json.load(open(args.depths))
    dw = {int(k): v for k, v in depths["depth_weights"].items()}

    out = {"threshold": args.threshold,
           "median_depth": depths["median_depth"],
           "p90_depth": depths["p90_depth"], "markers": {}}
    for marker in RATIO_MARKERS:
        rho = per_step_ratio(neutral, marker)
        med = depths["median_depth"]
        expected_at_consumption = sum(w * rho ** d for d, w in dw.items())
        # d* on integer depths 1..20
        dstar = 0
        for d in range(1, 21):
            if rho ** d >= args.threshold:
                dstar = d
            else:
                break
        share_beyond_dstar = sum(w for d, w in dw.items() if d > dstar)
        out["markers"][marker] = {
            "per_step_ratio": rho,
            "retention_at_median_depth": rho ** med if med else None,
            "expected_retention_at_consumption": expected_at_consumption,
            "d_star": dstar,
            "share_consumed_beyond_d_star": share_beyond_dstar,
        }

    # null-finding death by median depth, from H2 survival rows
    res = json.load(open(args.results))
    surv = res.get("H2_erosion", {}).get("survival_rows", [])
    med = depths["median_depth"]
    if surv and med:
        nul = [s for s in surv if s["cls"] == "null"
               and s["regime"] == "neutral"]
        if nul:
            dead = sum(1 for s in nul if s["event"] == 1 and s["time"] <= med)
            out["null_dead_by_median_depth_share"] = dead / len(nul)

    pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(out, f, indent=2)
    print(f"[compose] wrote {args.out}")
    for m, v in out["markers"].items():
        print(f"  {m}: rho={v['per_step_ratio']:.4f} "
              f"E[retention@consumption]={v['expected_retention_at_consumption']:.3f} "
              f"d*={v['d_star']}")


if __name__ == "__main__":
    main()
