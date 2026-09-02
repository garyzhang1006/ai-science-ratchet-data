"""How much causal hardening could the causal-strength instrument have seen?

The positive control moved only 43% of abstracts when every association was
rewritten as unqualified causation, which invites the objection that the null
is an insensitivity artifact. Two quantities settle how much weight the null
carries: the share of sources already at the scale ceiling, where no further
hardening is representable, and the upper confidence bound on drift expressed
in units of the positive control's own effect.
"""
import json, pathlib
import numpy as np, pandas as pd

REL = pathlib.Path(__file__).resolve().parents[1]
sc = pd.read_csv(REL / "results/scores.csv.gz")
res = json.load(open(REL / "results/results.json"))
pc = json.load(open(REL / "results/positive_control.json"))

src = sc[sc.generation == 0].drop_duplicates("pmid")
dist = src.causal_strength.value_counts().sort_index()
n = len(src)
at_ceiling = int((src.causal_strength >= 5).sum())
at_four_plus = int((src.causal_strength >= 4).sum())
print("source causal-strength distribution over", n, "abstracts")
for k, v in dist.items():
    print(f"  {k}: {v:3d}  ({100*v/n:.0f}%)")
print(f"at ceiling (5): {at_ceiling} ({100*at_ceiling/n:.0f}%)")
print(f"at 4 or above:  {at_four_plus} ({100*at_four_plus/n:.0f}%)")

cs = [m for m in res["H1_per_step_drift"]["neutral"]
      if m["marker"] == "causal_strength"][0]
ub = cs["estimate"] + 1.96 * cs["se"]
chain_ub = 10 * ub
pc_shift = pc["causal_strengthen"]["mean_after"] - pc["causal_strengthen"]["mean_before"]
print(f"\nper-generation upper 95% bound: {ub:+.4f}")
print(f"over ten generations:           {chain_ub:+.4f} scale points")
print(f"positive-control shift:         {pc_shift:+.4f} scale points")
print(f"ratio: {chain_ub/pc_shift:.3f} of a full rewrite-to-causation effect")

moved = pc["causal_strengthen"]["share_moved_intended"]
print(f"\npositive control moved {100*moved:.0f}% of abstracts;"
      f" {100*at_four_plus/n:.0f}% of sources already sit at 4 or 5,"
      " where the intended rewrite has little room")

out = dict(n_sources=n,
           source_causal_distribution={str(k): int(v) for k, v in dist.items()},
           share_at_ceiling=at_ceiling / n,
           share_at_four_or_above=at_four_plus / n,
           per_gen_upper_bound=float(ub),
           ten_generation_upper_bound=float(chain_ub),
           positive_control_shift=float(pc_shift),
           bound_as_share_of_positive_control=float(chain_ub / pc_shift))
json.dump(out, open("causal_sensitivity.json", "w"), indent=1)
print("\nwrote causal_sensitivity.json")
