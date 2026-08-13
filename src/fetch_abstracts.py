"""Fetch stratified open-access abstracts from PubMed via NCBI E-utilities.

Three claim classes, equal n per class:
  rct    randomized controlled trials whose abstracts report at least one
         numeric effect size with an interval
  obs    observational studies with explicit association language
  null   abstracts whose conclusions state an explicit null result

Operational null rule (documented for the paper's Appendix A): the abstract
matches at least one null phrase (NULL_PHRASES) in its final third, and the
abstract's causal-strength score comes from a negated trigger only.

Usage:
  python -m src.fetch_abstracts --per-class 20 --out data/abstracts.jsonl
"""
import argparse
import json
import pathlib
import re
import sys
import time
import xml.etree.ElementTree as ET

import requests

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from src.instruments.numeric import RE_CI, RE_EFFECT  # noqa: E402

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
OA = "pubmed pmc open access[filter]"
DATE = "2015:2024[dp]"

QUERIES = {
    "rct": f"Randomized Controlled Trial[pt] AND {OA} AND {DATE} AND hasabstract",
    "obs": ("(Cohort Studies[MeSH] OR Case-Control Studies[MeSH] OR "
            f"Cross-Sectional Studies[MeSH]) AND {OA} AND {DATE} AND hasabstract"),
    "null": (f"{OA} AND {DATE} AND hasabstract AND "
             "(\"no significant difference\"[tiab] OR \"did not differ\"[tiab] "
             "OR \"no association\"[tiab] OR \"was not associated\"[tiab] "
             "OR \"did not improve\"[tiab] OR \"did not reduce\"[tiab])"),
}

NULL_PHRASES = re.compile(
    r"no significant (?:difference|effect|association|improvement)|"
    r"did not (?:differ|improve|reduce|increase|decrease|affect)|"
    r"no (?:association|difference|effect|evidence of)|"
    r"was not (?:associated|significant|superior)|failed to (?:show|demonstrate)",
    re.IGNORECASE,
)
RE_ASSOC_LANG = re.compile(
    r"associated with|correlated with|association between", re.IGNORECASE)


def esearch(query: str, retmax: int, retstart: int = 0):
    r = requests.get(f"{EUTILS}/esearch.fcgi", params={
        "db": "pubmed", "term": query, "retmax": retmax,
        "retstart": retstart, "sort": "relevance", "retmode": "json",
    }, timeout=30)
    r.raise_for_status()
    return r.json()["esearchresult"]["idlist"]


def efetch(pmids):
    r = requests.get(f"{EUTILS}/efetch.fcgi", params={
        "db": "pubmed", "id": ",".join(pmids), "retmode": "xml",
        "rettype": "abstract",
    }, timeout=60)
    r.raise_for_status()
    out = []
    root = ET.fromstring(r.content)
    for art in root.findall(".//PubmedArticle"):
        pmid = art.findtext(".//PMID")
        title = art.findtext(".//ArticleTitle") or ""
        parts = [(el.get("Label"), "".join(el.itertext()))
                 for el in art.findall(".//Abstract/AbstractText")]
        abstract = " ".join(
            (f"{lab}: {txt}" if lab else txt) for lab, txt in parts).strip()
        if pmid and abstract:
            out.append({"pmid": pmid, "title": title, "abstract": abstract})
    return out


RE_NEG_BEFORE = re.compile(r"\b(?:no|not|was not|were not)\s*$",
                           re.IGNORECASE)


def _has_positive_assoc(abstract: str) -> bool:
    """Association language not immediately negated ("no association
    between" must not qualify an abstract as an association claim)."""
    for m in RE_ASSOC_LANG.finditer(abstract):
        if not RE_NEG_BEFORE.search(abstract[max(0, m.start() - 12):m.start()]):
            return True
    return False


def _null_tail(abstract: str) -> bool:
    tail = abstract[int(len(abstract) * 2 / 3):]
    return bool(NULL_PHRASES.search(tail))


def qualifies(cls: str, abstract: str) -> bool:
    """Mutually exclusive assignment with null-priority: an abstract whose
    conclusion states a null result belongs to the null stratum no matter
    which query surfaced it. Without this, fetch order silently absorbs
    null-result RCTs into the rct stratum (first-query-wins bias)."""
    if len(abstract.split()) < 150 or len(abstract.split()) > 450:
        return False
    if cls == "rct":
        return (not _null_tail(abstract)
                and bool(RE_CI.search(abstract))
                and bool(RE_EFFECT.search(abstract)))
    if cls == "obs":
        return not _null_tail(abstract) and _has_positive_assoc(abstract)
    if cls == "null":
        return _null_tail(abstract)
    return False


def fetch_class(cls: str, n: int, seen: set):
    kept, start = [], 0
    while len(kept) < n and start < 2000:
        ids = esearch(QUERIES[cls], retmax=100, retstart=start)
        if not ids:
            break
        start += 100
        time.sleep(0.4)
        for batch_start in range(0, len(ids), 50):
            batch = ids[batch_start:batch_start + 50]
            for rec in efetch(batch):
                if rec["pmid"] in seen:
                    continue
                if qualifies(cls, rec["abstract"]):
                    rec["cls"] = cls
                    kept.append(rec)
                    seen.add(rec["pmid"])
                    if len(kept) >= n:
                        return kept
            time.sleep(0.4)
    return kept


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-class", type=int, default=20)
    ap.add_argument("--out", default="data/abstracts.jsonl")
    args = ap.parse_args()

    pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    seen, rows = set(), []
    for cls in ("rct", "obs", "null"):
        got = fetch_class(cls, args.per_class, seen)
        print(f"[fetch] {cls}: {len(got)}/{args.per_class}")
        if len(got) < args.per_class:
            print(f"[fetch] WARNING: short stratum {cls}", file=sys.stderr)
        rows += got
    with open(args.out, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"[fetch] wrote {len(rows)} abstracts -> {args.out}")


if __name__ == "__main__":
    main()
