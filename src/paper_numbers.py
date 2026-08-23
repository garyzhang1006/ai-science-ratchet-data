"""Every in-text paper number not already in results.json or composed.json.

results.json carries the three preregistered hypothesis tests; the paper
also reports trajectory endpoints, front-loading shares, per-model hedge
drift, word-count statistics, the hedge-count and length-control checks,
the continuous H2 regression, and one case-study chain. This script
recomputes all of those from the released scores and chains, so that the
reproducibility claim covers the running text and not only the tables.

Usage:
  python -m src.paper_numbers --release release
Writes <release>/results/paper_numbers.json.
"""
import argparse
import glob
import gzip
import json
import pathlib

import numpy as np
import pandas as pd
import statsmodels.api as sm

import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
from src.io_utils import read_scores
from src.instruments.hedges import hedge_count, word_count

CASE_PMID = "32938413"  # the subclinical-hypothyroidism null case study


def load_texts(release: pathlib.Path) -> pd.DataFrame:
    """All generations with text: gen 0 from the corpus, 1..D from chains."""
    rows = []
    for line in open(release / "abstracts.jsonl"):
        r = json.loads(line)
        rows.append({"pmid": str(r["pmid"]), "generation": 0,
                     "model": None, "regime": None, "text": r["abstract"]})
    for path in glob.glob(str(release / "chains" / "chains_*.jsonl.gz")):
        with gzip.open(path, "rt") as f:
            for line in f:
                r = json.loads(line)
                rows.append({"pmid": str(r["pmid"]),
                             "generation": int(r["generation"]),
                             "model": r["model"], "regime": r["regime"],
                             "text": r["text"]})
    df = pd.DataFrame(rows)
    df["n_words"] = df["text"].map(word_count)
    df["n_hedges"] = df["text"].map(hedge_count)
    return df


def expand_gen0(texts: pd.DataFrame) -> pd.DataFrame:
    """Replicate each source row into every (model, regime) chain so that
    per-chain differencing has a generation-0 baseline."""
    gen0 = texts[texts["generation"] == 0]
    chains = texts[texts["generation"] > 0][
        ["pmid", "model", "regime"]].drop_duplicates()
    base = chains.merge(gen0.drop(columns=["model", "regime"]), on="pmid")
    return pd.concat([base, texts[texts["generation"] > 0]],
                     ignore_index=True)


