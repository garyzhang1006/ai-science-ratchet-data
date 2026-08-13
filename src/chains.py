"""Run summarization chains of depth D under two prompt regimes.

Each (abstract, model, regime) seeds one chain: generation g summarizes
generation g-1; generation 0 is the source abstract. Decoding is greedy
(temperature 0) by default to isolate systematic drift from sampling
variance; pass --temperature for the sensitivity arm.

Writes JSONL incrementally and resumes safely: rerunning skips completed
(pmid, model, regime) chains. Designed for a Kaggle T4 with 4-bit
quantization; also runs on any CUDA box.

Usage (one model per 12h Kaggle session):
  python -m src.chains --abstracts data/abstracts.jsonl \
      --model Qwen/Qwen2.5-7B-Instruct --out data/chains_qwen.jsonl
"""
import argparse
import json
import os
import pathlib
import time

# Fix for HF Xet backend hangs on Kaggle.
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

import torch  # noqa: E402
from transformers import (AutoModelForCausalLM, AutoTokenizer,  # noqa: E402
                          BitsAndBytesConfig)

# Prompt prefixes; the abstract text is appended after a blank line.
PROMPTS = {
    "neutral": (
        "Summarize the following scientific text faithfully, at "
        "approximately its original length.\n\n"
    ),
    "conservative": (
        "Summarize the following scientific text faithfully, at "
        "approximately its original length. Preserve every hedge, "
        "qualifier, number, and statement of uncertainty exactly as "
        "expressed; do not state any claim more strongly than the "
        "original does.\n\n"
    ),
}


def load_model(name: str, four_bit: bool = True):
    tok = AutoTokenizer.from_pretrained(name)
    kwargs = {"torch_dtype": torch.float16}
    if four_bit and torch.cuda.is_available():
        kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
        )
        kwargs["device_map"] = {"": 0}  # single-GPU; avoids meta-device bugs
    elif torch.cuda.is_available():
        kwargs["device_map"] = {"": 0}
    model = AutoModelForCausalLM.from_pretrained(name, **kwargs)
    model.train(False)
    return tok, model


def summarize(tok, model, text: str, regime: str, temperature: float) -> str:
    prompt = PROMPTS[regime] + text
    msgs = [{"role": "user", "content": prompt}]
    rendered = tok.apply_chat_template(
        msgs, tokenize=False, add_generation_prompt=True)
    enc = tok(rendered, return_tensors="pt").to(model.device)
    src_len = enc.input_ids.shape[1]
    max_new = min(1024, max(200, int(1.5 * len(tok(text).input_ids))))
    gen_kwargs = {"max_new_tokens": max_new,
                  "pad_token_id": tok.pad_token_id or tok.eos_token_id}
    if temperature > 0:
        gen_kwargs.update(do_sample=True, temperature=temperature, top_p=0.95)
    else:
        gen_kwargs.update(do_sample=False)
    with torch.no_grad():
        out = model.generate(**enc, **gen_kwargs)
    return tok.decode(out[0][src_len:], skip_special_tokens=True).strip()


def completed_chains(out_path: str, depth: int):
    done = set()
    p = pathlib.Path(out_path)
    if not p.exists():
        return done
    counts = {}
    for line in p.open():
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        key = (r["pmid"], r["model"], r["regime"])
        counts[key] = max(counts.get(key, 0), r["generation"])
    for k, g in counts.items():
        if g >= depth:
            done.add(k)
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--abstracts", default="data/abstracts.jsonl")
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--depth", type=int, default=10)
    ap.add_argument("--regimes", nargs="+",
                    default=["neutral", "conservative"])
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--no-4bit", action="store_true")
    args = ap.parse_args()

    abstracts = [json.loads(l) for l in open(args.abstracts)]
    pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    done = completed_chains(args.out, args.depth)
    print(f"[chains] {len(done)} chains already complete; "
          f"{len(abstracts) * len(args.regimes) - len(done)} to run",
          flush=True)

    tok, model = load_model(args.model, four_bit=not args.no_4bit)
    f = open(args.out, "a")
    t0 = time.time()
    for rec in abstracts:
        for regime in args.regimes:
            key = (rec["pmid"], args.model, regime)
            if key in done:
                continue
            text = rec["abstract"]
            for g in range(1, args.depth + 1):
                text = summarize(tok, model, text, regime, args.temperature)
                if not text:
                    print(f"[chains] EMPTY generation {key} g={g}", flush=True)
                    break
                f.write(json.dumps({
                    "pmid": rec["pmid"], "cls": rec["cls"],
                    "model": args.model, "regime": regime,
                    "generation": g, "text": text,
                }) + "\n")
                f.flush()
            print(f"[chains] done {key} ({time.time() - t0:.0f}s elapsed)",
                  flush=True)
    f.close()
    print("[chains] all chains complete", flush=True)


if __name__ == "__main__":
    main()
