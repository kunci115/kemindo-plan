"""Lead capture store for the external Solution Advisor. Each customer inquiry is
saved so the sales team can follow up with a quotation (the internal Copilot).
File-backed; swap to CRM later."""
from __future__ import annotations
import json
import uuid
import datetime
from typing import Any
from .config import DATA_DIR

LEAD_DIR = DATA_DIR / "leads"
LEAD_DIR.mkdir(parents=True, exist_ok=True)


def save_lead(company: str | None, contact: str | None, industry: str | None,
              need: str | None, products: list[str] | None = None) -> dict[str, Any]:
    lid = "L-" + uuid.uuid4().hex[:8]
    lead = {
        "id": lid,
        "created": datetime.datetime.now().isoformat(timespec="seconds"),
        "company": company, "contact": contact, "industry": industry,
        "need": need, "products_of_interest": products or [],
        "status": "NEW",
    }
    (LEAD_DIR / f"{lid}.json").write_text(json.dumps(lead, ensure_ascii=False, indent=2),
                                          encoding="utf-8")
    return lead


def list_leads() -> list[dict[str, Any]]:
    out = []
    for p in sorted(LEAD_DIR.glob("L-*.json"), reverse=True):
        out.append(json.loads(p.read_text(encoding="utf-8")))
    return out
