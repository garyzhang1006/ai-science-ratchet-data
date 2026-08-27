"""Causal-strength instrument.

Grades the strongest claim sentence in a text on a five-point rule-based
scale from no-claim to unqualified causation:

  1  no reported relation between variables
  2  associational language ("associated with", "correlated with")
  3  weak/indirect causal language ("linked to", "contributes to")
  4  hedged causal language (modal + causal verb: "may reduce",
     "could improve", "appears to increase")
  5  unqualified causal language ("reduces", "causes", "improves")

A negation within a short window before the trigger demotes the sentence:
negated causal ("did not reduce") counts as level 2 at most (a reported
relation is asserted to be absent), and negated association counts as
level 1. The text score is the max over its sentences.
"""
import re

SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z(\[])")

# Bare "lower/raise/slow/boost/increase/decrease" double as adjectives or
# nouns ("lower risk", "an increase in"), so those need a suffix here and
# are handled bare only after a modal or "to" (RE_BARE_AMBIG below).
CAUSAL_VERBS = (
    r"cause[sd]?|caus(?:es|ing)|reduce[sd]?|reduc(?:es|ing)|"
    r"increase[sd]|increas(?:es|ing)|decrease[sd]|decreas(?:es|ing)|"
    r"improve[sd]?|improv(?:es|ing)|prevent(?:s|ed|ing)?|"
    r"lower(?:s|ed|ing)|rais(?:es|ed|ing)|"
    r"lead(?:s|ing)?\s+to|led\s+to|result(?:s|ed|ing)?\s+in|"
    r"induc(?:es|ed|ing)|induce|"
    r"protect(?:s|ed|ing)?\s+against|eliminat(?:es|ed|ing)|eliminate|"
    r"boost(?:s|ed|ing)|enhanc(?:es|ed|ing)|enhance|"
    r"impair(?:s|ed|ing)?|worsen(?:s|ed|ing)?|slow(?:s|ed|ing)"
)
BARE_AMBIG = r"lower|raise|slow|boost|increase|decrease"
# Participle forms acting as adjectives ("associated with increased risk"):
# skipped when the previous word is a preposition/article.
PARTICIPLES = {"increased", "decreased", "reduced", "improved", "impaired",
               "lowered", "raised", "boosted", "worsened", "slowed",
               "enhanced", "caused", "prevented", "eliminated", "induced"}
ADJ_CONTEXT = {"with", "of", "in", "to", "and", "or", "the", "a", "an",
               "for", "on", "at", "by", "between"}
WEAK_CAUSAL = (
    r"linked?\s+to|link(?:s|ed)?\s+with|contribute[sd]?\s+to|"
    r"plays?\s+a\s+role\s+in|played\s+a\s+role\s+in|"
    r"implicated\s+in|influence[sd]?|affect(?:s|ed)?|impact(?:s|ed)?"
)
ASSOC = (
    r"associat(?:ed|ion|ions)\s+(?:with|between)|correlat(?:ed|es|ion)\s+with|"
    r"related\s+to|relationship\s+(?:with|between)|predict(?:s|ed|or|ors)?\s+(?:of|for)?|"
    r"higher\s+(?:risk|odds|rates?)\s+of|lower\s+(?:risk|odds|rates?)\s+of"
)
MODALS = r"may|might|could|can|appears?\s+to|appeared\s+to|seems?\s+to|seemed\s+to|likely\s+(?:to)?|potentially|possibly"
NEG = r"\b(?:no|not|n't|never|neither|nor|without|did\s+not|does\s+not|do\s+not|was\s+not|were\s+not|failed\s+to)\b"

RE_CAUSAL = re.compile(r"\b(?:%s)\b" % CAUSAL_VERBS, re.IGNORECASE)
RE_BARE_AMBIG = re.compile(r"\b(?:%s)\b" % BARE_AMBIG, re.IGNORECASE)
RE_EVIDENCE_VERB = re.compile(
    r"\b(?:shown|found|demonstrated|reported|observed|proven|known|able|"
    r"expected|tends?|tended)\s+to\W*$", re.IGNORECASE)
