"""Entailment instrument.

Bidirectional NLI between source abstract and generation with a public
cross-encoder (default cross-encoder/nli-deberta-v3-base), plus a
core-finding check: is the source's strongest claim sentence still entailed
by the generation? Label indices are read from model config, never
hardcoded. Runs on cuda, mps, or cpu.

Aggregation is SummaC-style and granular rather than whole-document. A
sentence-pair NLI model is trained on single-sentence premises, so feeding
it a 300-token abstract makes it report "not entailed" even for a claim
copied verbatim out of that abstract; scoring each hypothesis sentence
against every premise sentence and keeping the best-supporting one fixes
that. `validate_self_entailment` checks the property directly: a text must
entail its own sentences.
"""
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from .causal import split_sentences

DEFAULT_MODEL = "cross-encoder/nli-deberta-v3-base"


class EntailmentScorer:
    def __init__(self, model_name: str = DEFAULT_MODEL, device: str = None,
                 batch_size: int = 16, max_length: int = 512):
        if device is None:
            device = ("cuda" if torch.cuda.is_available()
                      else "mps" if torch.backends.mps.is_available()
                      else "cpu")
        self.device = device
        self.batch_size = batch_size
        self.max_length = max_length
        self.tok = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_name).to(device)
        self.model.train(False)  # inference mode
        id2label = {int(k): v.lower() for k, v in
                    self.model.config.id2label.items()}
        self.ent_idx = next(i for i, l in id2label.items() if "entail" in l)
        self.con_idx = next(i for i, l in id2label.items() if "contradict" in l)

    @torch.no_grad()
    def entail_probs(self, pairs):
        """pairs: list of (premise, hypothesis). Returns list of
        (p_entail, p_contradict)."""
        out = []
        for i in range(0, len(pairs), self.batch_size):
            batch = pairs[i:i + self.batch_size]
            enc = self.tok(
                [p for p, _ in batch], [h for _, h in batch],
                truncation=True, max_length=self.max_length,
                padding=True, return_tensors="pt",
            ).to(self.device)
            probs = torch.softmax(self.model(**enc).logits, dim=-1)
            for row in probs:
                out.append((row[self.ent_idx].item(),
                            row[self.con_idx].item()))
        return out

    def _granular(self, premise: str, hypothesis: str):
        """SummaC-style score: for each hypothesis sentence, the best
        entailment (and matching contradiction) over all premise sentences;
        the text-level score is the mean over hypothesis sentences."""
        prem = split_sentences(premise) or [premise]
        hyp = split_sentences(hypothesis) or [hypothesis]
        pairs = [(p, h) for h in hyp for p in prem]
        if not pairs:
            return float("nan"), float("nan")
        probs = self.entail_probs(pairs)
        n_p = len(prem)
        best_e, best_c = [], []
        for i in range(len(hyp)):
            block = probs[i * n_p:(i + 1) * n_p]
            j = max(range(len(block)), key=lambda k: block[k][0])
            best_e.append(block[j][0])
            best_c.append(max(c for _, c in block))
        return sum(best_e) / len(best_e), sum(best_c) / len(best_c)

    def bidirectional(self, source: str, gen: str):
        """Forward: is every claim in the generation supported by some
        sentence of the source? Low means unsupported additions. Backward:
        is every claim of the source still supported by the generation?
        Low means dropped content, so it falls for any summary and measures
        compression as much as infidelity."""
        fwd_e, fwd_c = self._granular(source, gen)
        bwd_e, bwd_c = self._granular(gen, source)
        return {"fwd_entail": fwd_e, "fwd_contra": fwd_c,
                "bwd_entail": bwd_e, "bwd_contra": bwd_c,
                "bi_entail": min(fwd_e, bwd_e)}

    def core_survival(self, gen: str, core_sentence: str) -> float:
        """Best support for the source's core-finding sentence anywhere in
        the generation."""
        if not core_sentence.strip():
            return float("nan")
        e, _ = self._granular(gen, core_sentence)
        return e

    def validate_self_entailment(self, texts):
        """Sanity check the instrument: a text must entail its own core
        sentence. Returns the mean self-entailment, which has to sit near
        1.0 for any downstream survival analysis to mean anything."""
        from .causal import core_claim_sentence
        scores = [self.core_survival(t, core_claim_sentence(t))
                  for t in texts]
        scores = [s for s in scores if s == s]  # drop NaN
        return sum(scores) / len(scores) if scores else float("nan")
