"""Hypothesis tests H1-H3 and all paper numbers.

H1  per-step drift: for each marker and regime, the mean of adjacent-
    generation differences, tested with a mixed model (random intercept per
    source abstract); falls back to OLS with cluster-robust SEs (clustered
    on abstract) when the mixed model fails or is degenerate. Holm
    correction across the five markers within each regime.
H2  erosion half-life: per chain, the first generation whose core-finding
    entailment drops below 0.5 (censored at max depth). Kaplan-Meier
    medians by claim class, log-rank test null vs non-null.
H3  regime effect: per marker, OLS of per-step differences on regime with
    cluster-robust SEs; reduction share and sign-flip check.

Writes results/results.json keyed to the paper's TK slots.

Usage:
  python -m src.analysis --scores results/scores.csv
"""
import argparse
import json
import math
import pathlib

import numpy as np
import pandas as pd

import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
from src.io_utils import read_scores
import statsmodels.api as sm
import statsmodels.formula.api as smf
from lifelines import KaplanMeierFitter
from lifelines.statistics import logrank_test

MARKERS = ["hedge_density", "causal_strength", "numeric_share_exact",
           "qualifier_share", "bi_entail"]
# +1 means the certainty ratchet predicts this marker RISES.
CERTAINTY_DIRECTION = {"hedge_density": -1, "causal_strength": +1,
                       "numeric_share_exact": -1, "qualifier_share": -1,
                       "bi_entail": -1}


def per_step_diffs(df: pd.DataFrame, marker: str) -> pd.DataFrame:
    d = df.sort_values("generation").copy()
    d["delta"] = d.groupby(["pmid", "model", "regime"])[marker].diff()
    return d.dropna(subset=["delta"])


def holm(pvals):
    """Holm step-down adjusted p-values, order preserved."""
    m = len(pvals)
    order = np.argsort(pvals)
    adj = np.empty(m)
    running = 0.0
    for rank, idx in enumerate(order):
        running = max(running, (m - rank) * pvals[idx])
        adj[idx] = min(1.0, running)
    return adj.tolist()


def drift_test(deltas: pd.DataFrame):
    """Mean per-step drift with mixed model; cluster-robust OLS fallback.
    Returns (estimate, se, pvalue, method)."""
    deltas = deltas.copy()
    deltas["const"] = 1.0
    try:
        mm = smf.mixedlm("delta ~ 1", deltas, groups=deltas["pmid"]).fit(
            reml=True, method="lbfgs")
        re_var = float(np.asarray(mm.cov_re).ravel()[0])
        degenerate = (not mm.converged) or re_var < 1e-10
        if not degenerate:
            return (float(mm.params["Intercept"]),
                    float(mm.bse["Intercept"]),
                    float(mm.pvalues["Intercept"]), "mixedlm")
    except Exception:
        pass
    ols = sm.OLS(deltas["delta"], deltas["const"]).fit(
        cov_type="cluster", cov_kwds={"groups": deltas["pmid"]})
    return (float(ols.params.iloc[0]), float(ols.bse.iloc[0]),
            float(ols.pvalues.iloc[0]), "ols_cluster")


def h1(df: pd.DataFrame):
    out = {}
    for regime in df["regime"].unique():
        sub = df[df["regime"] == regime]
        rows, pvals = [], []
        for marker in MARKERS:
            deltas = per_step_diffs(sub, marker)
            if len(deltas) < 10:
                rows.append({"marker": marker, "estimate": None,
                             "note": "insufficient data"})
                pvals.append(1.0)
                continue
            est, se, p, method = drift_test(deltas)
            direction_certainty = (
                "toward_certainty"
                if est * CERTAINTY_DIRECTION[marker] > 0
                else "away_from_certainty")
            rows.append({"marker": marker, "estimate": est, "se": se,
                         "p_raw": p, "method": method,
                         "n_deltas": int(len(deltas)),
                         "direction": direction_certainty})
            pvals.append(p)
        adj = holm(pvals)
        for r, pa in zip(rows, adj):
            r["p_holm"] = pa
            if "estimate" in r and r["estimate"] is not None:
                r["h1_verdict"] = (
                    "supported" if pa < 0.05
                    and r["direction"] == "toward_certainty"
                    else "reversed" if pa < 0.05 else "null")
        out[regime] = rows
    return out


