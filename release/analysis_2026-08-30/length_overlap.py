"""Post-hoc length-overlap analysis of the conservative-prompt effect.

The conservative prompt raises numeric fidelity and qualifier retention, and it
also raises summary length from 123 to 195 words. Both retention instruments
credit retained material, so the paper cannot say how much of the H3 gain is
length. This does NOT identify a length-independent effect. It asks a narrower
observational question: inside the region of realized lengths where the two
regimes actually overlap, and holding the source abstract fixed, how large is
the regime gap?
"""
import gzip, json, pathlib, itertools
import numpy as np, pandas as pd

REL = pathlib.Path(__file__).resolve().parents[1]

rows = []
for p in sorted((REL / "chains").glob("chains_*.jsonl.gz")):
    with gzip.open(p, "rt") as f:
        for line in f:
            r = json.loads(line)
            rows.append((r["pmid"], r["model"], r["regime"],
                         int(r["generation"]), len(r["text"].split())))
wc = pd.DataFrame(rows, columns=["pmid", "model", "regime", "generation", "words"])
wc["pmid"] = wc["pmid"].astype(str)

sc = pd.read_csv(REL / "results/scores.csv.gz")
sc["pmid"] = sc["pmid"].astype(str)
d = sc.merge(wc, on=["pmid", "model", "regime", "generation"], how="left")
gen = d[d.generation > 0].copy()
print("generations scored:", len(gen), "with word count:", gen.words.notna().sum())

for reg in ("neutral", "conservative"):
    s = gen[gen.regime == reg].words
    print(f"{reg:13s} n={len(s)} mean={s.mean():.1f} "
          f"p05={s.quantile(.05):.0f} p95={s.quantile(.95):.0f}")

lo = max(gen[gen.regime == "neutral"].words.quantile(.05),
         gen[gen.regime == "conservative"].words.quantile(.05))
hi = min(gen[gen.regime == "neutral"].words.quantile(.95),
         gen[gen.regime == "conservative"].words.quantile(.95))
ov = gen[(gen.words >= lo) & (gen.words <= hi)]
print(f"\noverlap band {lo:.0f} to {hi:.0f} words, n={len(ov)}, "
      f"neutral={(ov.regime=='neutral').sum()}, "
      f"conservative={(ov.regime=='conservative').sum()}")

def cluster_gap(df, col):
    """Regime gap in `col`, clustered on pmid, paired within abstract."""
    sub = df.dropna(subset=[col])
    per = sub.groupby(["pmid", "regime"])[col].mean().unstack()
    per = per.dropna()
    diff = per["conservative"] - per["neutral"]
    n = len(diff)
    if n < 3:
        return None
    se = diff.std(ddof=1) / np.sqrt(n)
    return dict(n_abstracts=int(n), gap=float(diff.mean()), se=float(se),
                ci_lo=float(diff.mean() - 1.96 * se),
                ci_hi=float(diff.mean() + 1.96 * se))

out = {"overlap_band_words": [float(lo), float(hi)],
       "n_in_band": int(len(ov)),
       "n_neutral_in_band": int((ov.regime == "neutral").sum()),
       "n_conservative_in_band": int((ov.regime == "conservative").sum())}
for col in ("numeric_share_exact", "qualifier_share", "fwd_entail"):
    out[col] = {"all_lengths": cluster_gap(gen, col),
                "overlap_band": cluster_gap(ov, col)}
    a, b = out[col]["all_lengths"], out[col]["overlap_band"]
    print(f"\n{col}")
    print(f"  all lengths   gap={a['gap']:+.4f} [{a['ci_lo']:+.4f},{a['ci_hi']:+.4f}] n={a['n_abstracts']}")
    if b:
        print(f"  overlap band  gap={b['gap']:+.4f} [{b['ci_lo']:+.4f},{b['ci_hi']:+.4f}] n={b['n_abstracts']}")
        print(f"  retained share of gap: {b['gap']/a['gap']:.2f}")
        out[col]["retained_share_of_gap"] = float(b["gap"] / a["gap"])

json.dump(out, open("length_overlap.json", "w"), indent=1)
print("\nwrote length_overlap.json")
