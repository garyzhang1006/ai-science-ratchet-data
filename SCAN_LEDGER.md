# Scan ledger: AISciK vagueness-ratchet paper

Rules: every parent scan has 20 sub-scans with distinct purposes; sub-scan 1
of parent N+1 reviews the diff produced by parent N. Score is an honest
workshop-acceptance estimate on a 10-point scale, never inflated. Numbers in
the paper are invariant unless a scan finds a real error, and every change is
followed by compile + numbers-invariant + anonymity + page-count checks.
Scripted sub-scans live in scan.py; judgment sub-scans are read-throughs.

Baseline before scan 1: 6.5-7 / 10 (likely accept, not assured). Ceiling set by
60 PubMed abstracts, three small open-weight models, 30 OpenAlex seed works.

## Parent scan plan (themes)
 1 mechanical invariants      2 statistical reporting      3 claims vs evidence
 4 internal consistency       5 hostile methods review     6 framing/novelty/related work
 7 figures and tables         8 citations/bibliography     9 LaTeX/typesetting
10 anonymity/CFP compliance  11 reproducibility claims    12 preregistration fidelity
13 structure and flow        14 abstract                  15 introduction
16 results sections          17 discussion/limits/concl   18 AI-tell language audit
19 grammar and usage         20 style-corpus imitation    21 cross-disciplinary reader
22 title/TLDR/submission     23 final integrity (after humanizer skills)

## Scan 1: mechanical invariants (20 sub-scans)
1 numbers traceable to release data | 2 abstract numbers appear in body |
3 \ref resolve | 4 labels referenced | 5 \cite resolve | 6 bibitems cited |
7 bib years | 8 bib venues | 9 LaTeX errors | 10 overfull boxes > 5pt |
11 page count = 8 | 12 anonymity guard | 13 figure files exist |
14 captions present | 15 heading case | 16 dashes | 17 doubled words |
18 straight quotes | 19 i.e./e.g. commas | 20 lowercase sentence starts
Findings: fig:depth never referenced (real); sec:results label unused;
"932" was the bartlett1932 cite key (scanner regex fixed); "actually" and
"in order to" filler; anonymity guard fails only on the user's placeholder.
Changes: referenced Figure 3 in 4.6; removed unused label; two filler words.
Score after: 6.5-7 (unchanged; mechanical).

## Scan 2: statistical reporting (20 sub-scans)
1 review scan-1 diff (Figure 3 sentence reads fine) | 2 every estimate has SE or p |
3 p-format consistency (abstract 7e-8 vs text 6.9e-8: unified) | 4 Holm vs raw labeled |
5 two-sided stated (added) | 6 effect sizes carry units | 7 cluster count stated (added 60) |
8 H2-continuous labeled uncorrected | 9 censoring stated (added) | 10 sensitivity p labeled Holm (added) |
11 85% rise arithmetic | 12 "nearly twice" (1.85x) | 13 "1.5 times" (1.51) | 14 41/79/52% shares |
15 SEs in table | 16 CI on headline (added, from paper_numbers.py) | 17 mixed-model fallback explained |
18 power (not claimed; fine) | 19 n per cell stated (added 180/regime) | 20 rounding consistency
Also: H3 interaction p's survive Holm (hedge 0.012 -> 0.024), now stated.
Score after: 6.7 (reporting is now reviewer-proof; substance unchanged).

## Scan 3: claims vs evidence (20 sub-scans)
1 review scan-2 diff | 2 abstract claim "reversal in all three models" | 3 "p<1e-39" |
4 "unfalsifiable rather than overstated" (inference, supported) | 5 41/79% | 6 depth-vs-first-hop claim |
7 "costs nothing in length" -> OVERCLAIM: conservative summaries are 58% longer than neutral; reworded to "stays within the source length" (abstract, 4.3 heading, 4.3 body, Discussion) |
8 intro "nothing left to check" -> overclaim (42% of numbers remain); fixed |
9 "whatever survives one hop survives nine more" (0.52->0.42, ok) | 10 "four hops to two recovers little" -> quantified (0.45 vs 0.49, ~3%) |
11 "handily" (one evaluative, ok) | 12 "any deployment can adopt today" -> overgeneral; fixed |
13 H2 continuous direction | 14 sensitivity "every sign" | 15 composition claims -> MODEL MISSPECIFIED (geometric rho^d vs measured front-loaded curve): 87%/86% should be ~62%/64%; needs recompute (ask user) |
16 self-entailment 0.944 | 17 "leaves causal language untouched" | 18 "79% at first hop" | 19 "suggests capacity" flagged as inference | 20 novelty claim -> added "to our knowledge"
Score after: 6.7 (composition defect found; not yet fixed).

