"""Kaggle kernel: NLI scoring (H2) plus the full downstream analysis.

Reads the released chains from the repo, runs bidirectional entailment and
core-finding survival on every generation, then runs analysis, composition,
and figures. Outputs everything the paper needs into /kaggle/working.

Runs on a T4 in a few minutes; also correct on a CPU-only kernel, just
slower. Set ACCEL in kernel-metadata.json accordingly.
"""
import os
import shutil
import subprocess
import sys

# Clone URL of the fork this kernel pulls its code and corpus from.
# push_kernels.sh substitutes it, or set RATCHET_REPO before running.
REPO = os.environ.get("RATCHET_REPO", "REPO_URL_PLACEHOLDER")
if not REPO.startswith(("http://", "https://", "git@")):
    raise SystemExit("Set RATCHET_REPO to your fork's clone URL, or let "
                     "kaggle/push_kernels.sh substitute it.")
os.environ["HF_HUB_DISABLE_XET"] = "1"


def sh(args):
    """Run and re-emit output line by line: Kaggle drops long subprocess
    stdout, so the notebook process must print it itself."""
    print("$ " + " ".join(args), flush=True)
    p = subprocess.Popen(args, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True)
    for line in p.stdout:
        print(line, end="", flush=True)
    p.wait()
    if p.returncode != 0:
        raise RuntimeError(f"command failed ({p.returncode}): {args}")


sh(["pip", "install", "-q", "lifelines", "transformers>=4.44", "sentencepiece"])

if os.path.isdir("repo"):
    sh(["git", "-C", "repo", "pull"])
else:
    sh(["git", "clone", REPO, "repo"])
os.chdir("repo")

# Decompress the released chains into the working layout score.py expects.
os.makedirs("data", exist_ok=True)
sh(["bash", "-c",
    "for f in release/chains/*.jsonl.gz; do "
    "gunzip -c \"$f\" > \"data/$(basename ${f%.gz})\"; done"])
sh(["bash", "-c", "wc -l data/chains_*.jsonl"])

import torch  # noqa: E402
print(f"[kernel] cuda={torch.cuda.is_available()} "
      f"device={'cuda' if torch.cuda.is_available() else 'cpu'}", flush=True)

W = "/kaggle/working"

# 0. Validate the entailment instrument before trusting anything built on
# it: a text must entail its own core sentence. The first run of this
# pipeline reported a clean H2 null that was entirely an artifact of this
# check failing (mean self-entailment 0.06), so the gate is hard.
sys.path.insert(0, os.getcwd())
import json as _json  # noqa: E402
from src.instruments.entailment import EntailmentScorer  # noqa: E402

_srcs = [_json.loads(l)["abstract"]
         for l in open("corpus/abstracts.jsonl")][:20]
_scorer = EntailmentScorer()
_self = _scorer.validate_self_entailment(_srcs)
print(f"[validate] mean self-entailment on 20 sources: {_self:.4f}", flush=True)
if _self < 0.80:
    raise SystemExit(
        f"[validate] FAILED: self-entailment {_self:.4f} < 0.80. The NLI "
        "instrument does not support claims drawn from its own premise, so "
        "H2 survival numbers would be meaningless. Fix the instrument "
        "before rerunning.")
del _scorer
if torch.cuda.is_available():
    torch.cuda.empty_cache()

# 1. Score every generation, entailment included.
sh([sys.executable, "-u", "-m", "src.score",
    "--abstracts", "corpus/abstracts.jsonl",
    "--chains", "data/chains_*.jsonl",
    "--out", f"{W}/scores.csv"])

# 2. H1-H3, with H2 now computable.
sh([sys.executable, "-u", "-m", "src.analysis",
    "--scores", f"{W}/scores.csv", "--out", f"{W}/results.json"])

# 3. Composition along the already-measured OpenAlex depth distribution.
shutil.copy("release/results/depth_distribution.json",
            f"{W}/depth_distribution.json")
sh([sys.executable, "-u", "-m", "src.compose",
    "--scores", f"{W}/scores.csv",
    "--depths", f"{W}/depth_distribution.json",
    "--results", f"{W}/results.json",
    "--out", f"{W}/composed.json"])

# 4. Figures and table 1, now including the survival panel.
sh([sys.executable, "-u", "-m", "src.figures",
    "--scores", f"{W}/scores.csv",
    "--results", f"{W}/results.json",
    "--depths", f"{W}/depth_distribution.json",
    "--composed", f"{W}/composed.json",
    "--outdir", f"{W}/figures"])

sh(["bash", "-c", f"gzip -f {W}/scores.csv"])
print("[kernel] DONE", flush=True)
