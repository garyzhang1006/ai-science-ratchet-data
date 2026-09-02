"""Verify the design claims the manuscript makes about independence and estimators.

Three claims are checked against the release rather than taken from the text.
Whether differencing really leaves no abstract-level variance for a random
intercept to absorb, which is the manuscript's reason for the clustered
fallback. Whether the cross-check scorer covers all 4,200 generations while the
primary scorer covers only the 3,600 main-arm ones. And how many independent
sources sit behind each headline denominator.
"""
import json, pathlib
import numpy as np, pandas as pd

REL = pathlib.Path(__file__).resolve().parents[1]
sc = pd.read_csv(REL / "results/scores.csv.gz")
sc["pmid"] = sc["pmid"].astype(str)
out = {}

print("== units of independence ==")
main = sc[sc.generation > 0]
out["n_scored_main"] = int(len(main))
out["n_sources"] = int(sc.pmid.nunique())
out["n_chains"] = int(main.groupby(["pmid", "model", "regime"]).ngroups)
print(f"main-arm scored generations {len(main)}, chains {out['n_chains']}, "
      f"independent sources {out['n_sources']}")
print(f"generations per source: {len(main)/out['n_sources']:.0f}")

print("\n== does differencing remove abstract-level variance ==")
for marker in ("hedge_density", "numeric_share_exact", "qualifier_share", "bi_entail"):
    d = sc.sort_values("generation").copy()
    d["delta"] = d.groupby(["pmid", "model", "regime"])[marker].diff()
    dd = d[(d.regime == "neutral") & d.delta.notna()]
    gm = dd.groupby("pmid").delta.mean()
    within = dd.groupby("pmid").delta.var(ddof=1).mean()
    between = gm.var(ddof=1)
    icc = between / (between + within) if (between + within) else float("nan")
    lvl = sc[(sc.regime == "neutral") & (sc.generation > 0)]
    lb = lvl.groupby("pmid")[marker].mean().var(ddof=1)
    lw = lvl.groupby("pmid")[marker].var(ddof=1).mean()
    icc_lvl = lb / (lb + lw) if (lb + lw) else float("nan")
    out.setdefault("icc", {})[marker] = {"levels": float(icc_lvl),
                                         "differences": float(icc)}
    print(f"  {marker:22s} ICC levels={icc_lvl:.3f}  ICC differences={icc:.3f}")

print("\n== scorer coverage by arm ==")
cc = pd.read_csv(REL / "results/scores_crosscheck.csv.gz")
sens = pd.read_csv(REL / "results/scores_sensitivity.csv.gz")
def cov(df, col):
    return int(df[col].notna().sum()) if col in df.columns else 0
out["crosscheck_rows"] = int(len(cc))
out["crosscheck_fwd_entail_nonnull"] = cov(cc, "fwd_entail")
out["sensitivity_rows"] = int(len(sens))
out["sensitivity_fwd_entail_nonnull"] = cov(sens, "fwd_entail")
out["primary_fwd_entail_nonnull_main"] = int(sc.fwd_entail.notna().sum())
print(f"  crosscheck table rows {len(cc)}, forward entailment populated "
      f"{out['crosscheck_fwd_entail_nonnull']}")
print(f"  sensitivity table rows {len(sens)}, forward entailment populated "
      f"{out['sensitivity_fwd_entail_nonnull']}")
print(f"  primary table rows {len(sc)}, forward entailment populated "
      f"{out['primary_fwd_entail_nonnull_main']}")
if "arm" in cc.columns:
    print("  crosscheck rows by arm:", cc.arm.value_counts().to_dict())
    out["crosscheck_by_arm"] = {k: int(v) for k, v in cc.arm.value_counts().items()}

json.dump(out, open("design_audit.json", "w"), indent=1)
print("\nwrote design_audit.json")