## Scan 4: internal consistency (20 sub-scans)
1 review scan-3 diff | 2 generation/hop/step usage -> defined interchangeably in 3.2 | 3 model name forms (natural drift, kept) |
4 "core finding" never defined -> added to Instruments | 5 word counts 210/123/195/116 consistent | 6 4,200 = 3,600 + 600 |
7 depth ten = 10 hops | 8 title matches findings | 9 abstract design sentence | 10 table caption vs text |
11 fig1 caption "95% intervals on the cell mean" matches figures.py (1.96 x sem) | 12 fig2 caption | 13 fig3 caption (pending recompute) |
14 first-run narrative vs corrected run | 15 0.944 vs 0.80 gate | 16 release list vs repo | 17 H1/H2/H3 statements vs prereg |
18 threshold 0.5 everywhere | 19 "three model families" | 20 footnote vs "five hours per model"
Score after: 6.7.
Scan 3 item 15 RESOLVED via Kaggle kernel ratchet-recompute (60 seeds, measured curve): 87%/86% -> 62%/66%; two-thirds of null chains dead by median depth; p90 depth 4 -> 3.
Scan 5 item 9 RESOLVED: positive controls (causal 3.07->4.23 strengthen, ->2.62 weaken, 0 wrong-way; hedges to 0 when stripped) now in Instruments.

## Scan 6: framing, novelty, related work (20 sub-scans)
1 review scan-5 diff | 2 novelty claim vs Peters & Chin-Yee 2025 (RSOS, verified PubMed) -> NARROWED in abstract and intro to repeated summarization + where loss falls |
3 iterative-generation lineage -> added Shumailov 2024 (Nature, verified) | 4 serial reproduction -> added Kirby 2008 (PNAS, verified) |
5 spin literature -> added Yavchitz 2012 (PLoS Med, verified); Boutron 2010 found but not added (space) | 6 hedge-detection tradition -> Farkas 2010 CoNLL (verified) |
7 NLI-as-faithfulness justification -> Maynez 2020 ACL (verified) | 8 Sumner framing kept | 9 Liang/Kobak prevalence kept |
10 every new bib entry verified online before insertion (CFP desk-reject rule) | 11 Vinkers 2015 not found in PubMed by my query; not cited |
12 Bratton 2019 replication verified; not cited (space) | 13 Jurgens/Teufel citation-function work: out of scope, not cited |
14 model collapse vs our setting distinguished (training-side vs inference-side) | 15 "certainty ratchet" framing explained as preregistered expectation |
16 contributions list matches results | 17 intro research question is a real question, not rhetorical | 18 title still accurate |
19 related work now 10 citations across NLP, psycholinguistics, science communication, and Nature | 20 trims made to keep main text on 8 pages (4 sentences condensed)
Style corpus: 21 pre-2023 papers measured (ACL/EMNLP/NAACL/TACL/CoNLL) + Sumner BMJ full text + 6 PubMed abstracts; targets in scratchpad corpus_targets.json.
Score after: 7.1 (composition defect fixed and strengthened; novelty honest; related work no longer thin).

## Scan 7: figures and tables (20 sub-scans, figures rendered to PNG and inspected)
1 review scan-6 diff | 2 fig1 legibility -> FAIL: five 1-inch panels, legend over data -> 2x3 grid, shared legend (figures.py, Kaggle v2) |
3 fig1 "p=0" underflow annotation -> "p<1e-100" | 4 fig1 y-label units "/100w" -> "per 100 words" | 5 fig2 legible, CIs shown |
6 fig3 left half-integer ticks -> integer ticks | 7 fig3 right now shows measured curve with 1.0 reference line | 8 all figures referenced in text |
9 captions self-contained | 10 caption/legend solid-dashed convention stated | 11 table1 SE/stars consistent with text | 12 table verdict column explained in caption |
13 figure files present | 14 colors distinguishable in grayscale? (line styles differ by regime; acceptable) | 15 fontsize at column width (fixed by grid) |
16 error bars defined (1.96 x SEM) | 17 fig2 CI bands from lifelines | 18 fig3 floor line labeled | 19 no figure on page 1 | 20 table placement [t]
Score after: 7.1.

## Scan 8: citations and bibliography (20 sub-scans)
1 review scan-7 diff | 2 cites resolve | 3 bibitems cited | 4 year/venue present | 5 label years match entries |
6 every entry verified online: Liang NHB version unverifiable -> switched to verified arXiv 2404.01268 (title corrected) | 7 OpenAlex cite added (Priem 2022, verified) |
8 accents in names | 9 et al. usage (mixed, left as natural drift) | 10 venue naming | 11 arXiv-only entries acceptable | 12 natbib labels |
13 \citet vs \citep usage | 14 no self-citation (double-blind) | 15 DeBERTa/NLI model cite (omitted, space) | 16 Holm/KM/log-rank standard methods uncited (fine) |
17 Sumner BMJ volume/page verified | 18 Peters RSOS volume/issue verified | 19 Shumailov Nature pages verified | 20 no "(?)" in PDF
Score after: 7.1.

