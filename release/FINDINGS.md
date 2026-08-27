# Findings, current as of the 2026-08-22 composition recompute

All three hypotheses computed. 60 stratified PubMed open-access abstracts,
three models (Qwen2.5-7B-Instruct, Phi-3.5-mini-instruct,
Mistral-7B-Instruct-v0.3), two prompt regimes, depth 10: 360 chains and 3600
generations, greedy decoding throughout, with a generation budget of 1.5
times the input length capped at 1024 tokens.

## H1: the drift is away from precision, not toward certainty

The preregistered hypothesis predicted falling hedge density and rising
causal strength. Hedge density rises instead, causal strength does not move,
and what collapses is the precision of the claim.

| Marker | Neutral per generation | Conservative per generation | Verdict |
|---|---|---|---|
| Hedge density (/100 words) | +0.0611 (0.0111) | +0.0332 (0.0057) | reversed |
| Causal strength (1-5) | +0.0067 (0.0172) | +0.0128 (0.0115) | null |
| Numeric fidelity (exact share) | -0.0549 (0.0039) | -0.0104 (0.0018) | supported |
| Qualifier retention | -0.0486 (0.0036) | -0.0112 (0.0022) | supported |
| Bidirectional entailment | -0.0677 (0.0016) | -0.0278 (0.0013) | supported |

Cluster-robust standard errors clustered on source abstract, Holm-corrected
across markers within regime. Everything except causal strength is
significant at p < 1e-7.

The reversal replicates in every model separately, with no sign flips
anywhere: Qwen +0.0499 (p = 4.0e-04), Phi +0.0969 (p = 3.1e-06), Mistral
+0.0366 (p = 2.0e-04), cluster-robust with the same normal reference used
for the pooled estimates.

Pooled neutral trajectories from generation 0 to 10: hedge density 0.72 to
1.33, numeric fidelity 1.00 to 0.45, qualifier retention 0.98 to 0.49. The
loss is front-loaded rather than compounding: numeric fidelity falls 1.00 to
0.56 across the first hop alone, which is 44% of the original content and
80% of all numeric loss incurred over ten generations. Qualifier retention
behaves the same way, with the first hop accounting for 52% of total loss.

## H2: the preregistered test is null, the continuous one supports it

The preregistered test, first generation whose core-finding entailment drops
below 0.5, compared by log-rank across claim classes, is null in both
regimes (neutral p = 0.40, conservative p = 0.21). It saturates: in the
neutral regime the median survival time is one generation for every class, which
leaves the binary test almost no room to discriminate.

The continuous version of the same question does discriminate. Regressing
core-finding entailment on generation interacted with an indicator for null
results, over all eleven generations of the neutral regime with errors
clustered on abstract, the baseline decay is -0.032 per generation
(p = 9e-15) and null-result abstracts decay an additional -0.0165 per
generation (p = 0.009), so null findings lose their core claim about 1.5
times as fast as positive ones, which is the direction H2 predicted. The gap
survives dropping the first hop: on generations 1 to 10 alone the baseline
decay is -0.0078 (p = 0.048) and the null excess -0.0145 (p = 0.041). Both
specifications are emitted by `src/paper_numbers.py`.

Treat this as secondary. It is an uncorrected test that was not
preregistered, and the preregistered test it supplements came out null.
Class trajectories, neutral regime, generation 0 to 10: null 0.97 to 0.21,
observational 0.95 to 0.37, randomized 0.94 to 0.32.

## H3: conservative prompting damps four of five rates and flips no sign

Reduction in drift magnitude under conservative prompting: 81.1% for numeric
fidelity, 76.9% for qualifier retention, 58.9% for bidirectional
entailment, and 45.7% for hedge density. Causal strength is the
exception: it is null in both regimes and drifts slightly further under the
conservative prompt (reduction share -91.7%, interaction p = 0.66).
The other four interactions are significant, at p = 0.012 for hedge
density and below 1e-26 for the remaining three. No marker flips sign.

The effect on core-finding survival is larger than on any single marker. At
generation 10 the core finding retains 0.726 support under conservative
prompting against 0.301 under neutral, and 10 to 21 chains per class cross
the erosion threshold rather than 44 to 49.

## Temperature sensitivity: the drift is not a greedy-decoding artifact

The main experiment fixes decoding at temperature 0. Rerunning a stratified
20-abstract subset through all three models under the neutral regime at
temperature 0.7, with a fixed seed, reproduces every sign and nearly every
magnitude.

