"""Kaggle CPU kernel: recompute the composition, the depth distribution,
the figures, and the instrument positive controls from the released data.

No GPU. Needs internet for the OpenAlex walk. Everything lands in
/kaggle/working and is also echoed to the log so the numbers survive even
if the output download is slow.
"""
import json
import os
import subprocess
import sys

REPO = "https://github.com/garyzhang1006/ai-science-ratchet-data"
W = "/kaggle/working"


def sh(args):
    print("$ " + " ".join(args), flush=True)
    p = subprocess.Popen(args, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True)
    for line in p.stdout:
        print(line, end="", flush=True)
    p.wait()
    if p.returncode != 0:
        raise RuntimeError(f"command failed ({p.returncode}): {args}")


sh(["pip", "install", "-q", "lifelines", "statsmodels"])
if os.path.isdir("repo"):
    sh(["git", "-C", "repo", "pull"])
else:
    sh(["git", "clone", REPO, "repo"])
os.chdir("repo")
py = sys.executable

sh([py, "-u", "-m", "src.openalex_depth", "--abstracts", "release/abstracts.jsonl",
    "--max-seeds", "60", "--out", f"{W}/depth_distribution.json"])
sh([py, "-m", "src.compose", "--scores", "release/results/scores.csv.gz",
    "--depths", f"{W}/depth_distribution.json",
    "--results", "release/results/results.json", "--out", f"{W}/composed.json"])
sh([py, "-m", "src.figures", "--scores", "release/results/scores.csv.gz",
    "--results", "release/results/results.json",
    "--depths", f"{W}/depth_distribution.json",
    "--composed", f"{W}/composed.json", "--outdir", f"{W}/figures"])
sh([py, "-m", "src.positive_control", "--abstracts", "release/abstracts.jsonl",
    "--out", f"{W}/positive_control.json"])

for fn in ("depth_distribution.json", "composed.json", "positive_control.json"):
    print(f"===== {fn} =====", flush=True)
    print(json.dumps(json.load(open(f"{W}/{fn}")), indent=1), flush=True)
print("[kernel] DONE", flush=True)