## Scan 9: LaTeX and typesetting (20 sub-scans)
1 review scan-8 diff | 2 zero errors | 3 zero overfull > 5pt | 4 zero underfull | 5 main text ends page 8, refs spill (CFP allows) |
6 all Figure/Section/Table refs tied with ~ (8/8) | 7 no double spaces | 8 quotes `` '' | 9 math-mode numbers consistent | 10 \% escaped |
11 no dashes | 12 line numbers on (dblblind mode) | 13 running header shows workshop | 14 footnotes typeset on their pages | 15 table booktabs |
16 figure widths \linewidth | 17 hyperref links colored? (default boxes; acceptable) | 18 no widows checked visually on pages 4-7 renders | 19 title linebreak ok | 20 bibliography natbib labels render
Score after: 7.1.

## Scan 10: anonymity and CFP compliance (20 sub-scans)
1 review scan-9 diff | 2 guard: only the user's placeholder remains | 3 no acknowledgments/funding | 4 no self-citation | 5 PDF metadata clean |
6 dblblindworkshop option | 7 single PDF | 8 NeurIPS 2026 style | 9 4-or-8 pages: main 8 | 10 references unlimited |
11 citations all verified (desk-reject rule) | 12 AI-use disclosure field on OpenReview -> USER must answer honestly | 13 AI authorship attestation -> user |
14 reciprocal reviewing commitment field -> user | 15 track: Research (recommend) | 16 in-person attendance -> user | 17 no external links in PDF besides placeholder |
18 figures carry no names | 19 supplement scrubbed (0 leaks) | 20 repo visibility during review -> user's decision
Score after: 7.1.

## Scan 11: reproducibility claims (20 sub-scans)
1 review scan-10 diff | 2 corpus in release | 3 chains in release | 4 score table | 5 results.json with estimator field |
6 paper_numbers.py covers every running-text number (re-verified) | 7 depth distribution (60 seeds) | 8 composed.json | 9 positive_control.json |
10 figures + table1 | 11 preregistration present with deviations | 12 test commands exist and pass | 13 "laptop CPU in minutes" -> FALSE for NLI scoring; corrected |
14 "roughly five hours per model" (hedged; kept) | 15 kernel scripts in repo | 16 requirements.txt | 17 README present | 18 seeds fixed (20260815, 20260813) stated in code |
19 model names exact HF ids in code | 20 supplement builder refuses on leaks
Score after: 7.1.

## Scan 12: preregistration fidelity (20 sub-scans)
1 review scan-11 diff | 2 H1 wording matches prereg | 3 H2 matches | 4 H3 matches | 5 depth 10 | 6 regimes | 7 greedy + 0.7 arm |
8 strata with null-priority | 9 150-450 gate | 10 mixed model + fallback rule | 11 two-sided | 12 Holm within regime | 13 KM event/censoring |
14 log-rank null vs rest | 15 H3 OLS cluster-robust | 16 exclusion rules match (NaN markers) | 17 deviations: two, now headed correctly in prereg file |
18 non-preregistered analyses labeled: continuous H2, length control, epistemic-only ("post hoc" added), positive controls, per-model breakdown |
19 composition method not in prereg (fine, descriptive) | 20 no analysis in prereg left unreported
Score after: 7.1.

## Scans 13-19 (judgment passes over the full text; 20 sub-purposes each, consolidated findings)
13 structure/flow: section order sound; limitations as run-in; conclusion forward-looking; no roadmap (space); duplicate intro sentence removed from Discussion.
14 abstract: 10 sentences/231 words; two Wh-cleft/short verdicts merged into colon payoffs; "We find" added; p consistent with text; novelty narrowed.
15 introduction: 4 manufactured short verdicts merged; "it is not a certainty ratchet" -> "the wrong name"; contributions (1)-(3) + release sentence; real research question kept.
16 results: short verdicts merged (4.1-4.5); "In each model separately"; "We see the same shape"; "We find that instructing"; composition numbers corrected earlier.
17 discussion/limits/conclusion: "however" mid-sentence; method paragraph trimmed; limitations carry 8 admissions incl. n=60, biomedical-only, exact-match floor, one NLI model.
18 AI-tell audit: 0 dashes, 0 Wh-clefts, "entirely" cut, "not X, it is Y" 0 real hits, "rather than" 6 (all substantive), -ing tails are procedural participles, no rule-of-three padding, no copula avoidance, no promotional vocabulary.
19 grammar/usage: agreement ok ("Sixty abstracts is small" kept as quantity), hyphenation consistent, quotes LaTeX-style, p-values hyphen, no doubled words, i.e./e.g. absent.