def cluster_drift(d: pd.DataFrame, col: str):
    """Mean adjacent-generation change with SEs clustered on abstract,
    matching the H1 fallback estimator in analysis.py."""
    d = d.sort_values("generation").copy()
    d["delta"] = d.groupby(["pmid", "model", "regime"])[col].diff()
    d = d.dropna(subset=["delta"])
    fit = sm.OLS(d["delta"], np.ones(len(d))).fit(
        cov_type="cluster", cov_kwds={"groups": d["pmid"]})
    return (float(fit.params.iloc[0]), float(fit.pvalues.iloc[0]),
            int(len(d)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", default="release")
    args = ap.parse_args()
    release = pathlib.Path(args.release)

    scores = read_scores(release / "results" / "scores.csv.gz")
    scores["pmid"] = scores["pmid"].astype(str)
    texts = expand_gen0(load_texts(release))
    texts["hedge_density"] = 100 * texts["n_hedges"] / texts["n_words"]
    neut = scores[scores["regime"] == "neutral"]
    cons = scores[scores["regime"] == "conservative"]
    tneut = texts[texts["regime"] == "neutral"]
    out = {}

    # Trajectory endpoints, pooled by generation.
    gmean = lambda df, col: df.groupby("generation")[col].mean()
    hedge = gmean(neut, "hedge_density")
    numeric = gmean(neut, "numeric_share_exact")
    qual = gmean(neut, "qualifier_share")
    out["trajectories_neutral"] = {
        "hedge_density_g0": round(hedge[0], 3),
        "hedge_density_g10": round(hedge[10], 3),
        "hedge_density_rise_pct": round(100 * (hedge[10] / hedge[0] - 1), 1),
        "numeric_g0": round(numeric[0], 3),
        "numeric_g1": round(numeric[1], 3),
        "numeric_g2": round(numeric[2], 3),
        "numeric_g4": round(numeric[4], 3),
        "numeric_g10": round(numeric[10], 3),
        "qualifier_g0": round(qual[0], 3),
        "qualifier_g10": round(qual[10], 3),
        "fwd_entail_g0": round(gmean(neut, "fwd_entail")[0], 3),
        "fwd_entail_g10": round(gmean(neut, "fwd_entail")[10], 3),
    }
    out["trajectories_conservative"] = {
        "numeric_g10": round(gmean(cons, "numeric_share_exact")[10], 3),
        "qualifier_g10": round(gmean(cons, "qualifier_share")[10], 3),
        "fwd_entail_g10": round(gmean(cons, "fwd_entail")[10], 3),
    }

    # Front-loading: the first hop's share of original content and of the
    # total loss incurred over all ten generations.
    out["front_loading"] = {
        "numeric_first_hop_share_of_original":
            round((numeric[0] - numeric[1]) / numeric[0], 3),
        "numeric_first_hop_share_of_total_loss":
            round((numeric[0] - numeric[1]) / (numeric[0] - numeric[10]), 3),
        "qualifier_first_hop_share_of_total_loss":
            round((qual[0] - qual[1]) / (qual[0] - qual[10]), 3),
    }

    # 95% CI on the headline estimate, normal reference as in analysis.py.
    r = json.load(open(release / "results" / "results.json"))
    hd = next(x for x in r["H1_per_step_drift"]["neutral"] if x["marker"] == "hedge_density")
    out["hedge_density_neutral_ci95"] = [round(hd["estimate"] - 1.96 * hd["se"], 3),
                                         round(hd["estimate"] + 1.96 * hd["se"], 3)]
    # H3 interaction p-values after Holm across the five markers.
    h3 = r["H3_regime"]
    ps = sorted((v["interaction_p"], k) for k, v in h3.items())
    m, running, holm = len(ps), 0.0, {}
    for rank, (pv, k) in enumerate(ps):
        running = max(running, (m - rank) * pv)
        holm[k] = float("%.3g" % min(1.0, running))
    out["h3_interaction_p_holm"] = holm

    # Per-model hedge-density drift, neutral regime.
    out["hedge_density_by_model_neutral"] = {}
    for model in sorted(neut["model"].unique()):
        est, p, _ = cluster_drift(neut[neut["model"] == model],
                                  "hedge_density")
        out["hedge_density_by_model_neutral"][model] = {
            "estimate": round(est, 4), "p": float(f"{p:.2e}")}

    # Hedge COUNT drift and word counts, neutral regime, from chain texts.
    est, p, n = cluster_drift(tneut, "n_hedges")
    words = tneut.groupby("generation")["n_words"].mean()
    out["hedge_count_neutral"] = {
        "per_step_drift": round(est, 4), "p": round(p, 3), "n_deltas": n}
    out["word_counts"] = {
        "source_mean": round(words[0], 1),
        "neutral_g1_mean": round(words[1], 1),
        "neutral_g10_mean": round(words[10], 1),
        "neutral_summary_mean": round(
            tneut[tneut["generation"] > 0]["n_words"].mean(), 1),
        "conservative_summary_mean": round(
            texts[(texts["regime"] == "conservative")
                  & (texts["generation"] > 0)]["n_words"].mean(), 1),
    }

    # Length control: per-step density change regressed on per-step word
    # change; the intercept is the density drift compression cannot explain.
    d = tneut.sort_values("generation").copy()
    g = d.groupby(["pmid", "model", "regime"])
    d["d_dens"] = g["hedge_density"].diff()
    d["d_words"] = g["n_words"].diff()
    d = d.dropna(subset=["d_dens", "d_words"])
    fit = sm.OLS(d["d_dens"], sm.add_constant(d["d_words"])).fit(
        cov_type="cluster", cov_kwds={"groups": d["pmid"]})
    out["density_controlling_words"] = {
        "intercept": round(float(fit.params["const"]), 4),
        "p": float(f"{fit.pvalues['const']:.2e}"),
        "word_slope": round(float(fit.params["d_words"]), 5),
    }

    # Continuous H2: core-finding entailment on generation x null indicator,
    # neutral regime, errors clustered on abstract. Reported on the full
    # chain and again on generations 1..D, i.e. after the first hop, because
    # the first hop carries most of the loss and a reader may want the
    # class gap net of it.
    core = neut.groupby(["cls", "generation"])["core_entail"].mean()
    out["h2_continuous_neutral"] = {
        "core_entail_g0_null": round(core["null"][0], 3),
        "core_entail_g10_null": round(core["null"][10], 3),
        "core_entail_g10_obs": round(core["obs"][10], 3),
        "core_entail_g10_rct": round(core["rct"][10], 3),
    }
    for label, first_gen in (("full_chain", 0), ("after_first_hop", 1)):
        h = neut.dropna(subset=["core_entail"])
        h = h[h["generation"] >= first_gen].copy()
        h["is_null"] = (h["cls"] == "null").astype(float)
        h["gen_x_null"] = h["generation"] * h["is_null"]
        X = sm.add_constant(h[["generation", "is_null", "gen_x_null"]])
        fit = sm.OLS(h["core_entail"], X).fit(
            cov_type="cluster", cov_kwds={"groups": h["pmid"]})
        base = float(fit.params["generation"])
        extra = float(fit.params["gen_x_null"])
        out["h2_continuous_neutral"][label] = {
            "generations": f"{first_gen}..10",
            "baseline_decay_per_gen": round(base, 4),
            "baseline_p": float(f"{fit.pvalues['generation']:.2g}"),
            "extra_decay_null": round(extra, 4),
            "extra_decay_null_p": float(f"{fit.pvalues['gen_x_null']:.2g}"),
            "null_rate_ratio": round((base + extra) / base, 2),
        }

    # Temperature arm comparison: greedy drift on the same 20 abstracts, so
    # the sensitivity estimates are compared like with like.
    sens_pmids = {str(json.loads(l)["pmid"])
                  for l in open(release / "abstracts_sensitivity.jsonl")}
    sub = neut[neut["pmid"].isin(sens_pmids)]
    out["greedy_drift_on_sensitivity_subset"] = {}
    for marker in ("hedge_density", "causal_strength",
                   "numeric_share_exact", "qualifier_share"):
        est, p, _ = cluster_drift(sub, marker)
        out["greedy_drift_on_sensitivity_subset"][marker] = {
            "estimate": round(est, 4), "p": float(f"{p:.2g}")}

    # H2 survival at depth ten: mean core-finding support by regime.
    out["h2_gen10_support"] = {
        "neutral": round(gmean(neut, "core_entail")[10], 3),
        "conservative": round(gmean(cons, "core_entail")[10], 3),
    }

    # Case study: the null abstract whose Qwen neutral chain loses all five
    # source p-values and its core finding at the first hop.
    case = scores[(scores["pmid"] == CASE_PMID) & (scores["regime"] == "neutral")
                  & (scores["model"] == "Qwen/Qwen2.5-7B-Instruct")]
    case = case.set_index("generation")
    out["case_study"] = {
        "pmid": CASE_PMID,
        "model": "Qwen/Qwen2.5-7B-Instruct",
        "numeric_n_source": int(case["numeric_n_source"].iloc[0]),
        "numeric_share_g1": float(case.loc[1, "numeric_share_exact"]),
        "numeric_share_g10": float(case.loc[10, "numeric_share_exact"]),
        "core_entail_g0": round(float(case.loc[0, "core_entail"]), 3),
        "core_entail_g1": round(float(case.loc[1, "core_entail"]), 3),
    }

    path = release / "results" / "paper_numbers.json"
    with open(path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"[paper_numbers] wrote {path}")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
