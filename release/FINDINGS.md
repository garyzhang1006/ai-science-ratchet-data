# Findings as of 2026-08-15

Run complete for H1 and H3; H2 (entailment) not yet computed.

## Corpus and chains

60 PubMed open-access abstracts, stratified 20/20/20 into randomized trials,
observational studies, and explicit null results. Three models
(Qwen2.5-7B-Instruct, Phi-3.5-mini-instruct, Mistral-7B-Instruct-v0.3) times
two prompt regimes times depth 10 gives 360 chains and 3600 generations, all
complete with no truncated chains. Greedy decoding throughout.

## H1: the direction is not toward certainty

The preregistered hypothesis predicted falling hedge density and rising
causal strength. Hedge density rises instead, and causal strength does not
move. What does fall, steeply, is the precision of the claim.

| Marker | Neutral per-step | Conservative per-step | Verdict |
|---|---|---|---|
| Hedge density (/100 words) | +0.0611 (0.0111) | +0.0332 (0.0057) | reversed |
| Causal strength (1-5) | +0.0067 (0.0172) | +0.0128 (0.0115) | null |
| Numeric fidelity (exact share) | -0.0459 (0.0034) | -0.0093 (0.0017) | supported |
| Qualifier retention | -0.0486 (0.0036) | -0.0112 (0.0022) | supported |

Cluster-robust standard errors in parentheses, clustered on source abstract;
Holm-corrected across markers within regime. Every drift except causal
strength is significant at p < 1e-7.

The reversal is not a single-model artifact. Hedge density rises in all three
models independently: Qwen +0.0499 (p = 0.0012), Phi +0.0969 (p = 9.3e-06),
Mistral +0.0366 (p = 0.00059). Causal strength is null in all three. Numeric
fidelity and qualifier retention fall in all three. No marker flips sign
between models.

Neutral-regime trajectories, pooled, from generation 0 to 10: hedge density
0.72 to 1.69, numeric fidelity 0.88 to 0.28, qualifier retention 0.98 to 0.33.
The single largest loss happens at the first hop, where numeric fidelity falls
from 0.88 to 0.43. Half of a paper's reported numbers do not survive one
summarization.

## H3: conservative prompting damps every rate and flips no sign

Reduction in drift magnitude under the conservative regime: 79.7% for numeric
fidelity, 76.9% for qualifier retention, 45.7% for hedge density. Interaction
p < 1e-3 for all three. No sign flips anywhere, which is what H3 predicted.

## Composition against real intermediation depth

An OpenAlex forward-citation walk over 30 seed works yielded 2327
consumption-weighted samples, giving a median intermediation depth of 2 hops
and a p90 of 4. Composing the measured neutral-regime rates along that
distribution, a claim at the median consumption depth retains 85.8% of its
original qualifiers, and qualifier retention stays above the 0.5 calibration
floor out to 10 hops. Hedging accumulates rather than decays, so its
per-step ratio exceeds 1.

## What this means for the paper's framing

The certainty-ratchet hypothesis does not survive contact with the data. The
process these chains describe is a loss of precision, not a gain of
confidence: claims shed their numbers and their scope conditions while
picking up hedges, so a summarized finding drifts toward being unfalsifiable
rather than toward being overstated. That is a publishable result and it is
cleanly measured, but it needs the title, abstract, and H1 rewritten around
vagueness rather than certainty.

## Outstanding

H2 (core-finding erosion by claim class) requires the NLI pass, which has not
been run. Every entailment column in the released scores is empty, figure 2
is absent, and the bidirectional-entailment row of table 1 is blank.

## Deviations

Both logged in `prereg/PREREGISTRATION.md`: all H1 estimates come from the
pre-specified cluster-robust OLS fallback because differencing leaves the
random intercept degenerate, and the third model is Phi-3.5-mini rather than
Llama-3.1-8B because the gated-model token was unavailable at run time.

## Files

- `abstracts.jsonl` — the 60-abstract corpus with stratum labels
- `chains/*.jsonl.gz` — all 3600 generations, one per model
- `results/scores_nonli.csv.gz` — every marker on every generation
- `results/results_nonli.json` — H1 and H3 estimates with per-test estimator
- `results/depth_distribution.json` — OpenAlex depth weights
- `results/composed.json` — retention composed along depth
- `figures/` — figure 1, figure 3, table 1