def h2(df: pd.DataFrame, threshold: float = 0.5):
    chains = []
    n_unmeasured = 0
    for key, ch in df.groupby(["pmid", "model", "regime", "cls"]):
        # Chains with no NLI measurement (--no-nli runs, or an abstract with
        # no extractable core sentence) must not masquerade as survivors.
        ch = ch[(ch["generation"] == 0) | ch["core_entail"].notna()]
        ch = ch.sort_values("generation")
        if not (ch["generation"] > 0).any():
            n_unmeasured += 1
            continue
        fail = ch[(ch["generation"] > 0) & (ch["core_entail"] < threshold)]
        if len(fail):
            t, e = int(fail["generation"].iloc[0]), 1
        else:
            # censor at THIS chain's last measured generation, not the
            # dataset-wide max: an early-terminated chain was never
            # observed past its own last row
            t, e = int(ch["generation"].max()), 0
        chains.append({"pmid": str(key[0]), "model": str(key[1]),
                       "regime": str(key[2]), "cls": str(key[3]),
                       "time": t, "event": e})
    surv = pd.DataFrame(chains)
    if surv.empty or surv["event"].sum() == 0:
        return {"note": "no erosion events at threshold",
                "chains": len(surv), "unmeasured_chains": n_unmeasured}
    out = {"threshold": threshold, "n_chains": len(surv),
           "unmeasured_chains": n_unmeasured, "by_class": {}}
    for regime in surv["regime"].unique():
        sr = surv[surv["regime"] == regime]
        reg = {}
        for cls in sr["cls"].unique():
            sc = sr[sr["cls"] == cls]
            km = KaplanMeierFitter().fit(sc["time"], sc["event"])
            med = km.median_survival_time_
            reg[cls] = {"n": len(sc), "events": int(sc["event"].sum()),
                        "median_halflife":
                            None if math.isinf(med) else float(med)}
        nul = sr[sr["cls"] == "null"]
        pos = sr[sr["cls"] != "null"]
        if len(nul) and len(pos):
            lr = logrank_test(nul["time"], pos["time"],
                              nul["event"], pos["event"])
            reg["logrank_null_vs_rest_p"] = float(lr.p_value)
        out["by_class"][regime] = reg
    out["survival_rows"] = chains
    return out


def h3(df: pd.DataFrame):
    out = {}
    for marker in MARKERS:
        deltas = per_step_diffs(df, marker)
        if deltas["regime"].nunique() < 2 or len(deltas) < 20:
            out[marker] = {"note": "insufficient data"}
            continue
        deltas = deltas.copy()
        deltas["cons"] = (deltas["regime"] == "conservative").astype(float)
        X = sm.add_constant(deltas["cons"])
        fit = sm.OLS(deltas["delta"], X).fit(
            cov_type="cluster", cov_kwds={"groups": deltas["pmid"]})
        neut = float(fit.params["const"])
        cons = neut + float(fit.params["cons"])
        out[marker] = {
            "drift_neutral": neut,
            "drift_conservative": cons,
            "interaction_p": float(fit.pvalues["cons"]),
            "reduction_share": (None if abs(neut) < 1e-12
                                else 1.0 - abs(cons) / abs(neut)),
            "sign_flip": bool(neut * cons < 0),
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scores", default="results/scores.csv")
    ap.add_argument("--out", default="results/results.json")
    ap.add_argument("--h2-threshold", type=float, default=0.5)
    args = ap.parse_args()

    df = read_scores(args.scores)
    results = {
        "n_abstracts": int(df["pmid"].nunique()),
        "models": sorted(df["model"].unique().tolist()),
        "n_chains": int(df.groupby(["pmid", "model", "regime"]).ngroups),
        "max_depth": int(df["generation"].max()),
        "H1_per_step_drift": h1(df),
        "H2_erosion": h2(df, args.h2_threshold),
        "H3_regime": h3(df),
    }
    pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"[analysis] wrote {args.out}")
    for regime, rows in results["H1_per_step_drift"].items():
        for r in rows:
            if r.get("estimate") is not None:
                print(f"  H1 {regime:12s} {r['marker']:22s} "
                      f"{r['estimate']:+.4f} p_holm={r['p_holm']:.4g} "
                      f"{r.get('h1_verdict', '')}")


if __name__ == "__main__":
    main()
