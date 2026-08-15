# Preregistration: The Certainty Ratchet

Hypotheses, instruments, model specifications, and exclusion rules below
were fixed before any chain was generated. The git commit timestamp of this
file is the time lock.

## Hypotheses

- **H1** Per-step drift in hedging and causal strength has nonzero mean in
  the direction of increased certainty: hedge density falls, causal
  strength rises, numeric fidelity falls, qualifier retention falls,
  bidirectional entailment falls, per generation.
- **H2** Null-result abstracts lose their core finding (entailment of the
  source's strongest claim sentence, threshold 0.5) faster than
  positive-result abstracts.
- **H3** Conservative prompting reduces the magnitude of per-step drift
  without changing its sign.

## Design constants

- Depth: 10 generations per chain.
- Regimes: neutral, conservative (exact prompt strings in `src/chains.py`).
- Decoding: greedy (temperature 0) primary; temperature 0.7 sensitivity arm.
- Strata: rct / obs / null, equal n, mutually exclusive with null-priority
  (a null-tail abstract is always classed null regardless of which query
  surfaced it); operational rules in `src/fetch_abstracts.py`
  (`qualifies()`).
- Abstract length gate: 150-450 words.

## Analysis

- H1 estimand: mean adjacent-generation difference per marker, mixed model
  with random intercept per source abstract; cluster-robust OLS fallback
  when the mixed model fails to converge or the random-intercept variance
  is degenerate (< 1e-10). Two-sided tests; Holm correction across the five
  markers within each regime.
- H2: Kaplan-Meier, event = first generation with core entailment < 0.5,
  censored at the chain's own last observed generation (depth 10 for
  complete chains); chains with no NLI measurement are excluded and
  counted; log-rank null vs non-null classes, per regime.
- H3: OLS of per-step differences on regime indicator, cluster-robust SEs
  (clustered on abstract); report reduction share and sign-flip check.

## Exclusion rules

- Empty generations terminate a chain; completed prefix is retained.
- Markers undefined for a source (no numbers, no qualifiers) are NaN and
  excluded from that marker's analysis only.
- No other exclusions.

## Deviations

None to the specification. One pre-specified fallback fired universally and
is recorded here for transparency.

**2026-08-15, estimator fallback.** In every marker-by-regime cell, the
random-intercept variance of the mixed model was degenerate (singular
covariance, boundary MLE), so all H1 estimates come from the pre-specified
cluster-robust OLS fallback rather than `mixedlm`. This is expected rather
than anomalous: the estimand is an adjacent-generation difference, and
differencing removes the abstract-level intercept by construction, leaving
no level variance for a random intercept to absorb. Clustering on the
source abstract still carries the dependence between the nine differences
within a chain. The `method` field of every entry in `results.json` records
which estimator produced it.

**2026-08-15, model substitution.** The third model was specified as
Llama-3.1-8B-Instruct. The run executed Phi-3.5-mini-instruct because the
gated-model token was unavailable in the compute environment, and the
harness swaps gated models for an ungated fallback automatically. The
released model set is therefore Qwen2.5-7B-Instruct, Phi-3.5-mini-instruct,
and Mistral-7B-Instruct-v0.3, all ungated, which the replication package
benefits from.
