"""Estimate the citation-depth distribution of scholarly reuse from
OpenAlex citation paths.

Estimator (documented for the paper's Appendix): starting from each source
article (matched by PMID), walk the citation graph FORWARD (works citing
the current node) for up to --max-depth hops, sampling at most
--branch citing works per node, preferring reviews (OpenAlex
type "review" or title containing "review"/"meta-analysis") as
citation hops. Each sampled endpoint contributes its citation count
as a consumption weight at its path depth. The resulting weighted depth
histogram approximates how many summarization-like hops separate a primary
claim from its typical point of consumption. Assumption, stated in the
paper's limitations: each citation hop is treated as one summarization
event.

OpenAlex is free, no key; polite pool via --mailto.

Usage:
  python -m src.openalex_depth --abstracts data/abstracts.jsonl \
      --out results/depth_distribution.json --mailto you@example.com
"""
import argparse
import json
import pathlib
import random
import time

import requests

API = "https://api.openalex.org"


def get(url, params, mailto, retries=4):
    params = dict(params or {})
    if mailto:
        params["mailto"] = mailto
    for i in range(retries):
        try:
            r = requests.get(url, params=params, timeout=30)
            if r.status_code == 429:
                time.sleep(2 ** i)
                continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException:
            time.sleep(2 ** i)
    return None


def work_by_pmid(pmid, mailto):
    return get(f"{API}/works/pmid:{pmid}", None, mailto)


def citing_works(work_id, mailto, per_page=50):
    wid = work_id.rsplit("/", 1)[-1]
    j = get(f"{API}/works", {
        "filter": f"cites:{wid}",
        "per-page": per_page,
        "select": "id,type,title,cited_by_count",
    }, mailto)
    return (j or {}).get("results", [])


def is_reviewlike(w):
    if w.get("type") == "review":
        return True
    t = (w.get("title") or "").lower()
    return "review" in t or "meta-analysis" in t


def walk(seed_work, mailto, max_depth, branch, rng):
    """Returns list of (depth, weight) consumption samples from one seed.

    A `seen` set guards against convergent citation paths: each work is
    sampled and expanded at most once, at the depth where it was first
    reached, so diamonds in the citation graph cannot double-count a
    subtree's consumption weight."""
    samples = []
    seen = {seed_work["id"]}
    frontier = [(seed_work["id"], 0)]
    while frontier:
        wid, depth = frontier.pop()
        if depth >= max_depth:
            continue
        citers = citing_works(wid, mailto)
        if not citers:
            continue
        new = [w for w in citers if w["id"] not in seen]
        for w in new:
            seen.add(w["id"])
            samples.append((depth + 1, 1 + w.get("cited_by_count", 0)))
        # recurse through review-like citers first (citation hops)
        reviews = [w for w in new if is_reviewlike(w)]
        others = [w for w in new if not is_reviewlike(w)]
        rng.shuffle(reviews)
        rng.shuffle(others)
        for w in (reviews + others)[:branch]:
            frontier.append((w["id"], depth + 1))
        time.sleep(0.15)
    return samples


def weighted_quantile(depths, weights, q):
    order = sorted(range(len(depths)), key=lambda i: depths[i])
    total = sum(weights)
    run = 0.0
    for i in order:
        run += weights[i]
        if run >= q * total:
            return depths[i]
    return depths[order[-1]] if order else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--abstracts", default="data/abstracts.jsonl")
    ap.add_argument("--out", default="results/depth_distribution.json")
    ap.add_argument("--max-depth", type=int, default=4)
    ap.add_argument("--branch", type=int, default=3)
    ap.add_argument("--max-seeds", type=int, default=30)
    ap.add_argument("--seed", type=int, default=20260813)
    ap.add_argument("--mailto", default="")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    pmids = [json.loads(l)["pmid"] for l in open(args.abstracts)]
    rng.shuffle(pmids)
    pmids = pmids[:args.max_seeds]

    all_samples, matched = [], 0
    for pmid in pmids:
        w = work_by_pmid(pmid, args.mailto)
        if not w:
            print(f"[openalex] no work for pmid {pmid}", flush=True)
            continue
        matched += 1
        s = walk(w, args.mailto, args.max_depth, args.branch, rng)
        all_samples += s
        print(f"[openalex] pmid {pmid}: {len(s)} consumption samples",
              flush=True)

    if not all_samples:
        raise SystemExit("[openalex] no samples collected")
    depths = [d for d, _ in all_samples]
    weights = [wt for _, wt in all_samples]
    hist = {}
    for d, wt in all_samples:
        hist[d] = hist.get(d, 0) + wt
    total = sum(hist.values())
    out = {
        "n_seed_works": matched,
        "n_samples": len(all_samples),
        "max_depth_walked": args.max_depth,
        "depth_weights": {str(k): v / total for k, v in sorted(hist.items())},
        "median_depth": weighted_quantile(depths, weights, 0.5),
        "p90_depth": weighted_quantile(depths, weights, 0.9),
        "estimator_note": (
            "Forward citation walk, review-preferring, branch-limited; "
            "endpoint weight = 1 + cited_by_count; one hop treated as one "
            "summarization event."),
    }
    pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(out, f, indent=2)
    print(f"[openalex] median depth {out['median_depth']}, "
          f"p90 {out['p90_depth']} -> {args.out}")


if __name__ == "__main__":
    main()
