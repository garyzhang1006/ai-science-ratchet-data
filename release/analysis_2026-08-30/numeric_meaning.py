"""Does exact numeric retention track preserved scientific meaning?

Numeric fidelity counts a number as kept when the same token appears in the
summary, which says nothing about whether it still attaches to the same
population, comparison, unit or finding. That construct gap has a measurable
signature: generations that keep their numbers while their entailment against
the source collapses. Counting them bounds how often high numeric fidelity
coexists with a summary the entailment scorer cannot support.
"""
import json, pathlib
import pandas as pd

REL = pathlib.Path(__file__).resolve().parents[1]
d = pd.read_csv(REL / "results/scores.csv.gz")
g = d[(d.generation > 0) & d.numeric_share_exact.notna()
      & (d.numeric_n_source > 0)].copy()

HI, LO = 0.80, 0.50
split = g[g.numeric_share_exact >= HI]
disc = split[split.fwd_entail < LO]
print(f"generations with a source statistic: {len(g)}")
print(f"  keeping at least {HI:.0%} of them exactly: {len(split)}")
print(f"  of those, forward entailment below {LO:.2f}: {len(disc)}"
      f"  ({100*len(disc)/len(split):.1f}%)")

by_reg = {}
for reg in ("neutral", "conservative"):
    s = split[split.regime == reg]
    dd = s[s.fwd_entail < LO]
    by_reg[reg] = dict(n_high_numeric=int(len(s)), n_discordant=int(len(dd)),
                       share=float(len(dd) / len(s)) if len(s) else None)
    print(f"  {reg:13s} {len(dd):4d}/{len(s):4d} = {100*len(dd)/max(len(s),1):.1f}%")

corr = g[["numeric_share_exact", "fwd_entail"]].corr().iloc[0, 1]
print(f"\nPearson r between numeric fidelity and forward entailment: {corr:.3f}")

sample = disc.sample(min(30, len(disc)), random_state=0)[
    ["pmid", "cls", "model", "regime", "generation",
     "numeric_share_exact", "fwd_entail"]]
sample.to_csv("numeric_meaning_sample.csv", index=False)

out = dict(n_with_source_statistic=int(len(g)),
           high_numeric_threshold=HI, low_entail_threshold=LO,
           n_high_numeric=int(len(split)), n_discordant=int(len(disc)),
           discordant_share=float(len(disc) / len(split)),
           by_regime=by_reg,
           pearson_numeric_vs_fwd_entail=float(corr),
           adjudication_sample_rows=int(len(sample)))
json.dump(out, open("numeric_meaning.json", "w"), indent=1)
print("wrote numeric_meaning.json and numeric_meaning_sample.csv")
