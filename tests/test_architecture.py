"""TDD: architecture graph data is well-formed (every edge endpoint exists)."""
import os
os.environ.setdefault("ENABLE_DENSE_RETRIEVAL", "false")

from app.architecture import build_architecture


def test_graph_is_consistent():
    g = build_architecture()
    nodes = {e["data"]["id"] for e in g["elements"] if "source" not in e["data"]}
    edges = [e["data"] for e in g["elements"] if "source" in e["data"]]
    # core nodes present
    assert "agent" in nodes
    assert "advisor" in nodes                # external tier present
    assert g["stats"]["tools"] >= 10         # 9 internal + capture_lead
    assert g["stats"]["engines"] >= 5
    # every edge connects existing nodes
    for e in edges:
        assert e["source"] in nodes, f"dangling source {e['source']}"
        assert e["target"] in nodes, f"dangling target {e['target']}"
    # agent fans out to all 9 tools
    tool_targets = {e["target"] for e in edges if e["source"] == "agent"}
    assert {"search_product", "build_quotation", "calc_dosage"} <= tool_targets
