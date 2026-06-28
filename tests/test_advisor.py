"""TDD: external Solution Advisor support pieces — lead capture store, /leads
endpoint, and company-profile knowledge availability. No LLM/langchain needed."""
import os
os.environ.setdefault("ENABLE_DENSE_RETRIEVAL", "false")

from fastapi.testclient import TestClient
from app.api import app
from app.store_leads import save_lead, list_leads
from app.data_store import get_store

client = TestClient(app)


def test_lead_capture_persists():
    lead = save_lead("PT Vale Indonesia", "budi@vale.example", "Nickel",
                     "Need sulfuric acid for HPAL", ["Sulfuric Acid"])
    assert lead["id"].startswith("L-")
    assert lead["status"] == "NEW"
    assert any(l["id"] == lead["id"] for l in list_leads())
    # via API
    r = client.get("/leads")
    assert r.status_code == 200
    assert any(l["id"] == lead["id"] for l in r.json())


def test_company_profile_in_knowledge():
    chunks = get_store().knowledge
    blob = " ".join(c["text"] for c in chunks).lower()
    assert "your solution partner" in blob
    assert "logistics" in blob and "energy" in blob
    # advisor must be able to cite a company-profile source
    assert any("company_profile.md" in c["citation"] for c in chunks)