| Marker | Temperature 0.7 | Temperature 0, same 20 abstracts |
|---|---|---|
| Hedge density | +0.0515 (p = 0.091) | +0.0527 (p = 0.0092) |
| Causal strength | +0.0250 (p = 0.86) | +0.0283 (p = 0.36) |
| Numeric fidelity | -0.0610 (p = 2.0e-11) | -0.0483 (p = 5.0e-15) |
| Qualifier retention | -0.0546 (p = 1.9e-17) | -0.0443 (p = 2.8e-15) |

No sign flips. The information-loss rates are slightly steeper under
sampling than under greedy decoding. Hedge density keeps essentially the
same effect size and loses significance only because the subset holds 20
abstracts rather than 60, which is a power difference and not a change in
the estimate.

## Composition against real citation depth

An OpenAlex forward-citation walk over 60 seed works produced 4920
citation-weighted samples, giving a median citation depth of 2 hops
and a p90 of 3. Composing measured neutral rates along that distribution, a
claim at the median depth of two hops retains 62.3% of its qualifiers, the
expectation over the whole depth distribution is 66.5%, and qualifier
retention stays above the 0.5 floor out to 10 hops. Hedge density rises
rather than decays, so its per-generation ratio exceeds 1.

## What this means for the paper's framing

The certainty-ratchet hypothesis does not survive the data. These chains
describe a loss of precision rather than a gain of confidence: claims shed
their numbers and qualifiers while accumulating hedges, so a
summarized finding drifts toward being unfalsifiable rather than toward
being overstated. The title, abstract, and H1 need rewriting around
vagueness.

## Instrument validation, and one failure that was caught

A second instrument fault was caught the same way, after the entailment one.
The generation-side number extractor read the hyphen in a confidence interval
("0.544-0.866", the standard PubMed format) as a minus sign, so a preserved
upper bound scored as lost. A second fault had the same shape: a p-value
written without its leading zero, as "P = .63", was extracted from the source
and could not be matched back. The corpus scored 0.88 against itself instead
of the 1.0 a self-comparison must give. With both corrected it scores exactly
1.0, and tests/test_instruments.py now gates on that. Every numeric
figure in the paper and in this note comes from the corrected extractor.


The entailment instrument initially used whole-document NLI and produced a
clean-looking H2 null with a median survival time of exactly 1.0 in every class.
That null was an artifact. A validation check, whether a source abstract
entails a sentence copied out of itself, returned 0.056, so the instrument
was reporting almost nothing as supported. The cause was not truncation
(median premise 287 tokens against a 512 limit) but the model itself:
`cross-encoder/nli-deberta-v3-base` is trained on single-sentence premises
and mislabels document-length ones.

Replacing whole-document scoring with SummaC-style sentence-level aggregation,
each hypothesis sentence against every premise sentence keeping the
best-supporting one, raised self-entailment to 0.944 on the 20-source
validation subset the gate reads, and to 0.955 across all 60 sources.
Three sources still score below the gate on their own core sentence. The scoring kernel now
aborts if that figure falls below 0.80, so this failure cannot pass silently
again. All numbers above come from the corrected instrument.

Backward entailment falls for any summary because summaries drop content, so
it measures compression as much as infidelity. Forward entailment is the
cleaner drift signal, falling 0.97 to 0.49 under neutral prompting against
0.97 to 0.78 under conservative.

## Deviations

Both logged in `prereg/PREREGISTRATION.md`. All H1 estimates come from the
pre-specified cluster-robust OLS fallback, because differencing removes the
abstract-level intercept and leaves the random-intercept variance
degenerate. The third model is Phi-3.5-mini rather than Llama-3.1-8B,
because the gated-model token was unavailable at run time.

## Files

- `abstracts.jsonl` — the 60-abstract corpus with class labels
- `abstracts_sensitivity.jsonl` — the 20-abstract sensitivity subset
- `chains/chains_*.jsonl.gz` — all 3600 main generations, one file per model
- `chains/sens_*.jsonl.gz` — the 600 temperature-0.7 generations
- `results/scores.csv.gz` — every marker on every generation
- `results/results.json` — H1, H2, and H3 with the estimator used per test
- `results/paper_numbers.json` — every figure quoted in the paper's running
  text (trajectory endpoints, front-loading shares, per-model drift, word
  counts, the hedge-count and length-control checks, the continuous H2
  regression, the temperature-arm comparison, and the case-study chain),
  recomputed by `python -m src.paper_numbers --release release`
- `results/scores_sensitivity.csv.gz`, `results/results_sensitivity.json` —
  the temperature arm
- `results/depth_distribution.json` — OpenAlex depth weights
- `results/composed.json` — retention composed along depth
- `figures/` — figures 1 to 3 and table 1
