"""TDD: conversation persistence (history survives) via store + API. No LLM."""
import os
os.environ.setdefault("ENABLE_DENSE_RETRIEVAL", "false")

from fastapi.testclient import TestClient
from app.api import app
from app.store_conversations import append_message, get_conversation

client = TestClient(app)


def test_conversation_crud_and_persistence():
    # create
    r = client.post("/conversations")
    assert r.status_code == 200
    cid = r.json()["id"]
    assert cid.startswith("C-")

    # append messages (simulates a chat turn) -> persists + titles
    append_message(cid, "user", "Quote 50 MT sulfuric acid for HPAL nickel")
    append_message(cid, "assistant", "Here is your quotation…", trace=[{"type": "tool_call", "tool": "build_quotation"}])

    # fetch back: messages survive
    r2 = client.get(f"/conversation/{cid}")
    assert r2.status_code == 200
    c = r2.json()
    assert len(c["messages"]) == 2
    assert c["title"].startswith("Quote 50 MT")          # title from first user msg
    assert c["messages"][1]["trace"][0]["tool"] == "build_quotation"

    # appears in list
    assert any(s["id"] == cid for s in client.get("/conversations").json())

    # delete
    assert client.delete(f"/conversation/{cid}").status_code == 200
    assert client.get(f"/conversation/{cid}").status_code == 404


def test_unknown_conversation_404():
    assert client.get("/conversation/C-nope").status_code == 404
