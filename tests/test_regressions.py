"""Regression tests for the 9 confirmed review findings."""
import json
import math
import pathlib
import sys
import tempfile

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))

import pandas as pd
from src.instruments.causal import sentence_causal_strength
from src.instruments.numeric import extract_stats, numeric_fidelity
from src.instruments.qualifiers import extract_qualifiers
from src.fetch_abstracts import qualifies
from src.chains import chain_state
from src.analysis import h2
from src.openalex_depth import walk
import src.openalex_depth as oad
import random

ok = True


def check(name, cond):
    global ok
    print(("PASS " if cond else "FAIL ") + name)
    ok = ok and cond


# 1. RE_PERCENT must not count "95% CI" as a statistic
src = "Risk was reduced by 12% (OR 0.62, 95% CI 0.45-0.85; P=.01)."
vals = extract_stats(src)
check("percent: 95 excluded", 95.0 not in vals and 12.0 in vals)
nf = numeric_fidelity(src, "Risk was reduced, with a 95% confidence interval reported.")
check("percent: boilerplate-only gen scores 0", nf["share_exact"] == 0.0)

# 2. negation clause boundary
check("negation: cross-clause no ignored",
      sentence_causal_strength("There were no dropouts; the treatment reduced anxiety scores.") == 5)
check("negation: same-clause still works",
      sentence_causal_strength("The treatment did not reduce anxiety.") == 2)

# 3. -ing forms
check("ing: is lowering = 5",
      sentence_causal_strength("The drug is lowering blood pressure in patients.") == 5)
check("ing: is preventing = 5",
      sentence_causal_strength("The vaccine is preventing infection.") == 5)

# 4. population qualifier: numeric prefix + bare noun-with
q1 = extract_qualifiers("A total of 200 patients with type 2 diabetes were enrolled.")
check("pop: 'of 200 patients with X' extracted",
      any(k == "population" for k, _ in q1))
q2 = extract_qualifiers("Patients with hypertension received the drug.")
check("pop: bare 'patients with X' extracted",
      any(k == "population" for k, _ in q2))

# 5. stratification exclusivity, null-priority
null_rct = ("word " * 150 +
            "aOR 1.02, 95% CI 0.89 to 1.17. The intervention did not differ from control.")
check("strat: null-tail RCT rejected from rct", not qualifies("rct", null_rct))
check("strat: null-tail RCT accepted as null", qualifies("null", null_rct))
no_assoc = "word " * 150 + "There was no association between X and Y."
check("strat: negated assoc rejected from obs", not qualifies("obs", no_assoc))
pos_assoc = "word " * 150 + "Higher X was associated with lower Y risk."
check("strat: positive assoc accepted as obs", qualifies("obs", pos_assoc))

# 6. chains resume: generation-level, no duplication
with tempfile.TemporaryDirectory() as td:
    out = pathlib.Path(td) / "c.jsonl"
    with open(out, "w") as f:
        for g in range(1, 6):  # partial chain, gens 1-5 of 10
            f.write(json.dumps({"pmid": "p1", "model": "m", "regime": "neutral",
                                "generation": g, "text": f"t{g}"}) + "\n")
    st = chain_state(str(out))
    check("resume: partial chain state = (5, t5)",
          st[("p1", "m", "neutral")] == (5, "t5"))

# 7. H2 censoring per-chain + NaN exclusion
rows = []
for g in range(0, 11):  # full chain, survives
    rows.append({"pmid": "a", "model": "m", "regime": "neutral", "cls": "rct",
                 "generation": g, "core_entail": 0.9})
for g in range(0, 4):  # truncated chain, survives to gen 3 only
    rows.append({"pmid": "b", "model": "m", "regime": "neutral", "cls": "rct",
                 "generation": g, "core_entail": 0.9})
for g in range(0, 11):  # dies at gen 4
    rows.append({"pmid": "c", "model": "m", "regime": "neutral", "cls": "null",
                 "generation": g, "core_entail": 0.9 if g < 4 else 0.1})
for g in range(0, 11):  # unmeasured chain (all NaN)
    rows.append({"pmid": "d", "model": "m", "regime": "neutral", "cls": "null",
                 "generation": g, "core_entail": math.nan})
r = h2(pd.DataFrame(rows))
sr = {row["pmid"]: row for row in r["survival_rows"]}
check("h2: truncated chain censored at own max (3)",
      sr["b"]["time"] == 3 and sr["b"]["event"] == 0)
check("h2: full survivor censored at 10",
      sr["a"]["time"] == 10 and sr["a"]["event"] == 0)
check("h2: event at 4", sr["c"]["time"] == 4 and sr["c"]["event"] == 1)
check("h2: NaN chain excluded and counted",
      "d" not in sr and r["unmeasured_chains"] == 1)

# 8. openalex diamond: no double counting
graph = {"S": [{"id": "A", "type": "article", "title": "a", "cited_by_count": 0},
               {"id": "B", "type": "article", "title": "b", "cited_by_count": 0}],
         "A": [{"id": "D", "type": "article", "title": "d", "cited_by_count": 0}],
         "B": [{"id": "D", "type": "article", "title": "d", "cited_by_count": 0}],
         "D": [{"id": "E", "type": "article", "title": "e", "cited_by_count": 0}],
         "E": []}
oad.citing_works = lambda wid, mailto, per_page=50: graph.get(wid.rsplit("/", 1)[-1], [])
oad.time.sleep = lambda s: None
samples = walk({"id": "S"}, "", 4, 3, random.Random(0))
ids_sampled = len(samples)
check("openalex: diamond sampled once each (4 works)", ids_sampled == 4)

# 9. the class label "null" must survive CSV round-trip (pandas parses the
# bare string "null" as NaN by default, which silently drops a stratum)
import tempfile
from src.io_utils import read_scores
with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
    f.write("pmid,cls,model,regime,generation,hedge_density\n")
    f.write("1,null,m,neutral,0,0.5\n1,rct,m,neutral,0,0.5\n1,obs,m,neutral,0,\n")
    path = f.name
df = read_scores(path)
check("io: class label 'null' survives read_scores",
      sorted(df["cls"].astype(str)) == ["null", "obs", "rct"])
check("io: empty numeric cell still reads as NaN",
      df["hedge_density"].isna().sum() == 1)

print()
print("ALL PASS" if ok else "FAILURES PRESENT")
sys.exit(0 if ok else 1)
