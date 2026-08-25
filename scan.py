"""Scripted sub-scans for the AISciK paper. Each check reads paper.tex (and
the compiled PDF text or the release data where needed) and prints
findings. Judgment sub-scans are done by reading; this file covers the
mechanical ones so that every parent scan re-verifies the invariants.

Usage: python3 scan.py [check ...]      (no args = run everything)
"""
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
TEX = (HERE / "paper.tex").read_text()
RELEASE = pathlib.Path("/Users/garyzhang/claude/ai-science-ratchet-data/release")


def body():
    return TEX.split(r"\begin{abstract}")[1].split(r"\begin{thebibliography}")[0]


def prose_of(sec_text):
    t = sec_text
    t = re.sub(r"\\begin\{table\}.*?\\end\{table\}", " ", t, flags=re.S)
    t = re.sub(r"\\begin\{figure\}.*?\\end\{figure\}", " ", t, flags=re.S)
    t = re.sub(r"\\footnote\{(?:[^{}]|\{[^{}]*\})*\}", " ", t)
    t = re.sub(r"\\(?:sub)*section\*?\{[^}]*\}", "\n\n", t)
    t = re.sub(r"\\label\{[^}]*\}", "", t)
    t = re.sub(r"\\cite[pt]?\{[^}]*\}", "CITE", t)
    t = re.sub(r"\\(?:ref|texttt|emph|textbf|url)\{([^}]*)\}", r"\1", t)
    t = re.sub(r"\$[^$]*\$", "NUM", t)
    t = re.sub(r"\\[a-zA-Z]+", "", t)
    return t.replace("``", '"').replace("''", '"').replace("{,}", ",")


def prose():
    return prose_of(body())


def sections():
    out, cur, buf = [], "Abstract", []
    for line in body().splitlines():
        m = re.match(r"\\(?:sub)?section\*?\{([^}]*)\}", line)
        if m:
            out.append((cur, "\n".join(buf)))
            cur, buf = m.group(1), []
        else:
            buf.append(line)
    out.append((cur, "\n".join(buf)))
    return out


def sentences(text):
    text = re.sub(r"\s+", " ", text)
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\\(\"])", text)
    return [s.strip() for s in parts if len(s.split()) > 1]


def fmt_variants(x):
    out = {str(x)}
    for f in ("%.4f", "%.3f", "%.2f", "%.1f", "%.0f", "%.2g", "%.1e", "%.2e"):
        try:
            out.add(f % x)
        except (TypeError, ValueError):
            pass
    if abs(x) <= 1.5:
        out.add("%.0f" % (100 * x))
        out.add("%.1f" % (100 * x))
    return out


def check_numbers():
    """Every numeric token in the body traces to the release data or to a
    design constant."""
    allowed = set()

    def add(x):
        if isinstance(x, bool):
            return
        if isinstance(x, (int, float)):
            allowed.update(fmt_variants(x))
        elif isinstance(x, dict):
            for v in x.values():
                add(v)
        elif isinstance(x, list):
            for v in x:
                add(v)

    for fn in ("results/paper_numbers.json", "results/results.json",
               "results/composed.json", "results/depth_distribution.json",
               "results/results_sensitivity.json"):
        add(json.load(open(RELEASE / fn)))
    design = {"60", "360", "3600", "4200", "600", "20", "10", "11", "9",
              "150", "450", "100", "5", "3", "2", "1", "4", "0.5", "0.7",
              "0.80", "512", "287", "0.056", "0.944", "101", "2026", "1800",
              "1560", "1710", "30", "0", "95", "7", "8", "3.8", "16", "180", "4920", "62", "66", "74", "1.44", "0.50", "3.07", "4.23", "2.62", "4900",
              # generation budget constants, src/chains.py:76
              "1024", "1.5"}
    allowed |= design
    t = re.sub(r"\{,\}", "", body())
    t = re.sub(r"\\times 10\^\{(-?\d+)\}", r"e\1", t)
    found = set(re.findall(r"(?<![A-Za-z\\\d])\d+(?:\.\d+)?(?:e-?\d+)?", t))
    bad = []
    for n in sorted(found):
        base = n.split("e")[0]
        if n in allowed or base in allowed:
            continue
        try:
            f = float(base)
            if ("%.1f" % (f / 100)) in allowed or ("%.3f" % (f / 100)) in allowed:
                continue
            if ("%.4f" % f) in allowed:
                continue
        except ValueError:
            pass
        bad.append(n)
    return ["untraceable number " + n for n in bad]


