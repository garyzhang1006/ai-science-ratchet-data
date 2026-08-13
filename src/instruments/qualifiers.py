"""Qualifier-retention instrument.

Extracts three families of scope qualifiers from the source and checks
their survival in a generation by fuzzy token overlap:

  population  "in adults", "among postmenopausal women", "patients with T2D"
  dosage      "50 mg/day", "2 g", "600 IU"
  setting     study-design terms ("randomized", "double-blind", "cohort", ...)

Retention = share of source qualifiers present in the generation
(token-overlap >= 0.6 for multi-token qualifiers, exact for single tokens).
"""
import re

RE_POP = re.compile(
    r"\b(?:in|among|of)\s+((?:[a-z-]+\s+){0,3}?"
    r"(?:adults?|children|adolescents?|infants?|women|men|males?|females?|"
    r"patients?|participants?|subjects?|individuals?|volunteers?|"
    r"mice|rats|smokers?|non-smokers|elderly|seniors?|pregnan(?:t|cy)\s*\w*))\b"
    r"((?:\s+(?:with|without|aged|over|under)\s+[\w\s.-]{1,40}?)?)(?=[,.;)]|\s+(?:who|were|was|and|or)\b|$)",
    re.IGNORECASE,
)
RE_DOSE = re.compile(
    r"\b(\d+(?:\.\d+)?\s*(?:mg|g|mcg|µg|ug|IU|units?|m[lL])"
    r"(?:\s*/\s*(?:day|d|kg|week|wk|dose))?)\b"
)
DESIGN_TERMS = [
    "randomized", "randomised", "double-blind", "single-blind",
    "placebo-controlled", "placebo", "crossover", "open-label",
    "cohort", "case-control", "cross-sectional", "prospective",
    "retrospective", "longitudinal", "meta-analysis", "systematic review",
    "registry", "observational", "pilot", "multicenter", "multicentre",
]
RE_DESIGN = re.compile(
    r"\b(?:" + "|".join(re.escape(t) for t in DESIGN_TERMS) + r")\b",
    re.IGNORECASE,
)

_TOKEN = re.compile(r"[a-z0-9][a-z0-9./-]*")


def _tokens(s: str):
    return set(_TOKEN.findall(s.lower()))


def extract_qualifiers(text: str):
    quals = []
    for m in RE_POP.finditer(text):
        q = (m.group(1) + (m.group(2) or "")).strip()
        if q:
            quals.append(("population", q))
    for m in RE_DOSE.finditer(text):
        quals.append(("dosage", m.group(1).strip()))
    for m in RE_DESIGN.finditer(text):
        quals.append(("setting", m.group(0).lower()))
    # dedupe on normalized token set
    seen, out = set(), []
    for kind, q in quals:
        key = (kind, frozenset(_tokens(q)))
        if key not in seen:
            seen.add(key)
            out.append((kind, q))
    return out


def _present(qual: str, gen_tokens: set) -> bool:
    qt = _tokens(qual)
    if not qt:
        return False
    if len(qt) == 1:
        return qt <= gen_tokens
    return len(qt & gen_tokens) / len(qt) >= 0.6


def qualifier_retention(source: str, gen: str):
    """Dict with n_source, retained, and share in [0,1] or None when the
    source has no extractable qualifiers."""
    quals = extract_qualifiers(source)
    if not quals:
        return {"n_source": 0, "retained": 0, "share": None}
    gt = _tokens(gen)
    kept = sum(1 for _, q in quals if _present(q, gt))
    return {"n_source": len(quals), "retained": kept, "share": kept / len(quals)}
