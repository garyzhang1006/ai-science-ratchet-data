"""Positive controls for the rule-based instruments.

A null result on causal strength is only informative if the instrument
moves when the text's causal language changes, so this script applies two
deterministic transforms to every source abstract and checks that the
score follows: (1) strengthen, replacing associational and hedged-causal
phrases with unqualified causal verbs, and (2) weaken, prefixing causal
verbs with a modal. It does the same for hedge density by inserting one
hedge per sentence and by deleting every hedge. Each control reports the
mean score before and after and the share of abstracts that moved in the
intended direction.

Usage: python -m src.positive_control --abstracts release/abstracts.jsonl \
           --out release/results/positive_control.json
"""
import argparse
import json
import pathlib
import re

import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
from src.instruments.causal import (causal_strength, sentence_causal_strength,
                                    split_sentences)
from src.instruments.hedges import HYLAND_HEDGES, hedge_density

STRENGTHEN = [
    (r"\b(?:was|were|is|are)\s+(?:significantly\s+)?associated with\b", "causes"),
    (r"\b(?:was|were|is|are)\s+(?:significantly\s+)?correlated with\b", "causes"),
    (r"\bassociated with\b", "causing"),
    (r"\bcorrelated with\b", "causing"),
    (r"\blinked to\b", "causes"),
    (r"\bcontribute[sd]? to\b", "causes"),
    (r"\b(?:may|might|could|appears? to|seems? to)\s+(reduce|increase|improve|decrease|prevent|lower|raise|cause)", r"\1s"),
]
WEAKEN = [
    (r"\b(reduce[sd]?|increase[sd]?|improve[sd]?|decrease[sd]?|prevent(?:s|ed)?|cause[sd]?|lower(?:s|ed)?|raise[sd]?)\b", r"may \1"),
    (r"\bmay (\w+?)(?:s|d|ed)\b", r"may \1"),
]
_hedge_pat = re.compile(r"\b(?:" + "|".join(re.escape(h) for h in sorted(HYLAND_HEDGES, key=len, reverse=True)) + r")\b", re.I)


def apply(rules, text):
    for pat, rep in rules:
        text = re.sub(pat, rep, text, flags=re.I)
    return text


def weaken(text):
    """Demote only sentences the instrument already grades as unqualified
    causal (level 5); touching other sentences turns participial adjectives
    such as "reduced risk" into hedged causal claims and inflates the score."""
    return " ".join(apply(WEAKEN, s) if sentence_causal_strength(s) == 5 else s
                    for s in split_sentences(text))


def add_hedges(text):
    return " ".join(re.sub(r"^(\w)", r"Perhaps \1", s) if not s.lower().startswith("perhaps") else s
                    for s in split_sentences(text))


def strip_hedges(text):
    return re.sub(r"\s{2,}", " ", _hedge_pat.sub("", text))


def control(texts, transform, scorer, direction):
    before = [scorer(t) for t in texts]
    after = [scorer(transform(t)) for t in texts]
    moved = sum(1 for b, a in zip(before, after) if (a - b) * direction > 0)
    unchanged = sum(1 for b, a in zip(before, after) if a == b)
    return {"mean_before": sum(before) / len(before),
            "mean_after": sum(after) / len(after),
            "share_moved_intended": moved / len(texts),
            "share_unchanged": unchanged / len(texts),
            "share_moved_wrong_way": 1 - (moved + unchanged) / len(texts)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--abstracts", default="release/abstracts.jsonl")
    ap.add_argument("--out", default="release/results/positive_control.json")
    args = ap.parse_args()
    texts = [json.loads(l)["abstract"] for l in open(args.abstracts)]
    out = {
        "n_abstracts": len(texts),
        "causal_strengthen": control(texts, lambda t: apply(STRENGTHEN, t), causal_strength, +1),
        "causal_weaken": control(texts, weaken, causal_strength, -1),
        "hedge_add_one_per_sentence": control(texts, add_hedges, hedge_density, +1),
        "hedge_strip_all": control(texts, strip_hedges, hedge_density, -1),
    }
    pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(args.out, "w"), indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