## Scan 20: style-corpus imitation (measured, 21 human-written pre-2023 papers + Sumner BMJ full text)
Before: short8 14.0% (human max 7.3%), long40 17.2%, we 0.95/100w, passive 0.20/100w (human min 0.44), However 0%, In/For/This openers 2.5% (human min 7.2%).
After: mean 24.7 (median 22.9), sd 11.4 (11.4), short8 2.4% (2.9%), long40 8.3% (7.9%), we 1.1, passive 0.55, However 1.2%, In/For/This 9.5%, 1-sentence paras 5%. All ten metrics inside the human range.
Method: 33 sentence splits, 10 passive conversions in methods, 9 In/For/This re-leads, 3 "we find" insertions, 1 mid-sentence "however".
Score after: 7.2 (prose no longer reads machine-shaped by measurement; substance unchanged).

## Scan 21: cross-disciplinary reader (20 sub-scans)
NLI and OLS expanded at first use; entailment glossed; log-rank/Holm named tests kept; no undefined acronyms remain (CI = confidence interval in quoted boilerplate); prompts quoted verbatim so a non-ML reader can judge them; no equations; figure captions self-contained.
Score after: 7.2.

## Scan 22: title, TLDR, submission fields
Title kept (user-approved earlier; "vagueness ratchet" defensible since hedge density rises monotonically through ten hops even though precision loss is front-loaded). TLDR drafted for OpenReview. Track: Research. AI-use disclosure and authorship attestation are the user's to answer.

## Final skills pass (ran LAST, after all scans, as instructed)
ml-paper-voice: applied honesty moves (loss reported with the win, surprise flagged, confound disclosed, failure mode named), italic pivot question, italic load-bearing adjectives, bold claim-fragment headings already in place, and a "Practical considerations" appendix with six real engineering scars verified against the repo (one required adding a regression test so the claim is true). Em dashes, numbered Remarks, and three-bullet contribution blocks NOT applied: they conflict with the global no-dash rule and with the measured human corpus.
paper-humanizer: checklist satisfied except the "one sentence under 8 words per page" rule, which the measured corpus contradicts (human median 2.9% short sentences); corpus measurement was followed instead. Acknowledgments omitted (double-blind).
humanizer: 0 em/en dashes, 0 Wh-clefts, 0 copula avoidance, 0 promotional vocabulary, 0 rule-of-three padding, 0 "not X but Y" habit, no signposting, no generic conclusion, no cutoff disclaimers; "silently" x3 -> x1; "at all" x2 -> x1.
stop-slop: adverbs pruned to number hedges and statistical terms; no filler openers; score 38/50 (directness 8, rhythm 8, trust 8, authenticity 7, density 7).

## Scan 23: final integrity
numbers traceable: clean | refs/bib: clean | LaTeX: 0 errors, 0 overfull | main text ends page 8, references page 9, appendix page 10 (CFP: references and appendices unlimited) | anonymity: only the user's URL placeholder | all 10 style metrics inside the human-corpus range | tests: ALL PASS | supplement rebuilt with 0 leaks | repo synced.
FINAL SCORE: 7.3 / 10 (honest). Up from 6.5-7 at session start. Ceiling still set by three small open-weight models, one NLI model, biomedical-only corpus, and a preregistered H2 that came out null.

## Scan 24: /humanizer rerun (user-invoked after scan 23)
1 review scan-23 state (clean) | 2 "are known to" doubled in abstract -> "already overgeneralize" | 3 "instead" x3 in abstract+intro -> intro reworded ("The loss lands on precision") |
4 intro two stacked punch sentences -> closer merged into the preceding sentence | 5 "This is vagueness:" aphorism -> plain statement | 6 "We find that" x5 -> x3 |
7 Discussion method paragraph: abstract-noun triad + "argues for a method" -> two concrete claims | 8 harness-outlasts-numbers line stated twice -> kept once (Conclusion) |
9 "rather than" x7 -> x5 (removed the one I added, and "in proportion rather than in count") | 10 "matters" x6 -> x4 | 11 Wh-cleft I introduced caught by scan.py vocab -> removed |
12 validation parenthetical question -> declarative (questions now 1, the intro pivot) | 13 predicate "open-weight" -> "open weight" | 14 em/en dashes: 0 | 15 curly quotes: 0 | 16 bold-colon lists: 0 |
17 numbers scan clean (no value touched) | 18 build 0 errors 0 overfull, conclusion page 8, references page 9 | 19 ten style metrics recomputed with the scan-23 definitions: all in the human range (in_open 0.089, passive 0.572, short8 0.018, long40 0.095) | 20 anonymity guard: only the user's URL placeholder.
Score after: 7.3 (unchanged; prose-only pass, no claim moved).