def check_refs():
    labels = set(re.findall(r"\\label\{([^}]*)\}", TEX))
    refs = set(re.findall(r"\\ref\{([^}]*)\}", TEX))
    cites = set(sum((c.split(",") for c in re.findall(r"\\cite[pt]?\{([^}]*)\}", TEX)), []))
    bibs = set(re.findall(r"\\bibitem\[[^\]]*\]\{([^}]*)\}", TEX))
    out = ["unresolved \\ref " + r for r in refs - labels]
    out += ["unreferenced label " + l for l in labels - refs]
    out += ["unresolved cite " + c for c in cites - bibs]
    out += ["uncited bibitem " + b for b in bibs - cites]
    return out


def check_bib():
    out = []
    for m in re.finditer(r"\\bibitem\[([^\]]*)\]\{([^}]*)\}(.*?)(?=\\bibitem|\\end\{thebibliography\})", TEX, re.S):
        label, key, entry = m.groups()
        if not re.search(r"\b(19|20)\d\d\b", entry):
            out.append(key + ": no year")
        if not re.search(r"\\emph\{|\\newblock In ", entry):
            out.append(key + ": no venue/publisher")
        yr_label = re.search(r"\((\d{4})\)", label)
        yr_entry = re.findall(r"\b((?:19|20)\d\d)\b", entry)
        if yr_label and yr_entry and yr_label.group(1) != yr_entry[-1]:
            out.append(key + ": label year " + yr_label.group(1) + " vs entry " + yr_entry[-1])
    return out


def check_log():
    logp = HERE / "build.log"
    log = logp.read_text(errors="replace") if logp.exists() else ""
    out = ["LaTeX error: " + l.strip() for l in log.splitlines() if l.startswith("!")]
    for m in re.finditer(r"Overfull \\hbox \(([\d.]+)pt", log):
        if float(m.group(1)) > 5:
            out.append("overfull hbox " + m.group(1) + "pt")
    if "undefined" in log.lower():
        out.append("undefined reference or citation in log")
    if "multiply" in log.lower():
        out.append("multiply-defined label")
    m = re.search(r"Output written on paper.pdf \((\d+) pages", log)
    pages = int(m.group(1)) if m else 0
    # CFP: main text 8 pages, references unlimited. Find the page that
    # carries the References heading.
    ref_page = None
    for pg in range(1, pages + 1):
        txt = subprocess.run(["pdftotext", "-f", str(pg), "-l", str(pg), str(HERE / "paper.pdf"), "-"],
                             capture_output=True, text=True).stdout
        if re.search(r"^References\s*$", txt, re.M):
            ref_page = pg
            break
    if ref_page == 9:
        first = subprocess.run(["pdftotext", "-f", "9", "-l", "9", str(HERE / "paper.pdf"), "-"],
                               capture_output=True, text=True).stdout
        first = [l for l in first.splitlines() if l.strip() and not l.strip().isdigit()]
        if first and first[0].strip() == "References":
            ref_page = 8  # main text filled page 8 exactly; references start page 9
    if ref_page is None or ref_page > 8:
        out.append("main text runs past page 8 (References on page %s)" % ref_page)
    # references and appendices are unlimited under the CFP
    return out


