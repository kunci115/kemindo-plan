"""Pricing + decision engine. DETERMINISTIC — LLM never sets price.

'LLM proposes, rules dispose.' The agent may suggest a discount; this engine
enforces floor margin, applies volume/payment tiers, and returns the required
approval level. Also a light win/loss-aware price hint from rfq_history.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any
from ..data_store import get_store


@dataclass
class PriceDecision:
    product_id: str
    name: str
    unit: str
    qty: float
    list_price: float
    discount_pct: float
    unit_price: float
    line_total: float
    cost: float
    margin_pct: float
    floor_price: float
    below_floor: bool
    approval_required: str | None
    flags: list[str]

    def dict(self) -> dict[str, Any]:
        return asdict(self)


def _volume_discount(qty: float, typical: float, tiers: list[dict]) -> float:
    if typical <= 0:
        return 0.0
    ratio = qty / typical
    disc = 0.0
    for t in sorted(tiers, key=lambda x: x["min_qty_ratio_vs_typical"]):
        if ratio >= t["min_qty_ratio_vs_typical"]:
            disc = t["discount_pct"]
    return disc


def quote_line(product_id: str, qty: float, requested_discount_pct: float = 0.0,
               payment_term: str = "NET30", typical_qty: float | None = None) -> PriceDecision:
    store = get_store()
    price = store.price_by_id[product_id]
    prod = store.product_by_id[product_id]
    rules = store.margin_rules

    list_price = price["list_price_idr"]
    cost = price["cost_idr"]
    floor = price["floor_price_idr"]

    # auto volume discount, take the larger of requested vs earned
    typ = typical_qty or (50 if prod["unit"] == "MT" else (4000 if prod["unit"] == "L" else 20000))
    vol_disc = _volume_discount(qty, typ, rules["volume_discount_tiers"])
    disc = max(requested_discount_pct, vol_disc)

    # payment-term margin adjustment (cost-of-capital proxy)
    term_adj = rules["payment_term_adjust"].get(payment_term, 0.0)

    unit_price = list_price * (1 - disc)
    eff_cost = cost * (1 + term_adj)
    margin = 1 - (eff_cost / unit_price) if unit_price else -1.0
    line_total = round(unit_price * qty)

    flags: list[str] = []
    below_floor = unit_price < floor
    if below_floor:
        flags.append(f"Unit price below floor (Rp{floor:,.0f}).")
    if vol_disc > requested_discount_pct:
        flags.append(f"Auto volume discount {vol_disc:.0%} applied (qty {qty:g} vs typical {typ:g}).")

    approval = _approval(margin, disc, line_total, rules)
    if approval:
        flags.append(f"Approval required: {approval}.")

    return PriceDecision(
        product_id=product_id, name=prod["name"], unit=prod["unit"], qty=qty,
        list_price=list_price, discount_pct=round(disc, 4),
        unit_price=round(unit_price), line_total=line_total, cost=cost,
        margin_pct=round(margin, 4), floor_price=floor, below_floor=below_floor,
        approval_required=approval, flags=flags,
    )


def _approval(margin: float, discount: float, order_value: float, rules: dict) -> str | None:
    level = None
    order = ["Sales Manager", "Commercial Director"]
    for t in rules["approval_thresholds"]:
        hit = (
            ("if_margin_below_pct" in t and margin < t["if_margin_below_pct"]) or
            ("if_discount_above_pct" in t and discount > t["if_discount_above_pct"]) or
            ("if_order_value_above_idr" in t and order_value > t["if_order_value_above_idr"])
        )
        if hit:
            cand = t["approval"]
            if level is None or order.index(cand) > order.index(level):
                level = cand
    return level


def win_loss_hint(product_id: str) -> dict[str, Any]:
    """Light pricing intelligence: historical win/loss for this product +
    average realized margin on WON deals. Guides 'win but keep margin'."""
    store = get_store()
    won_margins, lost = [], 0
    for r in store.rfqs:
        for it in r["items"]:
            if it["product_id"] == product_id:
                if r["status"] == "WON":
                    won_margins.append(it["realized_margin_pct"])
                elif r["status"] == "LOST":
                    lost += 1
    avg_won = round(sum(won_margins) / len(won_margins), 3) if won_margins else None
    return {
        "product_id": product_id,
        "won_deals": len(won_margins),
        "lost_deals": lost,
        "avg_won_margin_pct": avg_won,
        "hint": (f"Historically won at ~{avg_won:.0%} margin; price near this to "
                 f"stay competitive while protecting margin." if avg_won
                 else "No win history — price at target margin, watch competitor."),
    }
