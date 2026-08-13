"""Apply all five instruments to every generation in the chain files.

Reads the abstracts file (generation 0) plus one or more chains JSONL
files, scores every generation against its source abstract, and writes one
CSV row per (pmid, model, regime, generation). Generation 0 rows carry the
source's own marker values so trajectories start at the source.

NLI is the slow step; on CPU expect roughly 1-2 s per generation. Pass
--no-nli to fill entailment columns with NaN for a quick instrument pass.

Usage:
  python -m src.score --abstracts data/abstracts.jsonl \
      --chains data/chains_*.jsonl --out results/scores.csv
"""
import argparse
import glob
import json
import math
import pathlib
import sys

import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from src.instruments.hedges import hedge_density  # noqa: E402
from src.instruments.causal import causal_strength, core_claim_sentence  # noqa: E402
from src.instruments.numeric import numeric_fidelity  # noqa: E402
from src.instruments.qualifiers import qualifier_retention  # noqa: E402


def score_row(source: str, text: str, core: str, nli):
    row = {
        "hedge_density": hedge_density(text),
        "causal_strength": causal_strength(text),
    }
    nf = numeric_fidelity(source, text)
    row["numeric_share_exact"] = (math.nan if nf["share_exact"] is None
                                  else nf["share_exact"])
    row["numeric_n_source"] = nf["n_source"]
    qr = qualifier_retention(source, text)
    row["qualifier_share"] = (math.nan if qr["share"] is None
                              else qr["share"])
    row["qualifier_n_source"] = qr["n_source"]
    if nli is not None:
        bi = nli.bidirectional(source, text)
        row.update(bi)
        row["core_entail"] = nli.core_survival(text, core)
    else:
        for k in ("fwd_entail", "fwd_contra", "bwd_entail", "bwd_contra",
                  "bi_entail", "core_entail"):
            row[k] = math.nan
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--abstracts", default="data/abstracts.jsonl")
    ap.add_argument("--chains", nargs="+", required=True)
    ap.add_argument("--out", default="results/scores.csv")
    ap.add_argument("--no-nli", action="store_true")
    ap.add_argument("--nli-model", default=None)
    args = ap.parse_args()

    sources = {json.loads(l)["pmid"]: json.loads(l)
               for l in open(args.abstracts)}
    cores = {pmid: core_claim_sentence(rec["abstract"])
             for pmid, rec in sources.items()}

    nli = None
    if not args.no_nli:
        from src.instruments.entailment import EntailmentScorer
        nli = (EntailmentScorer(args.nli_model) if args.nli_model
               else EntailmentScorer())

    chain_files = []
    for pat in args.chains:
        chain_files += glob.glob(pat)
    if not chain_files:
        sys.exit(f"[score] no chain files match {args.chains}")

    rows = []
    seen_g0 = set()
    seen_rows = set()  # guards against duplicated chain rows reaching stats
    n_dup = 0
    for cf in chain_files:
        for line in open(cf):
            r = json.loads(line)
            src = sources.get(r["pmid"])
            if src is None:
                continue
            row_key = (r["pmid"], r["model"], r["regime"], r["generation"])
            if row_key in seen_rows:
                n_dup += 1
                continue
            seen_rows.add(row_key)
            g0_key = (r["pmid"], r["model"], r["regime"])
            if g0_key not in seen_g0:
                seen_g0.add(g0_key)
                base = score_row(src["abstract"], src["abstract"],
                                 cores[r["pmid"]], nli)
                base.update(pmid=r["pmid"], cls=src["cls"], model=r["model"],
                            regime=r["regime"], generation=0)
                rows.append(base)
            sc = score_row(src["abstract"], r["text"], cores[r["pmid"]], nli)
            sc.update(pmid=r["pmid"], cls=r["cls"], model=r["model"],
                      regime=r["regime"], generation=r["generation"])
            rows.append(sc)
            if len(rows) % 200 == 0:
                print(f"[score] {len(rows)} rows", flush=True)

    if n_dup:
        print(f"[score] WARNING: skipped {n_dup} duplicate chain rows "
              f"(same pmid/model/regime/generation)", flush=True)
    df = pd.DataFrame(rows)
    pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"[score] wrote {len(df)} rows -> {args.out}")


if __name__ == "__main__":
    main()
