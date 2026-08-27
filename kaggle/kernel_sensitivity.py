"""Kaggle kernel: temperature sensitivity arm.

The main experiment fixes decoding at temperature 0 to separate systematic
drift from sampling variance. This arm relaxes that, rerunning a stratified
20-abstract subset through all three models under the neutral regime at
temperature 0.7 with a fixed seed, so the reported signs can be checked
against a sampled decoder rather than a greedy one.

20 abstracts x 3 models x 1 regime x depth 10 = 600 generations, which fits
one T4 session with room to spare.
"""
import os
import shutil
import subprocess
import sys

# Clone URL of the fork this kernel pulls its code and corpus from.
# push_kernels.sh substitutes it, or set RATCHET_REPO before running.
REPO = os.environ.get("RATCHET_REPO", "REPO_URL_PLACEHOLDER")
if REPO == "REPO_URL_PLACEHOLDER":
    raise SystemExit("Set RATCHET_REPO to your fork's clone URL, or let "
                     "kaggle/push_kernels.sh substitute it.")
MODELS = [
    "Qwen/Qwen2.5-7B-Instruct",
    "microsoft/Phi-3.5-mini-instruct",
    "mistralai/Mistral-7B-Instruct-v0.3",
]
TEMPERATURE = 0.7
SEED = 20260815

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


sh(["pip", "install", "-q", "bitsandbytes", "accelerate",
    "transformers>=4.44"])

if os.path.isdir("repo"):
    sh(["git", "-C", "repo", "pull"])
else:
    sh(["git", "clone", REPO, "repo"])
os.chdir("repo")

W = "/kaggle/working"

# Resume any partial arm from a previous session attached as input.
for root, _, files in os.walk("/kaggle/input"):
    for fn in files:
        if fn.startswith("sens_") and fn.endswith(".jsonl"):
            shutil.copy(os.path.join(root, fn), os.path.join(W, fn))
            print(f"[kernel] resuming from {fn}", flush=True)

for model in MODELS:
    slug = model.split("/")[-1].lower().replace(".", "").replace("-", "_")
    out = f"{W}/sens_{slug}.jsonl"
    sh([sys.executable, "-u", "-m", "src.chains",
        "--abstracts", "corpus/abstracts_sensitivity.jsonl",
        "--model", model, "--out", out, "--depth", "10",
        "--regimes", "neutral",
        "--temperature", str(TEMPERATURE), "--seed", str(SEED)])

print("[kernel] DONE", flush=True)
