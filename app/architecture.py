"""Architecture graph data for the /graph visualization. Curated to match the
real codebase: one LangGraph ReAct orchestrator + deterministic tools/engines +
data. Future (planned) nodes are marked status=future so the diagram doubles as
a roadmap for presentations."""
from __future__ import annotations
from typing import Any

# layer -> display + color handled in the web page
NODES: list[dict[str, Any]] = [
    # entry
    {"id": "sales", "label": "Sales Engineer", "layer": "user",
     "desc": "Primary user. Asks in natural language or uploads an RFQ."},
    {"id": "ingest", "label": "Multimodal RFQ Ingest", "layer": "ingest",
     "desc": "PDF / Excel / CSV / image(OCR) -> text -> structured RFQ (DeepSeek). Auto-chains into the agent."},

    # orchestrator
    {"id": "agent", "label": "Orchestrator Agent\n(LangGraph ReAct · DeepSeek)", "layer": "agent",
     "desc": "Single ReAct agent. Plans, calls tools, cites sources. Conversation memory (last 12 turns). LLM never invents numbers."},

    # tools (real, from app/agent/tools.py)
    {"id": "search_product", "label": "search_product", "layer": "tool",
     "desc": "Map a problem/RFQ item to real catalog products. Cited."},
    {"id": "knowledge_lookup", "label": "knowledge_lookup", "layer": "tool",
     "desc": "Technical root-cause from the knowledge base. Cited."},
    {"id": "calc_dosage", "label": "calc_dosage", "layer": "tool",
     "desc": "Deterministic dosage (lime pH, HPAL acid, SMBS detox...)."},
    {"id": "stoichiometry", "label": "stoichiometry", "layer": "tool",
     "desc": "Acid/base neutralization mass balance."},
    {"id": "check_compatibility", "label": "check_compatibility", "layer": "tool",
     "desc": "Hazard segregation check before co-storage/shipping."},
    {"id": "check_inventory", "label": "check_inventory", "layer": "tool",
     "desc": "Stock per warehouse + lead time."},
    {"id": "price_quote_line", "label": "price_quote_line", "layer": "tool",
     "desc": "Price a line with margin floor + approval routing."},
    {"id": "win_loss_hint", "label": "win_loss_hint", "layer": "tool",
     "desc": "Historical win/loss margin to price competitively."},
    {"id": "build_quotation", "label": "build_quotation", "layer": "tool",
     "desc": "Assemble + persist quotation, return number + PDF link."},

    # engines (deterministic)
    {"id": "eng_chem", "label": "Chemistry Engine", "layer": "engine",
     "desc": "Dosage, stoichiometry, unit conversion. Deterministic."},
    {"id": "eng_compat", "label": "Compatibility Engine", "layer": "engine",
     "desc": "Hazard-class segregation matrix."},
    {"id": "eng_price", "label": "Pricing / Decision Engine", "layer": "engine",
     "desc": "Margin floor, volume/payment tiers, approval routing. LLM proposes, rules dispose."},
    {"id": "eng_retr", "label": "Hybrid Retrieval", "layer": "engine",
     "desc": "BM25 + dense(bge) + reranker, RRF fusion, citations."},
    {"id": "eng_quote", "label": "Quotation + PDF", "layer": "engine",
     "desc": "Builds quote object + reportlab PDF (Kemindo letterhead)."},

    # data
    {"id": "d_products", "label": "products.json", "layer": "data", "desc": "48 real catalog products."},
    {"id": "d_pricing", "label": "pricing.json", "layer": "data", "desc": "Prices + margin/approval rules."},
    {"id": "d_inventory", "label": "inventory.json", "layer": "data", "desc": "Stock per warehouse."},
    {"id": "d_rfq", "label": "rfq_history.json", "layer": "data", "desc": "Historical RFQ/quote win-loss."},
    {"id": "d_know", "label": "knowledge/*.md", "layer": "data", "desc": "Gold/nickel/paper handbooks (cited)."},
    {"id": "d_quotes", "label": "quotations store", "layer": "data", "desc": "Persisted quotes (DRAFT...)."},

    # external tier (Solution Advisor) — built
    {"id": "customer", "label": "Customer / Prospect", "layer": "user",
     "desc": "External user on the web. No access to pricing, margin, or internal stock."},
    {"id": "advisor", "label": "Solution Advisor\n(external · DeepSeek)", "layer": "agent",
     "desc": "Public customer-facing agent: product + technical guidance, company info, lead capture. Never exposes pricing/margin/stock."},
    {"id": "capture_lead", "label": "capture_lead", "layer": "tool",
     "desc": "Capture a customer inquiry -> routes to the sales team."},
    {"id": "d_leads", "label": "leads store", "layer": "data", "desc": "Captured customer inquiries."},
    {"id": "d_profile", "label": "company_profile.md", "layer": "data", "desc": "Public company-profile knowledge."},

    # future agents (roadmap) — dashed in UI
    {"id": "a_procure", "label": "Procurement Agent", "layer": "future", "status": "future",
     "desc": "Planned: supplier selection + negotiation."},
    {"id": "a_logistics", "label": "Logistics Agent", "layer": "future", "status": "future",
     "desc": "Planned: shipment + route optimization."},
    {"id": "a_exec", "label": "Executive Analytics Agent", "layer": "future", "status": "future",
     "desc": "Planned: KPI, forecasting, cross-sell intelligence."},
    {"id": "a_email", "label": "Email / Delivery", "layer": "future", "status": "future",
     "desc": "Planned: draft + SMTP send with PDF attached."},
]

