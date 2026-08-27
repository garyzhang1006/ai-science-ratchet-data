"""Kaggle T4 kernel: fetch abstracts (once) + run chains for ONE model.

Push three kernels, one per model, by editing MODEL_IDX below (or use
kaggle/push_kernels.sh which generates the three variants). Each fits a
12h session at the default n=60 abstracts. Chains resume: re-running a
kernel with the same output dataset attached continues where it stopped.

Kernel settings required: GPU = NvidiaTeslaT4, Internet = ON.
Gated models (Llama) need a Kaggle secret HF_TOKEN; ungated fallback is
used automatically if the token is missing.
"""
import os
import shutil
import subprocess
import sys

MODEL_IDX = 0  # 0, 1, 2 -- edited per kernel by push_kernels.sh
MODELS = [
    "Qwen/Qwen2.5-7B-Instruct",
    "meta-llama/Llama-3.1-8B-Instruct",
    "mistralai/Mistral-7B-Instruct-v0.3",
]
FALLBACKS = {"meta-llama/Llama-3.1-8B-Instruct":
             "microsoft/Phi-3.5-mini-instruct"}
# Clone URL of the fork this kernel pulls its code and corpus from.
# push_kernels.sh substitutes it, or set RATCHET_REPO before running.
REPO = os.environ.get("RATCHET_REPO", "REPO_URL_PLACEHOLDER")
if REPO == "REPO_URL_PLACEHOLDER":
    raise SystemExit("Set RATCHET_REPO to your fork's clone URL, or let "
                     "kaggle/push_kernels.sh substitute it.")
PER_CLASS = 20

os.environ["HF_HUB_DISABLE_XET"] = "1"


def sh(args):
    """Run and re-emit output line by line: Kaggle silently drops long
    subprocess stdout, so the notebook process must print it itself."""
    print("$ " + " ".join(args), flush=True)
    p = subprocess.Popen(args, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True)
    for line in p.stdout:
        print(line, end="", flush=True)
    p.wait()
    if p.returncode != 0:
        raise RuntimeError(f"command failed ({p.returncode}): {args}")


def get_hf_token():
    try:
        from kaggle_secrets import UserSecretsClient
        for attempt in range(8):  # secrets service is flaky; retry
            try:
                tok = UserSecretsClient().get_secret("HF_TOKEN")
                if tok:
                    return tok
            except Exception:
                pass
        return None
    except ImportError:
        return None


sh(["pip", "install", "-q", "bitsandbytes", "accelerate",
    "transformers>=4.44", "requests"])
if os.path.isdir("repo"):
    sh(["git", "-C", "repo", "pull"])
else:
    sh(["git", "clone", REPO, "repo"])
os.chdir("repo")

model = MODELS[MODEL_IDX]
tok = get_hf_token()
if tok:
    os.environ["HF_TOKEN"] = tok
elif model in FALLBACKS:
    print(f"[kernel] no HF_TOKEN; swapping gated {model} -> "
          f"{FALLBACKS[model]}", flush=True)
    model = FALLBACKS[model]

slug = model.split("/")[-1].lower().replace(".", "").replace("-", "_")
out = f"/kaggle/working/chains_{slug}.jsonl"

# Corpus preference order: repo's committed corpus (same fixed abstracts
# for every kernel) > previous run attached as input > fresh fetch.
prev = "/kaggle/input"
found = None
for root, _, files in os.walk(prev):
    if "abstracts.jsonl" in files:
        found = os.path.join(root, "abstracts.jsonl")
        break
os.makedirs("data", exist_ok=True)
if os.path.exists("corpus/abstracts.jsonl"):
    shutil.copy("corpus/abstracts.jsonl", "data/abstracts.jsonl")
elif found:
    shutil.copy(found, "data/abstracts.jsonl")
else:
    sh([sys.executable, "-m", "src.fetch_abstracts",
        "--per-class", str(PER_CLASS), "--out", "data/abstracts.jsonl"])
shutil.copy("data/abstracts.jsonl", "/kaggle/working/abstracts.jsonl")

# Resume from previous partial chains if attached as input.
for root, _, files in os.walk(prev):
    fn = f"chains_{slug}.jsonl"
    if fn in files:
        shutil.copy(os.path.join(root, fn), out)
        break

sh([sys.executable, "-m", "src.chains", "--abstracts",
    "data/abstracts.jsonl", "--model", model, "--out", out, "--depth", "10"])
print("[kernel] DONE", flush=True)
