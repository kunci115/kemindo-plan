"""Quotation persistence. Right-sized: one JSON file per quote on disk +
in-memory index. No DB server. Swap to Postgres when volume demands it."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from .config import DATA_DIR

QUOTE_DIR = DATA_DIR / "quotations"
QUOTE_DIR.mkdir(parents=True, exist_ok=True)


def save_quotation(quote: dict[str, Any]) -> dict[str, Any]:
    quote.setdefault("status", "DRAFT")
    path = QUOTE_DIR / f"{quote['quotation_no']}.json"
    path.write_text(json.dumps(quote, ensure_ascii=False, indent=2), encoding="utf-8")
    return quote


def get_quotation(no: str) -> dict[str, Any] | None:
    path = QUOTE_DIR / f"{no}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_quotations() -> list[dict[str, Any]]:
    out = []
    for p in sorted(QUOTE_DIR.glob("QT-*.json"), reverse=True):
        q = json.loads(p.read_text(encoding="utf-8"))
        out.append({
            "quotation_no": q["quotation_no"], "date": q.get("date"),
            "customer": q.get("customer"), "subtotal_idr": q.get("subtotal_idr"),
            "status": q.get("status"), "approval_required": q.get("approval_required"),
        })
    return out
