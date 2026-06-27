"""TDD: RFQ -> natural-language prompt composer (auto-chain). Pure, no LLM."""
import os
os.environ.setdefault("ENABLE_DENSE_RETRIEVAL", "false")

from app.ingest.rfq_parser import compose_rfq_prompt


def test_compose_prompt_embeds_customer_terms_and_items():
    rfq = {
        "customer_name": "PT Bumi Suksesindo",
        "delivery_location": "Banyuwangi port",
        "incoterm": "CIF",
        "payment_term": "NET30",
        "items": [
            {"product_guess": "Hydrated Lime", "quantity": 200, "unit": "MT", "spec_notes": "min 90%"},
            {"product_guess": "Activated Carbon", "quantity": 40, "unit": "MT", "spec_notes": "iodine >= 1000"},
        ],
    }
    p = compose_rfq_prompt(rfq)
    assert "quotation" in p.lower()
    assert "PT Bumi Suksesindo" in p
    assert "CIF" in p and "NET30" in p
    assert "Hydrated Lime" in p and "200 MT" in p
    assert "Activated Carbon" in p
    # ordered, numbered
    assert "1." in p and "2." in p


def test_compose_prompt_handles_empty():
    p = compose_rfq_prompt({"items": []})
    assert "no items extracted" in p.lower()
    assert "quotation" in p.lower()
