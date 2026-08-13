"""Hedge density instrument.

Counts matches against the hedge sublist of Hyland's (2005) metadiscourse
lexicon, normalized per 100 words. Multi-word items are matched as phrases;
single words on token boundaries. Deterministic, case-insensitive.
"""
import re

# Hedge items from Hyland (2005), Metadiscourse, Appendix (hedges category).
HYLAND_HEDGES = [
    "about", "almost", "apparent", "apparently", "appear", "appeared",
    "appears", "approximately", "argue", "argued", "argues", "around",
    "assume", "assumed", "broadly", "certain amount", "certain extent",
    "certain level", "claim", "claimed", "claims", "could", "couldn't",
    "doubt", "doubtful", "essentially", "estimate", "estimated", "fairly",
    "feel", "feels", "felt", "frequently", "from my perspective",
    "from our perspective", "from this perspective", "generally", "guess",
    "indicate", "indicated", "indicates", "in general", "in most cases",
    "in most instances", "in my opinion", "in my view", "in our opinion",
    "in our view", "in this view", "largely", "likely", "mainly", "may",
    "maybe", "might", "mostly", "often", "on the whole", "ought", "perhaps",
    "plausible", "plausibly", "possible", "possibly", "postulate",
    "postulated", "postulates", "presumable", "presumably", "probable",
    "probably", "quite", "rather", "relatively", "roughly", "seem", "seemed",
    "seems", "should", "sometimes", "somewhat", "suggest", "suggested",
    "suggests", "suppose", "supposed", "suspect", "suspects", "tend to",
    "tended to", "tends to", "typical", "typically", "uncertain",
    "uncertainly", "unclear", "unclearly", "unlikely", "usually", "would",
    "wouldn't",
]

# Longest-first so multi-word phrases win over their single-word prefixes.
_PATTERNS = [
    re.compile(r"\b" + re.escape(h).replace(r"\ ", r"\s+") + r"\b", re.IGNORECASE)
    for h in sorted(HYLAND_HEDGES, key=len, reverse=True)
]

_WORD = re.compile(r"[A-Za-z][A-Za-z'-]*")


def word_count(text: str) -> int:
    return len(_WORD.findall(text))


def hedge_count(text: str) -> int:
    """Count hedge occurrences. Each span is counted once; overlapping
    shorter matches inside an already-matched phrase are suppressed."""
    taken = []
    n = 0
    for pat in _PATTERNS:
        for m in pat.finditer(text):
            span = (m.start(), m.end())
            if any(s < span[1] and span[0] < e for s, e in taken):
                continue
            taken.append(span)
            n += 1
    return n


def hedge_density(text: str) -> float:
    """Hedges per 100 words. Returns 0.0 for empty text."""
    w = word_count(text)
    if w == 0:
        return 0.0
    return 100.0 * hedge_count(text) / w