EDGES: list[tuple[str, str]] = [
    ("sales", "agent"), ("sales", "ingest"), ("ingest", "agent"),
    # agent -> tools
    ("agent", "search_product"), ("agent", "knowledge_lookup"), ("agent", "calc_dosage"),
    ("agent", "stoichiometry"), ("agent", "check_compatibility"), ("agent", "check_inventory"),
    ("agent", "price_quote_line"), ("agent", "win_loss_hint"), ("agent", "build_quotation"),
    # tools -> engines
    ("search_product", "eng_retr"), ("knowledge_lookup", "eng_retr"),
    ("calc_dosage", "eng_chem"), ("stoichiometry", "eng_chem"),
    ("check_compatibility", "eng_compat"),
    ("price_quote_line", "eng_price"), ("win_loss_hint", "eng_price"),
    ("build_quotation", "eng_quote"), ("build_quotation", "eng_price"),
    # engines -> data
    ("eng_retr", "d_products"), ("eng_retr", "d_know"),
    ("eng_compat", "d_products"),
    ("eng_price", "d_pricing"), ("eng_price", "d_rfq"),
    ("check_inventory", "d_inventory"),
    ("eng_quote", "d_pricing"), ("eng_quote", "d_quotes"),
    # external Solution Advisor tier
    ("customer", "advisor"),
    ("advisor", "search_product"), ("advisor", "knowledge_lookup"),
    ("advisor", "calc_dosage"), ("advisor", "check_compatibility"), ("advisor", "capture_lead"),
    ("capture_lead", "d_leads"), ("knowledge_lookup", "d_profile"),
    ("d_leads", "agent"),   # captured leads feed the internal sales copilot
    # future (dashed)
    ("agent", "a_procure"), ("agent", "a_logistics"), ("agent", "a_exec"), ("agent", "a_email"),
]


def build_architecture() -> dict[str, Any]:
    elements = []
    for n in NODES:
        elements.append({"data": {"id": n["id"], "label": n["label"], "layer": n["layer"],
                                  "desc": n["desc"], "status": n.get("status", "built")}})
    for s, t in EDGES:
        future = any(x.get("id") in (s, t) and x.get("status") == "future" for x in NODES)
        elements.append({"data": {"id": f"{s}->{t}", "source": s, "target": t,
                                  "kind": "future" if future else "built"}})
    return {
        "elements": elements,
        "stats": {"tools": sum(1 for n in NODES if n["layer"] == "tool"),
                  "engines": sum(1 for n in NODES if n["layer"] == "engine"),
                  "data": sum(1 for n in NODES if n["layer"] == "data"),
                  "future": sum(1 for n in NODES if n.get("status") == "future")},
    }