def check_anon():
    r = subprocess.run(["sh", str(HERE / "check_anon.sh")], capture_output=True, text=True)
    return [l for l in r.stdout.splitlines() if l.startswith("LEAK")]


def check_typography():
    t = body()
    out = []
    pats = [
        (r"—|–", "dash"),
        (r"\s,", "space before comma"),
        (r"\.\.", "double period"),
        (r"(?<=\S)  +(?=\S)", "double space"),
        (r"\b(\w+) \1\b", "doubled word"),
        (r'(?<!`)"', "straight double quote"),
        (r"(?<!\$)\bp\s*=\s*\d", "p= outside math"),
        (r"\bi\.e\.(?!,)", "i.e. without comma"),
        (r"\be\.g\.(?!,)", "e.g. without comma"),
        (r"[a-z]\.\s+[a-z]", "lowercase sentence start"),
    ]
    for pat, msg in pats:
        for m in re.finditer(pat, t):
            if msg == "doubled word" and m.group(1).lower() in ("that", "had"):
                continue
            ctx = t[max(0, m.start() - 30):m.end() + 30].replace("\n", " ")
            out.append(msg + ": ..." + ctx + "...")
    return out[:40]


VOCAB = ["delve", "crucial", "pivotal", "vital", "holistic", "synergy",
         "tapestry", "testament", "landscape", "navigate", "journey",
         "unlock", "empower", "elevate", "foster", "realm", "game-changer",
         "cutting-edge", "state-of-the-art", "seamless", "leverage",
         "utilize", "facilitate", "underscore", "highlight", "showcase",
         "actually", "genuinely", "simply", "really", "basically",
         "in order to", "it is worth noting", "at the end of the day",
         "not only", "serves as", "stands as", "represents a", "marks a",
         "dive", "robust", "significant", "interestingly", "importantly",
         "notably", "very", "rather than", "at all", "in today's"]


def check_vocab():
    p = prose().lower()
    out = []
    for w in VOCAB:
        n = len(re.findall(r"\b" + re.escape(w) + r"\b", p))
        if n:
            out.append(w + ": " + str(n))
    out.append("rhetorical questions: " + str(p.count("?")))
    out.append("Wh-cleft openers: " + str(len(re.findall(r"(?:^|[.] )What [a-z]", prose()))))
    out.append("not-X-it-is-Y: " + str(len(re.findall(r"\bnot [^.;]{2,40}[;,] (?:it|they|this) (?:is|are)\b", p))))
    out.append("-ing tails: " + str(len(re.findall(r", [a-z]+ing ", p))))
    out.append("passive (be + -ed): " + str(len(re.findall(r"\b(?:is|are|was|were|be|been|being) [a-z]+ed\b", p))))
    return out


def check_rhythm():
    out = []
    for name, sec in sections():
        pr = prose_of(sec)
        ss = sentences(pr)
        if not ss:
            continue
        lens = [len(s.split()) for s in ss]
        paras = [p for p in re.split(r"\n\s*\n", pr) if p.strip()]
        plens = [len(sentences(p)) for p in paras]
        runs = sum(1 for i in range(2, len(lens)) if max(lens[i-2:i+1]) - min(lens[i-2:i+1]) <= 3)
        out.append("%-32s sents=%3d min=%2d max=%2d <8=%d >40=%d paras=%d sent/para=%s flat-runs=%d" % (
            name[:32], len(lens), min(lens), max(lens), sum(l < 8 for l in lens),
            sum(l > 40 for l in lens), len(paras), plens, runs))
    return out


