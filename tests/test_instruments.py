"""Instrument smoke tests with known-answer checks."""
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))

from src.instruments.hedges import hedge_density, hedge_count, word_count
from src.instruments.causal import (causal_strength, core_claim_sentence,
                                    sentence_causal_strength)
from src.instruments.numeric import extract_stats, numeric_fidelity
from src.instruments.qualifiers import extract_qualifiers, qualifier_retention

fails = []


def check(name, got, want):
    ok = got == want
    if not ok:
        fails.append(name)
    print(f"{'PASS' if ok else 'FAIL'} {name}: got {got!r} want {want!r}")


def check_approx(name, got, want, tol=1e-6):
    ok = abs(got - want) < tol
    if not ok:
        fails.append(name)
    print(f"{'PASS' if ok else 'FAIL'} {name}: got {got!r} want {want!r}")


# --- hedges ---
check("hedge none", hedge_count("This drug reduces mortality."), 0)
check("hedge two", hedge_count("This may suggest a benefit."), 2)
check("hedge phrase once",
      hedge_count("In most cases the effect holds."), 1)  # phrase, not 'most'
check_approx("hedge density", hedge_density("It may work."), 100.0 * 1 / 3)

# --- causal ---
check("causal assoc", causal_strength("Coffee was associated with lower risk."), 2)
check("causal weak", causal_strength("Coffee is linked to lower risk."), 3)
check("causal hedged", causal_strength("Coffee may reduce risk."), 4)
check("causal strong", causal_strength("Coffee reduces risk of stroke."), 5)
check("causal negated", causal_strength("Coffee did not reduce risk."), 2)
check("causal none", causal_strength("We enrolled 40 participants."), 1)
check("causal max over sentences",
      causal_strength("Coffee was associated with risk. Tea reduces risk."), 5)
core = core_claim_sentence(
    "We enrolled 40 adults. Treatment reduced mortality by 20% (p=0.01). "
    "Side effects were mild.")
check("core sentence", "reduced mortality" in core, True)

# --- numeric ---
s = "OR = 0.75 (95% CI 0.60 to 0.94, p=0.02) and a 12% reduction"
vals = extract_stats(s)
check("numeric count", len(vals) >= 4, True)
nf = numeric_fidelity(s, "The odds ratio was 0.75 (p=0.02).")
check("numeric exact 2", nf["retained_exact"], 2)
nf2 = numeric_fidelity("The effect was OR = 0.752.", "The OR was 0.75.")
check("numeric rounded", nf2["retained_rounded"], 1)
nf3 = numeric_fidelity("No numbers here at all.", "Still none.")
check("numeric none -> None", nf3["share_exact"], None)

# --- qualifiers ---
src = ("In postmenopausal women, 50 mg/day of the drug was tested in a "
       "randomized double-blind placebo-controlled trial.")
q = extract_qualifiers(src)
kinds = sorted(set(k for k, _ in q))
check("qualifier kinds", kinds, ["dosage", "population", "setting"])
qr_keep = qualifier_retention(src, src)
check_approx("qualifier self-retention", qr_keep["share"], 1.0)
qr_drop = qualifier_retention(src, "The drug was tested in a trial.")
check("qualifier drop", qr_drop["share"] < 0.5, True)
qr_none = qualifier_retention("Nothing here.", "Nothing.")
check("qualifier none -> None", qr_none["share"], None)

print()
if fails:
    print("FAILURES:", fails)
    sys.exit(1)
print("ALL PASS")