## Scan 25: /paper-humanizer rerun (user-invoked after scan 24; reference.md Parts A and C reread)
1 review scan-24 diff (clean) | 2 conclusion reordered so it ends on the forward-looking wish (C22) | 3 two long-then-short verdicts added ("Truncation does not explain it." / "The curves then flatten.") |
4 one serial comma allowed to drift (A6; forbidden list bans perfectly consistent typography) | 5 run-in label style: bold period throughout, consistent | 6 dash style: none in prose, 0 per page |
7 candid first-person admissions naming the cause: Llama token footnote, spurious-null section, "where power ran out", six appendix scars | 8 exact hardware and wall-clock: Kaggle T4, NF4, ~5 h/model, 12 h session limit |
9 unrounded numbers: 4,920 samples, 1,560 and 1,710 differences, 287 tokens | 10 lists of 4 and 5 items present (no fixed list length) | 11 footnotes carry caveats (2) |
12 contractions: "can't" x2; second person "you" x1; surname-as-subject cites present | 13 strong evaluatives at ~1/page: "handily", "dismal", "cheap trick" |
14 crucial/leverage/delve/"worth noting": 0 in prose (delving only in the Kobak title) | 15 no bullets, no summary section, Limitations kept as a run-in inside Discussion (workshop norm) |
16 acknowledgments omitted (double-blind) | 17 errors NOT injected (rule: only on explicit request) | 18 numbers scan clean; build 0 errors 0 overfull; conclusion page 8, references page 9 |
19 ten style metrics vs 21-paper corpus: all in range, short8 now 0.029 (corpus median) | 20 short-sentence rule of the skill still overridden by the larger measured corpus, as in scan 8.
Score after: 7.3 (unchanged).

## Scan 26: /stop-slop rerun (user-invoked after scan 25; phrases.md and structures.md reread)
1 review scan-25 diff (clean) | 2 emphasis crutch "The answer matters, because" in the abstract -> cut, reason stated directly | 3 adverbs: "nearly produced a false result" -> "produced a false result on its first run"; "flat to slightly declining" -> "flat" (the number sits beside it); "immediately" -> "at the first hop" |
4 four passives with an obvious actor -> "we" (drew abstracts, generate chains, fixed the preregistration, replaced whole-document scoring); passive100 now 0.502, still above the human floor 0.441, so the remaining 21 methods passives stay (reference D13) |
5 three sentences of 49-51 words split at their colon/semicolon; the 50-word stratum definition and the 56-word release inventory kept as lists (reference A3) | 6 flat runs 3 -> 1 (H2 caveat shortened, composition sentence split, Limitations floor sentence shortened) |
7 "rather than" 5 -> 3 | 8 throat-clearing, "It turns out", "This matters", binary contrasts, negative listings, What-if setups: 0 | 9 false agency: academic conventions only (figure shows, curve flattens) | 10 meta-joiners: 0 |
11 vague declaratives: 0 (each "worse"/"matters" is followed by the specific thing in the same sentence) | 12 quotables: harness-over-numbers line kept as the honest caveat | 13 em dashes 0 |
14 >35-word sentences: 28 of 174 remain, kept because the 21-paper corpus has long40 in [0.026, 0.209] and the paper sits at 0.075 | 15 numbers scan clean | 16 build 0 errors 0 overfull |
17 conclusion page 8, references page 9 | 18 all 10 style metrics in range | 19 anonymity: placeholder only | 20 stop-slop score: directness 8, rhythm 8, trust 8, authenticity 8, density 8 = 40/50 (scan 8 was 38/50).
Score after: 7.3 (unchanged; prose-only pass).

## Scan 27 (hourly loop iteration 1, 2026-08-25 00:45)
Sub-purposes: 1 rhythm flat-runs, 2 filler words, 3 citation tilde spacing, 4 estimator description, 5 numeric traceability sweep (agent), 6 hostile grammar sweep (agent), 7 wall-clock honesty, 8 percentage-vs-points units, 9 untraceable-figure disclosure, 10 corpus metric gate, 11 abstract/body consistency, 12 LaTeX compile, 13 page count, 14 anon check, 15 repo sync, 16 vocab bans, 17 hedge inventory, 18 acronym first-use, 19 typography, 20 bib integrity.

Real fixes:
- Analysis said "nine differences within a chain"; results.json n_deltas=1800 over 180 chains/regime gives TEN. Corrected. This was a substantive misstatement of the estimator.
- "roughly five hours per model" understated the logs (5.86h / 4.14h / 7.09h). Now "between four and seven hours per model".
- "about 3% of the original numbers" was percentage points, not percent. Now "about three points".
- Six missing ~ before \citep.
- Two flat rhythm runs killed (Intro 20/18/19, Limitations 31/31/34).
- Disclosed in Reproducibility that the 0.056 self-entailment mean and 287-token median premise come from the discarded pre-fix run and are not in the archive.

