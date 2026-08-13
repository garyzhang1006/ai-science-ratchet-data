# The Certainty Ratchet: data and code

Pipeline for "The Certainty Ratchet: Directional Epistemic Drift in AI
Summarization of Scientific Claims." Everything is automated: fetching
stratified abstracts, running summarization chains, scoring five epistemic
markers, hypothesis tests, OpenAlex depth composition, figures.

## Pipeline

| Step | Script | Where | Time |
|---|---|---|---|
| 1. Fetch 60 stratified PubMed OA abstracts | `src/fetch_abstracts.py` | laptop | ~10 min |
| 2. Chains: 60 abstracts x 3 models x 2 regimes x depth 10 | `src/chains.py` via `kaggle/` | Kaggle T4 | ~8-11 h per model |
| 3. Score 5 instruments on every generation | `src/score.py` | laptop | ~1-2 h (NLI on CPU) |
| 4. H1-H3 tests | `src/analysis.py` | laptop | ~1 min |
| 5. OpenAlex depth + composition | `src/openalex_depth.py`, `src/compose.py` | laptop | ~20 min |
| 6. Figures + Table 1 | `src/figures.py` | laptop | ~1 min |

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
Phi-3.5-mini automatically. Download each kernel's output
`chains_*.jsonl` and `abstracts.jsonl` into `data/`, then continue with
step 3. Kernels resume if interrupted: attach the previous run's output as
an input dataset and re-run.

Before first push: set your GitHub username in `REPO` inside
`kaggle/kernel_ratchet.py` (placeholder `GARYZHANG_GH_USER`).

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

- `results/scores.csv` -- one row per (abstract, model, regime, generation)
- `results/results.json` -- H1 drift estimates, H2 half-lives, H3 regime
  effects, mapped 1:1 to the paper's TK slots
- `results/depth_distribution.json`, `results/composed.json` -- OpenAlex
  intermediation depths and composed retention, with `d_star`
- `figures/out/` -- fig1-fig3 PDFs and `table1.tex`

## Setup

```bash
pip install -r requirements.txt
```

Python 3.10+. `bitsandbytes` is needed only on the GPU side and is
installed by the kernel itself.