def check_terms():
    p = prose()
    out = []
    groups = [["generation", "hop", "step"],
              ["hedge density", "hedging density", "hedge rate"],
              ["numeric fidelity", "numeric retention", "numeric share"],
              ["core finding", "core-finding"],
              ["Qwen2.5-7B-Instruct", "Qwen2.5-7B", "Qwen"],
              ["Phi-3.5-mini-instruct", "Phi-3.5-mini", "Phi"],
              ["Mistral-7B-Instruct-v0.3", "Mistral-7B", "Mistral"],
              ["preregistered", "pre-registered", "preregistration"],
              ["front-loaded", "front loaded", "front-loading"],
              ["per 100 words", "per hundred words"],
              ["summarization", "summarisation"],
              ["anonymized", "anonymised"]]
    for group in groups:
        counts = {g: len(re.findall(r"\b" + re.escape(g) + r"\b", p)) for g in group}
        out.append(str(counts))
    return out


def check_acronyms():
    p = prose()
    out = []
    for ac in ["NLI", "OLS", "LLM", "CI", "RCT", "AI", "NF4", "T4", "JSONL", "CPU", "GPU"]:
        first = re.search(r"\b" + ac + r"\b", p)
        if first:
            window = p[max(0, first.start() - 120):first.end() + 60]
            out.append(ac + ": first use ..." + window.strip()[:170].replace("\n", " ") + "...")
    return out


def check_abstract():
    ab = prose_of(TEX.split(r"\begin{abstract}")[1].split(r"\end{abstract}")[0])
    ss = sentences(ab)
    nums = re.findall(r"NUM|\d+%", ab)
    return ["words=%d sentences=%d numbers=%d" % (len(ab.split()), len(ss), len(nums)),
            "first: " + ss[0][:90], "last: " + ss[-1][:90],
            "lengths: " + str([len(s.split()) for s in ss])]


def check_figures():
    out = []
    for f in re.findall(r"\\includegraphics\[[^\]]*\]\{([^}]*)\}", TEX):
        if not (HERE / f).exists():
            out.append("missing figure file " + f)
    for m in re.finditer(r"\\caption\{((?:[^{}]|\{[^{}]*\})*)\}", TEX):
        cap = m.group(1)
        out.append("caption %d words: %s..." % (len(cap.split()), cap[:70]))
    return out


def check_headings():
    out = []
    for h in re.findall(r"\\(?:sub)?section\*?\{([^}]*)\}", TEX):
        words = h.split()
        caps = [w for w in words[1:] if w[0].isupper() and w not in ("H1", "H2", "H3")]
        if caps:
            out.append("title-case words in heading: " + h)
    return out


def check_wordcounts():
    out = ["TOTAL prose words: %d" % len(prose().split())]
    for name, sec in sections():
        out.append("%-40s %5d words" % (name[:40], len(prose_of(sec).split())))
    return out


def check_firstperson():
    out = []
    for name, sec in sections():
        p = prose_of(sec)
        n = len(p.split()) or 1
        we = len(re.findall(r"\b(?:we|our|us)\b", p, re.I))
        out.append("%-40s we/our per 100 words = %.1f" % (name[:40], 100.0 * we / n))
    return out


def check_hedges():
    p = prose().lower()
    words = ["may", "might", "could", "seems", "appears", "likely", "suggest",
             "suggests", "plausibly", "roughly", "about", "approximately",
             "arguably", "perhaps", "possibly", "somewhat"]
    return [w + ": " + str(len(re.findall(r"\b" + w + r"\b", p))) for w in words
            if re.findall(r"\b" + w + r"\b", p)]


def check_claims():
    ab = TEX.split(r"\begin{abstract}")[1].split(r"\end{abstract}")[0]
    rest = TEX.split(r"\end{abstract}")[1].replace("{,}", "")
    out = []
    for n in set(re.findall(r"\d+(?:\.\d+)?", ab.replace("{,}", ""))):
        if n not in rest:
            out.append("abstract number %s not found outside abstract" % n)
    return out


CHECKS = {k[6:]: v for k, v in list(globals().items()) if k.startswith("check_")}

if __name__ == "__main__":
    names = sys.argv[1:] or list(CHECKS)
    for n in names:
        print("=== " + n + " ===")
        res = CHECKS[n]()
        if not res:
            print("(clean)")
        for line in res:
            print("  " + line)