Agent verification: ~90 numeric values traced to release JSONs, zero mismatches, two untraceable (now disclosed).
Corpus metrics all inside 21-paper human range: mean 24.19, sd 11.20, short8 0.031, long40 0.080, we100 1.02, passive100 0.485, however 0.012, we_open 0.117, in_open 0.093.
Score: 7.4/10 (up 0.1 from the estimator-description fix; prose was already at ceiling for this evidence base).
Outstanding: [ANONYMIZED REPOSITORY URL] placeholder, user action.

## Scan 28 (hourly loop iteration 2, 2026-08-25 01:45)
Sub-purposes: 1 page-limit regression, 2 machine-authorship cold read (agent), 3 adversarial AISciK reviewer (agent), 4 instrument-confound disclosure, 5 causal ceiling caveat, 6 composition caveat placement, 7 geometric-decay preemption, 8 rhetorical symmetry, 9 abstract-noun subjects, 10 template section closers, 11 prereg callback phrasing, 12 vocab bans, 13 participle audit, 14 corpus metric gate, 15 numbers, 16 refs, 17 bib, 18 typography, 19 compile, 20 repo sync.

Page-limit regression: scan 27's two added sentences pushed the Conclusion to page 9. Condensed, main text back inside 8 pages.

Substantive additions from the adversarial reviewer (both verified in source before acting):
- src/instruments/entailment.py line 91 computes bi_entail = min(fwd, bwd), and the paper itself disqualifies backward entailment four pages later. Table 1's caption now carries that caveat at the point of use.
- src/instruments/causal.py causal_strength() is max over sentences, so the H1 causal null is a ceiling statistic. Now stated at first mention.
- composed.json geometric_rho_for_reference 0.935 predicts 0.87 qualifier survival at two hops against a measured 0.62. That comparison now appears in 4.6 and preempts the "just exponential decay" objection.
- Citation-hop-is-not-a-summarization-event caveat moved from Limitations into 4.6 next to the headline retention numbers.

Prose: 12 machine-tell edits (ratchet metaphor split, thus-triad wrap-up, discussion antithesis, abstract-noun aphorism, "Note that" opener, conclusion triad, three template subsection closers, one deleted empty closer).
OVERRIDES recorded: kept the numbered contributions sentence (NeurIPS norm, ml-paper-voice mandates a three-item block) and the single italic pivot question (ml-paper-voice allows exactly one). Discussion flat-runs=1 is the Limitations enumeration, left deliberately.
Corpus metrics all in range: mean 23.59, sd 10.85.
Cold-read authorship verdict before these edits: 30/100 human. Not remeasured after, so unverified.
Score: 7.6/10. The +0.2 is the two instrument caveats, which close the two objections the reviewer called capable of sinking it.
Outstanding: [ANONYMIZED REPOSITORY URL] placeholder.

## Scan 29 (hourly loop iteration 3, 2026-08-25 02:45)
Sub-purposes: 1 scan.py full, 2 appendix grammar, 3 caption audit, 4 contraction consistency, 5 authorship re-score (agent), 6 real-corpus tone audit (agent, 8 fetched papers), 7 duplicate formulation, 8 conclusion triad, 9 discussion antithesis, 10 self-narrating prose, 11 related-work antithesis, 12 second-person address, 13 comma splice, 14 hypothesis phrasing, 15 corpus metric gate, 16 numbers, 17 refs, 18 bib, 19 typography, 20 repo sync.

Authorship cold read: 30/100 before scan 28's edits, 64/100 after. Six further findings applied.
Real corpus fetched by agent (ACL 2025 Broken Telephone, ACL 2020 Maynez, TACL 2022 SummaC, RSOS 2025 Peters, EMNLP-IJCNLP 2019 Yu, COLING 2020 Yu, Findings EMNLP 2024 Fang, EMNLP 2025 MetaFaith). Divergences fixed:
- Second person "you" appeared three times; none of the eight real papers address the reader inside Results. All three removed.
- "...without flipping any sign, H3 predicted this, and..." was a comma splice I introduced in scan 28. Now a separate sentence.
- "We had reasons to expect the second case" replaced with "We expected the second case, since", matching the corpus phrasing for an a priori hypothesis.
- Duplicate "passed through any unassisted summarization" formulation in Introduction and 4.6 removed.
Appendix: "warns if it had to" tense slip fixed.
OVERRIDE recorded: kept the short epigram "That prediction did not survive the data." The corpus agent found no analogue in eight papers, but short8 sits at 0.041 inside the measured 21-paper range [0.006, 0.073], and the sentence carries the paper's central reversal.
DECLINED: moving the case study to a boxed figure. It would cost roughly half a page against a hard 8-page main-text limit.
Corpus metrics all in range: mean 23.23, sd 10.95.
Score: 7.6/10, unchanged. This pass moved prose only; no claim, number, or instrument description changed.
Outstanding: [ANONYMIZED REPOSITORY URL] placeholder.

