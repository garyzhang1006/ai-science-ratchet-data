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

REPO = "https://github.com/garyzhang1006/ai-science-ratchet-data"
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
