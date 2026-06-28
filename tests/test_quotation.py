"""TDD: quotation build/persist + PDF rendering. No LLM needed."""
import os
os.environ.setdefault("ENABLE_DENSE_RETRIEVAL", "false")

from app.quotation import build_quotation, render_quotation_pdf
from app.store_quotations import get_quotation, list_quotations


def test_build_persists_and_indexes():
    q = build_quotation("PT Vale Indonesia",
                        [{"product_id": "P008", "qty": 50}],
                        payment_term="NET60")
    assert q["quotation_no"].startswith("QT-")
    assert q["status"] == "DRAFT"
    assert q["customer"] == "PT Vale Indonesia"
    assert q["subtotal_idr"] > 0
    assert len(q["lines"]) == 1
    # persisted + retrievable
    again = get_quotation(q["quotation_no"])
    assert again is not None
    assert again["subtotal_idr"] == q["subtotal_idr"]
    # appears in list
    assert any(s["quotation_no"] == q["quotation_no"] for s in list_quotations())


def test_margin_guard_flags_approval():
    # heavy discount pushes below floor -> approval required
    q = build_quotation("PT Test",
                        [{"product_id": "P008", "qty": 50, "discount_pct": 0.5}])
    line = q["lines"][0]
    assert line["below_floor"] is True
    assert q["approval_required"] is not None


def test_unit_conversion_mt_to_kg():
    # P008 is priced per kg; "50 MT" must become 50,000 kg, not 50 kg (1000x bug)
    q_kg = build_quotation("PT A", [{"product_id": "P008", "qty": 50, "unit": "kg"}])
    q_mt = build_quotation("PT B", [{"product_id": "P008", "qty": 50, "unit": "MT"}])
    assert q_mt["lines"][0]["qty"] == 50000
    assert q_mt["subtotal_idr"] == q_kg["subtotal_idr"] * 1000
    # canonical summary present for the agent to echo verbatim
    assert "Subtotal" in q_mt["summary_markdown"]


def test_pdf_is_valid_bytes():
    q = build_quotation("PT Agincourt Resources",
                        [{"product_id": "P001", "qty": 20},
                         {"product_id": "P003", "qty": 5}])
    pdf = render_quotation_pdf(q)
    assert isinstance(pdf, (bytes, bytearray))
    assert pdf[:4] == b"%PDF"          # valid PDF magic header
    assert len(pdf) > 1500             # has real content