RE_PREV_WORD = re.compile(r"([A-Za-z']+)\W*$")
RE_WEAK = re.compile(r"\b(?:%s)\b" % WEAK_CAUSAL, re.IGNORECASE)
RE_ASSOC = re.compile(r"\b(?:%s)\b" % ASSOC, re.IGNORECASE)
RE_MODAL = re.compile(r"\b(?:%s)\b" % MODALS, re.IGNORECASE)
RE_NEG = re.compile(NEG, re.IGNORECASE)

_NEG_WINDOW = 40  # characters before the trigger scanned for negation


# A clause boundary resets the negation scope: "There were no dropouts;
# the treatment reduced anxiety" must not read the unrelated "no". A
# coordinating conjunction opens a new clause whether or not a comma precedes
# it, so the third branch is needed; without it the documented example fails
# in its commaless form and the safety clause inverts the efficacy claim.
RE_CLAUSE_BOUNDARY = re.compile(
    r"[;:]"
    r"|,\s*(?:and|but|while|whereas|although)\b"
    r"|\s+(?:and|but|while|whereas|although)\s+", re.IGNORECASE)


def _negated(sentence: str, start: int) -> bool:
    window = sentence[max(0, start - _NEG_WINDOW):start]
    parts = RE_CLAUSE_BOUNDARY.split(window)
    return bool(RE_NEG.search(parts[-1]))


def _prev_word(sentence: str, start: int) -> str:
    m = RE_PREV_WORD.search(sentence[:start])
    return m.group(1).lower() if m else ""


def sentence_causal_strength(sentence: str) -> int:
    best = 1
    for m in RE_CAUSAL.finditer(sentence):
        word = m.group(0).lower()
        if word in PARTICIPLES and _prev_word(sentence, m.start()) in ADJ_CONTEXT:
            continue  # adjectival use, not a claim verb
        if _negated(sentence, m.start()):
            best = max(best, 2)
            continue
        pre = sentence[max(0, m.start() - _NEG_WINDOW):m.start()]
        if RE_MODAL.search(pre):
            best = max(best, 4)
        else:
            best = max(best, 5)
    for m in RE_BARE_AMBIG.finditer(sentence):
        pre = sentence[max(0, m.start() - _NEG_WINDOW):m.start()]
        prev = _prev_word(sentence, m.start())
        # "to lower" counts only after an evidence verb ("shown to lower"),
        # not after e.g. "linked to lower risk" (adjectival).
        infinitive_ok = (prev == "to" and RE_EVIDENCE_VERB.search(
            sentence[max(0, m.start() - _NEG_WINDOW):m.start()]))
        if infinitive_ok or RE_MODAL.search(pre):
            if _negated(sentence, m.start()):
                best = max(best, 2)
            elif RE_MODAL.search(pre):
                best = max(best, 4)
            else:
                best = max(best, 5)  # "shown to lower ..."
    if best < 4:
        for m in RE_WEAK.finditer(sentence):
            if _negated(sentence, m.start()):
                best = max(best, 2)
            elif RE_MODAL.search(sentence[max(0, m.start() - _NEG_WINDOW):m.start()]):
                best = max(best, 3)
            else:
                best = max(best, 3)
    if best < 3:
        for m in RE_ASSOC.finditer(sentence):
            best = max(best, 1 if _negated(sentence, m.start()) else 2)
    return best


def split_sentences(text: str):
    return [s.strip() for s in SENT_SPLIT.split(text) if s.strip()]


def causal_strength(text: str) -> int:
    """Max sentence-level causal strength; 1 for empty text."""
    sents = split_sentences(text)
    if not sents:
        return 1
    return max(sentence_causal_strength(s) for s in sents)


def core_claim_sentence(text: str) -> str:
    """The strongest claim sentence: max causal strength, ties broken by
    presence of numbers, then by length. Used as the H2 core finding."""
    sents = split_sentences(text)
    if not sents:
        return ""
    has_num = re.compile(r"\d")
    return max(
        sents,
        key=lambda s: (sentence_causal_strength(s), bool(has_num.search(s)), len(s)),
    )