## Scan 30 (hourly loop iteration 4, 2026-08-25 03:45)
Sub-purposes: 1 scan.py full, 2 self-introduced tells, 3 claim-evidence audit (agent), 4 H3 verdict accuracy, 5 Holm arithmetic, 6 compression-direction error, 7 single-annotator scope, 8 subsection title accuracy, 9 page limit, 10 figure sizing, 11 duplicate provenance sentence, 12 corpus gate, 13 rhythm, 14 numbers, 15 refs, 16 bib, 17 typography, 18 headings, 19 compile, 20 repo sync.

REAL CLAIM ERRORS FIXED (this is the important part of this pass):
- "reduces the drift magnitude of every marker" was FALSE. H3_regime.causal_strength has drift_conservative 0.0128 > drift_neutral 0.0067, reduction_share -0.9167, so conservative prompting moves causal strength the other way. Now "four of the five markers", with the causal exception stated and its own null p = 0.66 given. The subsection title changed from "damps every rate" to "damps four of five rates".
- "every rate remains significantly nonzero" was also FALSE: causal_strength conservative p_holm = 0.266. Now "each of those four rates". The agent missed this one; found by hand from results.json.
- "The price is compression" was backwards, since conservative summaries are LONGER (195 vs 123 words). Now "The price is paid in compression".
- Holm adjusted p for the hedge-density H3 interaction now stated inline (0.012 raw, 0.024 after Holm), computed by hand from the five stored interaction p-values. No recomputation.
- "a single annotator" narrowed to "a single human annotator", since the entailment arm is itself one NLI checkpoint.

Self-introduced tells caught: filler "really" and a Wh-cleft opener, both from scan 29 edits. Third consecutive pass where my own humanizer edit created a new defect.
Page limit: additions overflowed to page 9 again; reclaimed by cutting a Results sentence duplicating the Introduction's provenance point and shrinking fig1 to 0.84 and fig2 to 0.80 linewidth.
Corpus metrics all in range, mean 23.29. No flat rhythm runs.
Score: 7.8/10. The H3 correction is the largest single honesty gain of the campaign, since an overstated preregistered verdict is exactly what a referee checking the release JSON would have caught.
Outstanding: [ANONYMIZED REPOSITORY URL] placeholder.

## Scan 31 (hourly loop iteration 5, 2026-08-25 04:45)
Sub-purposes: 1 scan.py full, 2 universal-quantifier sweep by hand, 3 universal-quantifier audit (agent), 4 sensitivity arm coverage, 5 per-model claim scope, 6 truncation claim verifiability, 7 Holm value provenance, 8 page limit, 9 figure sizing, 10 corpus gate, 11 rhythm, 12 numbers, 13 refs, 14 bib, 15 typography, 16 headings, 17 abstract-body consistency, 18 compile, 19 anon, 20 repo sync.

