"""Kaggle kernel: independent NLI cross-check of the entailment arm.

The paper's entailment numbers come from one cross-encoder
(cross-encoder/nli-deberta-v3-base). A single scorer is a single point of
failure, and this pipeline already produced one artifact from exactly that
weakness. This kernel rescores every generation with a second model from a
different family and size (roberta-large-mnli, 355M, RoBERTa/MNLI against
184M DeBERTa-v3/multi-NLI), then asks three questions:

  1. Does the second model pass the same self-entailment gate?
  2. Do the two scorers agree per generation (Pearson, Spearman)?
  3. Does the paper's claim survive, that forward entailment falls far
     under neutral prompting and much less under conservative?

Agreement alone is not the test. The test is whether the conclusion holds.
"""
import json
import os
import subprocess
import sys

REPO = os.environ.get("RATCHET_REPO", "REPO_URL_PLACEHOLDER")
if not REPO.startswith(("http://", "https://", "git@")):
    raise SystemExit("Set RATCHET_REPO to the clone URL.")
os.environ["HF_HUB_DISABLE_XET"] = "1"

CROSS_MODEL = "roberta-large-mnli"
W = "/kaggle/working"


def sh(args):
    """Kaggle drops long subprocess stdout, so re-emit it line by line."""
    print("$ " + " ".join(args), flush=True)
    p = subprocess.Popen(args, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True)
    for line in p.stdout:
        print(line, end="", flush=True)
    p.wait()
    if p.returncode != 0:
        raise RuntimeError(f"command failed ({p.returncode}): {args}")


sh(["pip", "install", "-q", "transformers>=4.44", "sentencepiece", "scipy"])

if os.path.isdir("repo"):
    sh(["git", "-C", "repo", "pull"])
else:
    sh(["git", "clone", REPO, "repo"])
os.chdir("repo")
sys.path.insert(0, os.getcwd())

import csv                                            # noqa: E402
import gzip                                           # noqa: E402
import torch                                          # noqa: E402
from scipy import stats                               # noqa: E402
from src.instruments.entailment import EntailmentScorer   # noqa: E402

print(f"[kernel] cuda={torch.cuda.is_available()}", flush=True)

# ---------------------------------------------------------------- corpus
sources, cores = {}, {}
from src.instruments.causal import core_claim_sentence  # noqa: E402
for line in open("corpus/abstracts.jsonl"):
    d = json.loads(line)
    sources[str(d["pmid"])] = d["abstract"]
    cores[str(d["pmid"])] = core_claim_sentence(d["abstract"])
print(f"[corpus] {len(sources)} sources", flush=True)

# The sensitivity arm reuses every key of the main arm (pmid, model,
# regime, generation) at a different temperature, so the arm has to be
# carried explicitly or the two collide on join and on the regime means.
rows = []
import pathlib                                        # noqa: E402
for p in sorted(pathlib.Path("release/chains").glob("*.jsonl.gz")):
    arm = "sens" if p.name.startswith("sens_") else "main"
    with gzip.open(p, "rt") as fh:
        for line in fh:
            d = json.loads(line)
            if d.get("text", "").strip():
                d["arm"] = arm
                rows.append(d)
import collections as _c                              # noqa: E402
print(f"[chains] {len(rows)} generations "
      f"{dict(_c.Counter(r['arm'] for r in rows))}", flush=True)

# ------------------------------------------------------------ the scorer
scorer = EntailmentScorer(model_name=CROSS_MODEL, batch_size=64)
if torch.cuda.is_available():
    scorer.model = scorer.model.half()
print(f"[model] {CROSS_MODEL} on {scorer.device} "
      f"labels={scorer.model.config.id2label}", flush=True)

# Gate 1: the same self-entailment check that caught the original artifact.
# A model that fails this cannot adjudicate anything downstream.
self_scores = [scorer.core_survival(t, cores[k])
               for k, t in sources.items()]
self_scores = [s for s in self_scores if s == s]
self_mean = sum(self_scores) / len(self_scores)
print(f"[validate] self-entailment mean over {len(self_scores)} sources: "
      f"{self_mean:.4f}", flush=True)
gate_passed = self_mean >= 0.80
if not gate_passed:
    print("[validate] WARNING: the cross-check model FAILS the gate that "
          "the primary model passes at 0.955. Its disagreement with the "
          "primary scorer would then be evidence about this model, not "
          "about the paper's numbers. Scoring continues so the failure is "
          "documented with data.", flush=True)

# ---------------------------------------------------------------- score
out = []
for i, d in enumerate(rows):
    src = sources[str(d["pmid"])]
    b = scorer.bidirectional(src, d["text"])
    b["core_entail"] = scorer.core_survival(d["text"], cores[str(d["pmid"])])
    b.update({k: d[k] for k in ("pmid", "cls", "model", "regime",
                                "generation", "arm")})
    out.append(b)
    if (i + 1) % 250 == 0:
        print(f"[score] {i + 1}/{len(rows)}", flush=True)

