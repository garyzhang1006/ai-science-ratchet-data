"""Entailment instrument.

Bidirectional NLI between source abstract and generation with a public
cross-encoder (default cross-encoder/nli-deberta-v3-base), plus a
core-finding check: is the source's strongest claim sentence still entailed
by the generation? Label indices are read from model config, never
hardcoded. Runs on cuda, mps, or cpu.
"""
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

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

    def bidirectional(self, source: str, gen: str):
        """Forward: source premise -> gen hypothesis (unsupported additions
        when low). Backward: gen premise -> source hypothesis (dropped
        content when low)."""
        (fwd_e, fwd_c), (bwd_e, bwd_c) = self.entail_probs(
            [(source, gen), (gen, source)])
        return {"fwd_entail": fwd_e, "fwd_contra": fwd_c,
                "bwd_entail": bwd_e, "bwd_contra": bwd_c,
                "bi_entail": min(fwd_e, bwd_e)}

    def core_survival(self, gen: str, core_sentence: str) -> float:
        """P(generation entails the source core-finding sentence)."""
        if not core_sentence.strip():
            return float("nan")
        (e, _), = self.entail_probs([(gen, core_sentence)])
        return e
