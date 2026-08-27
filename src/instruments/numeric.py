"""Numeric-fidelity instrument.

Extracts effect sizes, confidence intervals, and p-values by pattern, then
scores a generation against its source: exact retention, rounded retention
(match at fewer decimals), and loss. All comparisons are on numeric value,
not surface string, so "0.50" retains "0.5".
"""
import re

RE_PVAL = re.compile(
    r"\bp\s*(?:[=<>]|≤|≥|<=|>=)\s*(0?\.\d+|\d+(?:\.\d+)?(?:\s*[×x]\s*10\s*[-−]\s*\d+|e-?\d+)?)",
    re.IGNORECASE,
)
RE_EFFECT = re.compile(
    r"\b(?:a?OR|a?RR|a?HR|IRR|SMD|WMD|MD|RD|β|beta|r|d|g|"
    r"odds\s+ratio|risk\s+ratio|hazard\s+ratio|relative\s+risk|"
    r"rate\s+ratio|mean\s+difference|risk\s+difference)"
    r"(?:\s*[\[\(]\s*a?(?:OR|RR|HR|MD|RD|IRR)\s*[\]\)])?"
    r"\s*(?:of|was|were)?\s*[=:,]?\s*([-+−]?\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
RE_CI = re.compile(
    r"(?:9[059](?:\.\d+)?\s*%\s*"
    r"(?:CI|confidence\s+interval)s?"
    r"(?:\s*[\[\(]\s*CI\s*[\]\)])?"
    r"[\s,:=]*[\[\(]?)"
    r"\s*([-+−]?\d+(?:\.\d+)?)\s*(?:to|,|–|—|-)\s*([-+−]?\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
# Negative lookahead: "95% CI" / "95% confidence interval" is reporting
# convention, not a study statistic, and must not count as retained.
RE_PERCENT = re.compile(
    r"([-+−]?\d+(?:\.\d+)?)\s*%(?!\s*(?:CI\b|confidence))", re.IGNORECASE)
# The sign must not follow a digit or a decimal point. Without the
# lookbehind, the hyphen separating a confidence interval's bounds
# ("0.544-0.866", the standard PubMed format) is read as a minus sign,
# so the upper bound becomes -0.866 and can never match the correctly
# signed value the source-side RE_CI pattern extracted.
RE_ANY_NUM = re.compile(r"(?<![\d.])[-+−]?\d+(?:\.\d+)?")


def _to_float(s: str):
    s = s.replace("−", "-").replace(" ", "")
    if "×" in s or "x" in s.lower():
        m = re.match(r"([-+]?\d+(?:\.\d+)?)[×xX]10[-]?(\d+)", s)
        if m:
            return float(m.group(1)) * 10 ** (-int(m.group(2)))
    try:
        return float(s.lower().replace("e-", "e-"))
    except ValueError:
        return None


def extract_stats(text: str):
    """All statistical numbers in the text, as a list of floats
    (p-values, effect sizes, CI bounds, percentages)."""
    vals = []
    for m in RE_PVAL.finditer(text):
        v = _to_float(m.group(1))
        if v is not None:
            vals.append(v)
    for m in RE_EFFECT.finditer(text):
        v = _to_float(m.group(1))
        if v is not None:
            vals.append(v)
    for m in RE_CI.finditer(text):
        for g in m.groups():
            v = _to_float(g)
            if v is not None:
                vals.append(v)
    for m in RE_PERCENT.finditer(text):
        v = _to_float(m.group(1))
        if v is not None:
            vals.append(v)
    return vals


def _rounds_to(src: float, gen: float) -> bool:
    """True if gen equals src rounded to gen's precision (1 or 2 fewer dp)."""
    for dp in (0, 1, 2, 3):
        if abs(round(src, dp) - gen) < 1e-9 and abs(src - gen) > 1e-9:
            return True
    return False


def numeric_fidelity(source: str, gen: str):
    """Returns dict with n_source, retained_exact, retained_rounded, lost,
    and share_exact in [0,1] or None when the source has no stats."""
    src_vals = extract_stats(source)
    # Generation side is deliberately liberal (any number): the question is
    # whether a source statistic survives in ANY surface form ("odds ratio
    # was 0.75" must count even though it lacks the "OR =" pattern).
    gen_vals = [v for v in
                (_to_float(m.group(0)) for m in RE_ANY_NUM.finditer(gen))
                if v is not None]
    n = len(src_vals)
    if n == 0:
        return {"n_source": 0, "retained_exact": 0, "retained_rounded": 0,
                "lost": 0, "share_exact": None}
    gen_pool = list(gen_vals)
    exact = rounded = 0
    for sv in src_vals:
        hit = next((g for g in gen_pool if abs(g - sv) < 1e-9), None)
        if hit is not None:
            exact += 1
            gen_pool.remove(hit)
            continue
        hit = next((g for g in gen_pool if _rounds_to(sv, g)), None)
        if hit is not None:
            rounded += 1
            gen_pool.remove(hit)
    return {
        "n_source": n,
        "retained_exact": exact,
        "retained_rounded": rounded,
        "lost": n - exact - rounded,
        "share_exact": exact / n,
    }
