"""LangChain tools exposed to the DeepSeek agent. Each wraps a DETERMINISTIC
engine so the LLM orchestrates but never fabricates numbers, prices, or dosages.
"""
from __future__ import annotations
import json
from typing import Any
from langchain_core.tools import tool
from ..retrieval.hybrid import get_corpus
from ..data_store import get_store
from ..reasoning import chemistry, compatibility, pricing
from ..quotation import build_quotation as _build_quote


@tool
def search_product(query: str) -> str:
    """Find Kemindo products by need, problem, name, or industry. Returns top
    matches with id, name, application, and a citation. Use this to map an RFQ
    item or a customer problem to real catalog products."""
    hits = get_corpus().search(query, kind="product", k=5)
    out = [{"id": h["payload"]["id"], "name": h["payload"]["name"],
            "category": h["payload"]["category"],
            "industries": h["payload"]["industries"],
            "application": h["payload"]["application"],
            "citation": h["citation"]} for h in hits]
    return json.dumps(out, ensure_ascii=False)


@tool
def knowledge_lookup(query: str) -> str:
    """Search the technical knowledge base (gold recovery, nickel, paper
    chemistry) for root-cause/application guidance. Returns text snippets WITH
    citations — always cite these in your answer."""
    hits = get_corpus().search(query, kind="knowledge", k=3)
    out = [{"heading": h["payload"]["heading"], "citation": h["citation"],
            "text": h["payload"]["text"][:900]} for h in hits]
    return json.dumps(out, ensure_ascii=False)


@tool
def calc_dosage(kind: str, value: float | None = None, target_ph: float = 11.0) -> str:
    """Compute a recommended dosage deterministically. kind must be one of:
    'lime_ph' (value=ore tons/day, target_ph), 'activated_carbon' (value=slurry m3),
    'hpal_acid' (value=ore tons/day), 'smbs_detox' (value=WAD CN kg/day)."""
    if kind not in chemistry.DOSAGE_FUNCS:
        return json.dumps({"error": f"unknown kind. options: {list(chemistry.DOSAGE_FUNCS)}"})
    fn = chemistry.DOSAGE_FUNCS[kind]
    res = fn(value, target_ph) if kind == "lime_ph" else fn(value)
    return json.dumps(res.dict(), ensure_ascii=False)


@tool
def stoichiometry(acid_kg: float, acid: str = "H2SO4", base: str = "Ca(OH)2") -> str:
    """Mass of base needed to neutralize a given mass of acid (molar-equivalent).
    acids: H2SO4, HCl. bases: Ca(OH)2, NaOH."""
    try:
        return json.dumps(chemistry.stoichiometry_neutralization(acid_kg, acid, base))
    except ValueError as e:
        return json.dumps({"error": str(e)})


@tool
def check_compatibility(product_ids: list[str]) -> str:
    """Check storage/segregation safety among products (by id). Flags
    incompatible pairs (oxidizer+flammable, acid+base, etc). Call before
    recommending products be shipped/stored together."""
    store = get_store()
    prods = [store.product_by_id[i] for i in product_ids if i in store.product_by_id]
    return json.dumps(compatibility.check_pairwise(prods), ensure_ascii=False)


@tool
def check_inventory(product_id: str) -> str:
    """Stock on hand per warehouse + total + lead time for a product id."""
    store = get_store()
    rows = store.stock_for(product_id)
    return json.dumps({"product_id": product_id,
                       "total_on_hand": store.total_stock(product_id),
                       "warehouses": rows}, ensure_ascii=False)


@tool
def price_quote_line(product_id: str, qty: float, discount_pct: float = 0.0,
                     payment_term: str = "NET30") -> str:
    """Price one line with margin guardrail. Returns unit price, margin, floor
    breach flag, and required approval level. The LLM may PROPOSE a discount but
    this engine enforces the rules."""
    try:
        return json.dumps(pricing.quote_line(product_id, qty, discount_pct, payment_term).dict())
    except KeyError:
        return json.dumps({"error": f"no price for {product_id}"})


@tool
def win_loss_hint(product_id: str) -> str:
    """Historical win/loss + avg won-margin for a product, to price competitively
    while protecting margin."""
    return json.dumps(pricing.win_loss_hint(product_id), ensure_ascii=False)


@tool
def build_quotation(customer_name: str, lines: list[dict], payment_term: str = "NET30",
                    incoterm: str = "EXW Warehouse") -> str:
    """Assemble a full quotation. lines = [{"product_id","qty","discount_pct"?}].
    Returns quotation object with subtotal + overall approval requirement."""
    return json.dumps(_build_quote(customer_name, lines, payment_term, incoterm),
                      ensure_ascii=False)


@tool
def capture_lead(company_name: str | None = None, contact: str | None = None,
                 industry: str | None = None, need: str | None = None,
                 products_of_interest: list[str] | None = None) -> str:
    """Capture a customer inquiry so a Kemindo sales specialist can follow up with
    pricing + a formal quotation. Call this once you have at least the customer's
    need and a way to reach them (company or contact)."""
    from ..store_leads import save_lead
    lead = save_lead(company_name, contact, industry, need, products_of_interest)
    return json.dumps({"lead_id": lead["id"], "status": "captured",
                       "message": "Inquiry forwarded to Kemindo sales team."}, ensure_ascii=False)


# internal staff tools (full) — pricing, margin, stock, quotation
ALL_TOOLS = [search_product, knowledge_lookup, calc_dosage, stoichiometry,
             check_compatibility, check_inventory, price_quote_line,
             win_loss_hint, build_quotation]

# external customer tools — NO price/margin/cost/internal-stock exposure
EXTERNAL_TOOLS = [search_product, knowledge_lookup, calc_dosage, stoichiometry,
                  check_compatibility, capture_lead]