FIELDS = ["fwd_entail", "fwd_contra", "bwd_entail", "bwd_contra",
          "bi_entail", "core_entail", "pmid", "cls", "model", "regime",
          "generation", "arm"]
with gzip.open(f"{W}/scores_crosscheck.csv.gz", "wt", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=FIELDS)
    w.writeheader()
    for r in out:
        w.writerow({k: r[k] for k in FIELDS})
print(f"[write] {W}/scores_crosscheck.csv.gz", flush=True)

# ------------------------------------------------- agreement and verdict
def key(r):
    return (str(r["pmid"]), r["model"], r["regime"], int(r["generation"]))


primary = {}
for arm, path in (("main", "release/results/scores.csv.gz"),
                  ("sens", "release/results/scores_sensitivity.csv.gz")):
    with gzip.open(path, "rt") as fh:
        for r in csv.DictReader(fh):
            primary[(arm,) + key(r)] = r

paired = [(primary[(r["arm"],) + key(r)], r)
          for r in out if (r["arm"],) + key(r) in primary]
main_paired = [(p, q) for p, q in paired if q["arm"] == "main"]
print(f"[join] {len(paired)} of {len(out)} matched "
      f"({len(main_paired)} in the main arm)", flush=True)

agree = {}
for f in ("fwd_entail", "bwd_entail", "bi_entail", "core_entail"):
    a = [float(p[f]) for p, q in paired if p[f] not in ("", "nan")
         and q[f] == q[f]]
    b = [q[f] for p, q in paired if p[f] not in ("", "nan") and q[f] == q[f]]
    agree[f] = {"n": len(a),
                "pearson_r": float(stats.pearsonr(a, b)[0]),
                "spearman_rho": float(stats.spearmanr(a, b)[0]),
                "mean_primary": sum(a) / len(a),
                "mean_crosscheck": sum(b) / len(b)}
    print(f"[agree] {f}: r={agree[f]['pearson_r']:.3f} "
          f"rho={agree[f]['spearman_rho']:.3f} n={len(a)}", flush=True)


def endpoints(recs, getter):
    """Mean forward entailment at generation 1 and generation 10 by regime.

    Generation 0 is the source scored against itself, so the drift the
    paper reports runs from the first machine summary onward."""
    o = {}
    for reg in ("neutral", "conservative"):
        for g in (1, 10):
            v = [getter(r) for r in recs
                 if r["regime"] == reg and int(r["generation"]) == g
                 and getter(r) == getter(r)]
            o[f"{reg}_g{g}"] = sum(v) / len(v) if v else float("nan")
    return o


# Main arm only: the sensitivity arm is neutral-only at a different
# temperature and would bias the neutral mean it is compared against.
prim_ep = endpoints([p for p, q in main_paired],
                    lambda r: float(r["fwd_entail"]))
cross_ep = endpoints([q for p, q in main_paired], lambda r: r["fwd_entail"])
print(f"[endpoints] primary    {prim_ep}", flush=True)
print(f"[endpoints] crosscheck {cross_ep}", flush=True)

# The paper's claim is that conservative prompting preserves forward
# entailment and neutral prompting does not. The chains carry no
# generation 0 (that row is the source scored against itself), so the
# claim is tested where both scorers have data: the regime gap at
# generation 10, plus the drop from generation 1 as a secondary read.
prim_gap = prim_ep["conservative_g10"] - prim_ep["neutral_g10"]
cross_gap = cross_ep["conservative_g10"] - cross_ep["neutral_g10"]
prim_drop_n = prim_ep["neutral_g1"] - prim_ep["neutral_g10"]
prim_drop_c = prim_ep["conservative_g1"] - prim_ep["conservative_g10"]
cross_drop_n = cross_ep["neutral_g1"] - cross_ep["neutral_g10"]
cross_drop_c = cross_ep["conservative_g1"] - cross_ep["conservative_g10"]
reproduced = (prim_gap > 0) and (cross_gap > 0)

verdict = {
    "cross_model": CROSS_MODEL,
    "primary_model": "cross-encoder/nli-deberta-v3-base",
    "self_entailment_mean": self_mean,
    "self_entailment_gate_passed": gate_passed,
    "n_generations": len(out),
    "n_paired": len(paired),
    "n_paired_main_arm": len(main_paired),
    "agreement": agree,
    "fwd_entail_endpoints_primary": prim_ep,
    "fwd_entail_endpoints_crosscheck": cross_ep,
    "regime_gap_g10_primary": prim_gap,
    "regime_gap_g10_crosscheck": cross_gap,
    "neutral_minus_conservative_drop_primary": prim_drop_n - prim_drop_c,
    "neutral_minus_conservative_drop_crosscheck": cross_drop_n - cross_drop_c,
    "regime_contrast_sign_reproduced": bool(reproduced),
}
with open(f"{W}/nli_crosscheck.json", "w") as fh:
    json.dump(verdict, fh, indent=2)
print(json.dumps(verdict, indent=2), flush=True)
print("[done]", flush=True)
