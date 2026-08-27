"""Compose measured per-step drift along the OpenAlex depth distribution.

For share-type markers (hedge density, qualifier retention) retention at
depth d is read straight off the measured neutral-regime trajectory,
R(d) = mean(marker at generation d) / mean(marker at generation 0), for
d = 0..10. A geometric rho**d model was used in an earlier version and is
kept only as a reference field; it understates front-loaded loss because
it averages the first hop's drop over ten steps. The citation-weighted
expectation sum_d w_d R(d) over the depth distribution (depths 1-4, all
inside the measured range) gives the state of a claim at typical citation depth.
Null-finding survival at depth d comes straight from the H2 survival rows.

Policy quantity: d* = max measured depth with R(d) >= --threshold.

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

    # Fail on a missing input with the command that produces it, rather than
    # with a bare FileNotFoundError from three frames down.
    produced_by = {
        args.scores: "python -m src.score --chains 'data/chains_*.jsonl'",
        args.depths: "python -m src.openalex_depth --mailto you@example.com",
        args.results: "python -m src.analysis",
    }
    for path, cmd in produced_by.items():
        if not pathlib.Path(path).exists():
            raise SystemExit(
                f"{path} is missing. Produce it with\n  {cmd}\n"
                "or point the matching flag at the frozen copy under release/results/.")

    df = read_scores(args.scores)
    neutral = df[df["regime"] == "neutral"]
    depths = json.load(open(args.depths))
    dw = {int(k): v for k, v in depths["depth_weights"].items()}

    out = {"threshold": args.threshold,
           "median_depth": depths["median_depth"],
           "p90_depth": depths["p90_depth"], "markers": {}}
    traj = neutral.groupby("generation").mean(numeric_only=True)
    max_gen = int(traj.index.max())
    for marker in RATIO_MARKERS:
        curve = [float(traj.loc[d, marker] / traj.loc[0, marker])
                 for d in range(0, max_gen + 1)]
        rho = per_step_ratio(neutral, marker)
        med = depths["median_depth"]
        if max(dw) > max_gen:
            raise SystemExit(f"depth distribution reaches {max(dw)} hops "
                             f"but chains only go to {max_gen}")
        expected_at_consumption = sum(w * curve[d] for d, w in dw.items())
        dstar = 0
        for d in range(1, max_gen + 1):
            if curve[d] >= args.threshold:
                dstar = d
            else:
                break
        share_beyond_dstar = sum(w for d, w in dw.items() if d > dstar)
        out["markers"][marker] = {
            "retention_curve": curve,
            "first_hop_retention": curve[1],
            "retention_at_median_depth": curve[med] if med else None,
            "expected_retention_at_consumption": expected_at_consumption,
            "d_star": dstar,
            "d_star_is_measured_max": dstar == max_gen,
            "share_consumed_beyond_d_star": share_beyond_dstar,
            "geometric_rho_for_reference": rho,
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
        print(f"  {m}: R(1)={v['first_hop_retention']:.3f} "
              f"E[retention@consumption]={v['expected_retention_at_consumption']:.3f} "
              f"d*={v['d_star']}")


if __name__ == "__main__":
    main()