THIRD AND FOURTH FALSE UNIVERSAL CLAIMS FOUND (same class as scan 30's H3 error):
- "reproduces every sign and nearly every magnitude" for the temperature arm was FALSE. results_sensitivity.json has bi_entail estimate null with note "insufficient data", so entailment was never scored on that subset. Now scoped to the four rule-based markers, with the omission stated. Found by hand and independently confirmed by the agent.
- "In each model separately, hedge density rises with no sign flips on any marker" asserted per-model sign stability for all five instruments. paper_numbers.py:164 computes per-model drift for hedge density only. Narrowed to the three models on that one marker.

UNVERIFIABLE CLAIM REPLACED WITH A MECHANISM:
- "3,600 scored generations, all of which completed without truncation" had no backing artifact. "None truncated" appears only as prose in FINDINGS.md:6; no truncation field exists in the chain JSONL and no check exists in src. Replaced with the actual generation budget from src/chains.py:76 (1.5x input length, capped at 1,024 tokens), which a reader can verify. An absence claim needs evidence of absence, and the release has none.

PROVENANCE UPGRADE: the Holm-adjusted 0.024 I computed by hand in scan 30 is stored in paper_numbers.json as h3_interaction_p_holm.hedge_density = 0.0237. The paper's figure now traces to an artifact.

Agent verified and found clean: abstract per-model claim, "all four survive Holm", "fallback fired in every cell", H2 null in both regimes, positive control "no abstract moving the wrong way", 4,200 generation count, two preregistration deviations.
Page overflow reclaimed by tightening three sentences and shrinking fig3 to 0.80 linewidth, matching fig1 and fig2.
Corpus metrics all in range, mean 23.18, sd 10.77.
Score: 7.9/10. Two more false universals removed and one unverifiable absence claim replaced. The claim layer is now materially more defensible than the prose layer.
Outstanding: [ANONYMIZED REPOSITORY URL] placeholder.

## Scan 32 (hourly loop iteration 6, 2026-08-25 05:45)
Sub-purposes: 1 scan.py full, 2 untraceable-number flag, 3 Table 1 digit-by-digit vs results.json, 4 significance stars vs p_holm, 5 bibliography verification (agent, all 14 entries), 6 claims-about-cited-works verification (agent, 10 claims), 7 hedge-list count, 8 null-result phrasing in Discussion, 9 null-result phrasing in Conclusion, 10 causal ceiling consistency, 11 corpus gate, 12 rhythm, 13 vocab, 14 refs, 15 bib, 16 typography, 17 page limit, 18 compile, 19 anon, 20 repo sync.

CITATION AUDIT PASSED. All 14 bibliography entries verified against primary sources (ACL Anthology, arXiv, DOI, PubMed): author lists, titles, venues, volumes, pages, years all correct. No fabricated citations, which is the desk-reject condition at this venue. Nine of ten claims about cited works verified exact, including Peters odds ratio 4.85 CI [3.06, 7.70] behind "nearly five times", Yavchitz RR 5.6 CI [2.8, 11.1], and Liang/Kobak prevalence figures.

ONE CITATION CLAIM CORRECTED:
- The paper credited Mohamed et al. 2025 with "partial mitigation by conservative decoding". That paper frames constrained PROMPTING as its mitigation finding and never tested greedy or beam decoding. Changed to "constrained prompting". Misattributing a cited paper's own headline finding is the kind of error its authors would notice as reviewers.

NULL-RESULT PHRASING TIGHTENED (third pass in a row on this class):
- Discussion "leaves causal language untouched" became "the strongest causal sentence holds its grade", which also matches the ceiling caveat.
- Conclusion "causal language never moved" became "the causal measure did not move". A null is a failure to detect, not a demonstration of absence.

VERIFIED CLEAN: Table 1's twenty estimates and standard errors and five verdict labels match results.json exactly; the *** markers match p_holm. The 101-item hedge list count confirmed directly from src/instruments/hedges.py HYLAND_HEDGES.
scan.py updated to know the two generation-budget constants from src/chains.py:76, with the source recorded in the code.
Corpus metrics all in range, mean 23.20.
Score: 8.0/10. The citation surface is now audited end to end, which removes the single fastest rejection path, and no remaining claim in the paper outruns its evidence as far as six passes of checking can tell.
Outstanding: [ANONYMIZED REPOSITORY URL] placeholder, user action.

## Scan 33 (hourly loop iteration 7, 2026-08-25 06:45)
Sub-purposes: 1 scan.py full, 2 figure-vs-data annotations, 3 PDF font embedding, 4 page geometry hacks, 5 PDF metadata leak, 6 line numbers present, 7 pdfTeX hyperref "(?)" trap, 8 log warnings, 9 named-file existence, 10 preregistration fidelity (agent), 11 hypothesis wording vs prereg, 12 estimator-fallback provenance, 13 undisclosed deviations, 14 H2 preregistered vs exploratory, 15 prereg edit history, 16 numbers, 17 refs, 18 bib, 19 typography, 20 repo sync.

PAPER: no changes needed. Every scan clean, all claims verified in earlier passes still hold.

VERIFIED THIS PASS (all previously unchecked):
- Figure 1's inline annotations (+0.061/step p=6.9e-08, +0.007 p=0.7, -0.049 p=1.2e-40) match results.json Holm values exactly; fig3's median depth 2 and 0.5 floor match composed.json.
- PDF compliance: no \vspace/\small/geometry squeezing, all fonts embedded, letter size, empty Title and Author metadata, 382 line numbers present for double-blind, zero log warnings, zero "(?)" citation artifacts.
- Every file named in Reproducibility exists in the release.
- PREREGISTRATION FIDELITY: H1, H2, H3 stated in the paper almost word for word as preregistered. The cluster-robust OLS fallback with its 1e-10 variance threshold is in src/analysis.py:66-80 and present in the FIRST commit f266c20 (2026-08-13), untouched since, so it was genuinely specified before data. The Phi-3.5 fallback table predates the runs too. No undisclosed deviations exist. The H2 log-rank is the preregistered test and reproduces at p=0.3998 and p=0.2106; the continuous regression lives in a separate script and the paper labels it non-preregistered.

REPO FIX (not the paper): PREREGISTRATION.md claimed "the git commit timestamp of this file is the time lock", singular, while the file has four commits, one of them a cosmetic header change made on 2026-08-22 during manuscript revision. A reviewer following the anonymous link would see that mismatch. The header now states all four commits, what each did, and that the first chain was generated on 2026-08-15 after the two specification commits. The paper's own prose was already accurate and needed no change.

Score: 8.0/10, unchanged. Nothing in the paper moved, and preregistration fidelity was confirmed rather than repaired.
Outstanding: [ANONYMIZED REPOSITORY URL] placeholder, user action.
