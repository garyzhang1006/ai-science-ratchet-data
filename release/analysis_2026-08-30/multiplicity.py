"""A single ledger of every test the paper reports, and what correction it carries.

The manuscript Holm-corrects five markers within each regime and says so, but it
also reports per-model estimates, a normalization check, an epistemic-hedge
subset, a continuous H2 regression in two windows, five H3 interactions and a
temperature arm. Counting them in one place shows how much of the paper is
confirmatory and how the exploratory results would fare under a correction they
were never given.
"""
import json, pathlib
import numpy as np

REL = pathlib.Path(__file__).resolve().parents[1]
res = json.load(open(REL / "results/results.json"))
pn = json.load(open(REL / "results/paper_numbers.json"))
sens = json.load(open(REL / "results/results_sensitivity.json"))

tests = []
for reg in ("neutral", "conservative"):
    for m in res["H1_per_step_drift"][reg]:
        tests.append(("confirmatory", f"H1 {m['marker']} {reg}",
                      m["p_holm"], "Holm within regime"))
for reg in ("neutral", "conservative"):
    p = res["H2_erosion"]["by_class"][reg]["logrank_null_vs_rest_p"]
    tests.append(("confirmatory", f"H2 log-rank {reg}", p, "none, preregistered"))
for k, v in res["H3_regime"].items():
    tests.append(("confirmatory", f"H3 interaction {k}",
                  pn["h3_interaction_p_holm"][k], "Holm across markers"))

ex = [("H2 continuous full chain", pn["h2_continuous_neutral"]["full_chain"]["extra_decay_null_p"]),
      ("H2 continuous after hop 1", pn["h2_continuous_neutral"]["after_first_hop"]["extra_decay_null_p"]),
      ("hedge count raw", pn["hedge_count_neutral"]["p"]),
      ("hedge density controlling words", pn["density_controlling_words"]["p"]),
      ("hedges per sentence", pn["hedges_per_sentence_neutral"]["p"]),
      ("epistemic-hedge subset", pn["hedge_density_epistemic_only_neutral"]["p"])]
for mdl, v in pn["hedge_density_by_model_neutral"].items():
    ex.append((f"per-model hedge density {mdl.split('/')[-1]}", v["p"]))
for m in sens["H1_per_step_drift"]["neutral"]:
    if m.get("p_holm") is not None and m.get("estimate") is not None:
        ex.append((f"temperature arm {m['marker']}", m["p_holm"]))
for name, p in ex:
    tests.append(("exploratory", name, p, "none"))

conf = [t for t in tests if t[0] == "confirmatory"]
expl = [t for t in tests if t[0] == "exploratory"]
print(f"confirmatory tests reported: {len(conf)}")
print(f"exploratory tests reported:  {len(expl)}")

ps = np.array([t[2] for t in expl], float)
order = np.argsort(ps)
m = len(ps)
holm = np.empty(m)
run = 0.0
for i, idx in enumerate(order):
    run = max(run, (m - i) * ps[idx])
    holm[idx] = min(1.0, run)
print("\nexploratory family, Holm across all of them")
surv = 0
for (kind, name, p, _), h in sorted(zip(expl, holm), key=lambda z: z[1]):
    flag = "survives" if h < 0.05 else "does not survive"
    if h < 0.05:
        surv += 1
    print(f"  {name:44s} raw={p:.3g}  Holm={h:.3g}  {flag}")
print(f"\n{surv} of {m} exploratory tests survive a Holm correction "
      "applied across the whole exploratory family")

out = dict(n_confirmatory=len(conf), n_exploratory=len(expl),
           n_exploratory_surviving_family_holm=int(surv),
           exploratory=[dict(name=n, p_raw=float(p), p_holm_family=float(h))
                        for (k, n, p, _), h in zip(expl, holm)])
json.dump(out, open("multiplicity.json", "w"), indent=1)
print("\nwrote multiplicity.json")
