"""In-memory data store. Loads data/*.json once. Indexes for fast lookup.

Right-sized: corpus is tiny (~48 products), so dicts + brute-force beat a DB
server. Swap to Postgres/pgvector only when volume demands it.
"""
from __future__ import annotations
import json
from functools import lru_cache
from pathlib import Path
from typing import Any
from .config import DATA_DIR, KNOWLEDGE_DIR


def _load(name: str) -> dict[str, Any]:
    p = DATA_DIR / name
    with open(p, encoding="utf-8") as f:
        return json.load(f)


class Store:
    def __init__(self) -> None:
        self.products: list[dict] = _load("products.json")["products"]
        self.pricing: dict = _load("pricing.json")
        self.inventory: list[dict] = _load("inventory.json")["stock"]
        self.customers: list[dict] = _load("customers.json")["customers"]
        self.rfqs: list[dict] = _load("rfq_history.json")["rfqs"]

        # indexes
        self.product_by_id = {p["id"]: p for p in self.products}
        self.price_by_id = {x["product_id"]: x for x in self.pricing["price_list"]}
        self.margin_rules = self.pricing["margin_rules"]
        self.customer_by_id = {c["id"]: c for c in self.customers}

        # inventory grouped by product
        self.inv_by_product: dict[str, list[dict]] = {}
        for row in self.inventory:
            self.inv_by_product.setdefault(row["product_id"], []).append(row)

        # knowledge docs (markdown, chunked by heading for citation)
        self.knowledge: list[dict] = self._load_knowledge()

    def _load_knowledge(self) -> list[dict]:
        chunks: list[dict] = []
        if not KNOWLEDGE_DIR.exists():
            return chunks
        for md in sorted(KNOWLEDGE_DIR.glob("*.md")):
            text = md.read_text(encoding="utf-8")
            # chunk on "## " headings, keep heading as anchor
            current_head = md.stem
            buf: list[str] = []
            line_no = 0
            start_line = 1
            for i, line in enumerate(text.splitlines(), 1):
                if line.startswith("## "):
                    if buf:
                        chunks.append(self._chunk(md.name, current_head, buf, start_line, i - 1))
                    current_head = line[3:].strip()
                    buf = [line]
                    start_line = i
                else:
                    buf.append(line)
                line_no = i
            if buf:
                chunks.append(self._chunk(md.name, current_head, buf, start_line, line_no))
        return chunks

    @staticmethod
    def _chunk(file: str, heading: str, lines: list[str], start: int, end: int) -> dict:
        return {
            "source": file,
            "heading": heading,
            "lines": f"{start}-{end}",
            "text": "\n".join(lines).strip(),
            "citation": f"{file}#{heading} (L{start}-{end})",
        }

    # ---- helpers used by tools ----
    def stock_for(self, product_id: str) -> list[dict]:
        return self.inv_by_product.get(product_id, [])

    def total_stock(self, product_id: str) -> float:
        return sum(r["qty_on_hand"] for r in self.stock_for(product_id))

    def won_lost_for(self, product_id: str) -> dict[str, int]:
        won = lost = 0
        for r in self.rfqs:
            if any(it["product_id"] == product_id for it in r["items"]):
                if r["status"] == "WON":
                    won += 1
                elif r["status"] == "LOST":
                    lost += 1
        return {"won": won, "lost": lost}


@lru_cache
def get_store() -> Store:
    return Store()
