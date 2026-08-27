# The Vagueness Ratchet: data and code

Pipeline for "The Vagueness Ratchet: Repeated AI Summarization Makes
Scientific Claims Less Precise, Not More Confident." Everything is automated: fetching
stratified abstracts, running summarization chains, scoring five epistemic
markers, hypothesis tests, OpenAlex depth composition, figures.

## Pipeline

| Step | Script | Where | Time |
|---|---|---|---|
| 1. Fetch 60 stratified PubMed OA abstracts | `src/fetch_abstracts.py` | laptop | ~10 min |
| 2. Chains: 60 abstracts x 3 models x 2 regimes x depth 10 | `src/chains.py` via `kaggle/` | Kaggle T4 | 4.1 to 7.0 h per model as measured |
| 3. Score 5 instruments on every generation | `src/score.py` | laptop | ~1-2 h (NLI on CPU) |
| 4. H1-H3 tests | `src/analysis.py` | laptop | ~1 min |
| 5. OpenAlex depth + composition | `src/openalex_depth.py`, `src/compose.py` | laptop | ~20 min |
| 6. Figures + Table 1 | `src/figures.py` | laptop | ~1 min |
| 7. Every in-text number + positive controls | `src/paper_numbers.py`, `src/positive_control.py` | laptop | ~1 min |
| 8. Tests | `tests/` | laptop | ~1 min |

`bash run_all.sh` runs every CPU step and tells you when to insert the
Kaggle step. `prereg/PREREGISTRATION.md` is the analysis lock; its git
commit date is the timestamp.

## Kaggle chains

```bash
bash kaggle/push_kernels.sh <kaggle-username>
```

Pushes three private script kernels (one model each: Qwen2.5-7B,
Llama-3.1-8B, Mistral-7B-v0.3), each T4 + internet. Add a Kaggle secret
`HF_TOKEN` for the gated Llama model; without it the kernel swaps in
Phi-3.5-mini automatically. In the released run the swap fired, because an
account-level secret is not visible to a notebook unless the notebook opts
in, so the third model is Phi-3.5-mini and the release needs no gated token
to reproduce. Download each kernel's output
`chains_*.jsonl` and `abstracts.jsonl` into `data/`, then continue with
step 3. Kernels resume if interrupted: attach the previous run's output as
an input dataset and re-run.

Before first push: point `REPO` inside each `kaggle/kernel_*.py` at your own
fork, since the kernels clone that URL to get the code and corpus.

## Instruments

1. **Hedge density** (`instruments/hedges.py`): matches per 100 words
   against the hedge sublist of Hyland (2005).
2. **Causal strength** (`instruments/causal.py`): five-point rule scale,
   negation-aware, max over sentences.
3. **Numeric fidelity** (`instruments/numeric.py`): effect sizes, CIs,
   p-values, percentages; exact / rounded / lost vs source.
4. **Qualifier retention** (`instruments/qualifiers.py`): population,
   dosage, and study-design qualifiers; fuzzy token overlap >= 0.6.
5. **Entailment** (`instruments/entailment.py`): bidirectional NLI
   (cross-encoder/nli-deberta-v3-base) plus core-finding survival.

All rule-based instruments are deterministic; released chains let anyone
rescore with instruments of their own choosing.

## Outputs

A fresh run writes into `results/` and `figures/out/`. The frozen copies the
paper cites live under `release/`, which is what to read if you want the
published numbers rather than your own rerun.

- `scores.csv` -- one row per (abstract, model, regime, generation); the
  released copy is `release/results/scores.csv.gz`
- `results.json` -- H1 per-generation drift estimates, H2 median survival
  times, H3 regime interactions, each with the estimator recorded per test
- `depth_distribution.json`, `composed.json` -- OpenAlex citation depths and
  composed retention, with `d_star`
- `paper_numbers.json` -- every in-text figure the paper quotes, recomputed
  by `src/paper_numbers.py`
- `figures/out/` -- fig1-fig3 PDFs and `table1.tex`

## Tests

```bash
python tests/test_instruments.py
python tests/test_regressions.py
python tests/test_release_consistency.py
```

They run as plain scripts. `test_instruments.py` gates numeric and qualifier
self-retention, meaning a text scored against itself must keep its own
statistics; that gate is what caught a confidence-interval hyphen being read
as a minus sign. `test_release_consistency.py` fails if the prose in
`release/FINDINGS.md` drifts away from the released JSON.

## Setup

```bash
pip install -r requirements.txt
```

Python 3.10+. `bitsandbytes` is needed only on the GPU side and is
installed by the kernel itself.
