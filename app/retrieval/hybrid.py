"""Hybrid retrieval: BM25 (lexical) + dense (bge-small) fused by RRF, then
cross-encoder rerank (bge-reranker). Every hit carries a citation.

Degrades gracefully: if dense models are disabled/unavailable, falls back to
BM25-only (pure python, zero downloads). The agent's answers cite sources so
process engineers can verify against the actual datasheet/knowledge doc.
"""
from __future__ import annotations
import re
from functools import lru_cache
from typing import Any
from ..config import get_settings
from ..data_store import get_store

_TOKEN = re.compile(r"[a-z0-9]+")


def _tok(s: str) -> list[str]:
    return _TOKEN.findall(s.lower())


def _product_doc(p: dict) -> str:
    return (f"{p['name']} {p.get('sku_brand','')} {p.get('formula','')} "
            f"{p['category']} {' '.join(p['industries'])} {p['application']} "
            f"{p.get('specification','')}")


class Corpus:
    """Unified searchable corpus: products + knowledge chunks."""

    def __init__(self) -> None:
        store = get_store()
        self.docs: list[dict[str, Any]] = []
        for p in store.products:
            self.docs.append({
                "kind": "product", "id": p["id"], "title": p["name"],
                "text": _product_doc(p),
                "citation": f"products.json#{p['id']} ({p['name']})",
                "payload": p,
            })
        for k in store.knowledge:
            self.docs.append({
                "kind": "knowledge", "id": k["citation"], "title": k["heading"],
                "text": f"{k['heading']}\n{k['text']}",
                "citation": k["citation"], "payload": k,
            })
        self._tokenized = [_tok(d["text"]) for d in self.docs]
        self._bm25 = None
        self._emb = None  # lazy dense matrix

    # ---- lexical ----
    def bm25(self):
        if self._bm25 is None:
            from rank_bm25 import BM25Okapi
            self._bm25 = BM25Okapi(self._tokenized)
        return self._bm25

    # ---- dense (lazy) ----
    def embeddings(self):
        if self._emb is None:
            model = _embed_model()
            if model is None:
                return None
            self._emb = model.encode([d["text"] for d in self.docs],
                                     normalize_embeddings=True)
        return self._emb

    def search(self, query: str, kind: str | None = None, k: int = 5) -> list[dict]:
        scores_bm = self.bm25().get_scores(_tok(query))
        fused: dict[int, float] = {}
        # RRF over BM25 ranking
        for rank, idx in enumerate(sorted(range(len(scores_bm)),
                                          key=lambda i: scores_bm[i], reverse=True)):
            fused[idx] = fused.get(idx, 0.0) + 1.0 / (60 + rank)
        # RRF over dense ranking (if available)
        emb = self.embeddings() if get_settings().enable_dense else None
        if emb is not None:
            qv = _embed_model().encode([query], normalize_embeddings=True)[0]
            dense_scores = emb @ qv
            for rank, idx in enumerate(sorted(range(len(dense_scores)),
                                              key=lambda i: dense_scores[i], reverse=True)):
                fused[idx] = fused.get(idx, 0.0) + 1.0 / (60 + rank)

        ranked = sorted(fused.items(), key=lambda kv: kv[1], reverse=True)
        cands = [self.docs[i] for i, _ in ranked if kind is None or self.docs[i]["kind"] == kind]
        cands = cands[: max(k * 3, 12)]
        cands = self._rerank(query, cands, k)
        return cands

    def _rerank(self, query: str, cands: list[dict], k: int) -> list[dict]:
        ce = _rerank_model()
        if ce is None or not cands:
            return cands[:k]
        pairs = [(query, c["text"]) for c in cands]
        scores = ce.predict(pairs)
        order = sorted(range(len(cands)), key=lambda i: scores[i], reverse=True)
        out = []
        for i in order[:k]:
            d = dict(cands[i]); d["rerank_score"] = float(scores[i]); out.append(d)
        return out


@lru_cache
def _embed_model():
    if not get_settings().enable_dense:
        return None
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer(get_settings().embed_model)
    except Exception as e:  # offline / not installed -> BM25 only
        print(f"[retrieval] dense disabled ({e}); using BM25 only")
        return None


@lru_cache
def _rerank_model():
    if not get_settings().enable_dense:
        return None
    try:
        from sentence_transformers import CrossEncoder
        return CrossEncoder(get_settings().rerank_model)
    except Exception as e:
        print(f"[retrieval] reranker disabled ({e})")
        return None


@lru_cache
def get_corpus() -> Corpus:
    return Corpus()
