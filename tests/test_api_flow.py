"""TDD: full quotation user-flow through the HTTP API (no LLM).
build -> fetch json -> download PDF -> list -> 404 path."""
import os
os.environ.setdefault("ENABLE_DENSE_RETRIEVAL", "false")

from fastapi.testclient import TestClient
from app.api import app

client = TestClient(app)


def test_quotation_user_flow():
    # 1. build a quotation
    r = client.post("/quotation", json={
        "customer_name": "PT Vale Indonesia",
        "lines": [{"product_id": "P008", "qty": 50},
                  {"product_id": "P019", "qty": 10}],
        "payment_term": "NET60",
    })
    assert r.status_code == 200
    q = r.json()
    no = q["quotation_no"]
    assert no.startswith("QT-")
    assert q["status"] == "DRAFT"
    assert len(q["lines"]) == 2

    # 2. fetch it back as json
    r2 = client.get(f"/quotation/{no}")
    assert r2.status_code == 200
    assert r2.json()["subtotal_idr"] == q["subtotal_idr"]

    # 3. download the PDF
    r3 = client.get(f"/quotation/{no}/pdf")
    assert r3.status_code == 200
    assert r3.headers["content-type"] == "application/pdf"
    assert r3.content[:4] == b"%PDF"

    # 4. it appears in the list
    r4 = client.get("/quotations")
    assert r4.status_code == 200
    assert any(s["quotation_no"] == no for s in r4.json())


def test_unknown_quotation_404():
    assert client.get("/quotation/QT-DOESNOTEXIST").status_code == 404
    assert client.get("/quotation/QT-DOESNOTEXIST/pdf").status_code == 404
