"""Conversation persistence so chat history survives refresh. One JSON file per
conversation + in-memory listing. Right-sized; swap to Postgres + per-user
scoping when multi-user lands (see proposal future work)."""
from __future__ import annotations
import json
import uuid
import datetime
from typing import Any
from .config import DATA_DIR

CONV_DIR = DATA_DIR / "conversations"
CONV_DIR.mkdir(parents=True, exist_ok=True)


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def _path(cid: str):
    return CONV_DIR / f"{cid}.json"


def new_conversation(owner: str = "sales") -> dict[str, Any]:
    cid = "C-" + uuid.uuid4().hex[:8]
    conv = {"id": cid, "title": "New conversation", "owner": owner,
            "created": _now(), "updated": _now(), "messages": []}
    _path(cid).write_text(json.dumps(conv, ensure_ascii=False, indent=2), encoding="utf-8")
    return conv


def get_conversation(cid: str) -> dict[str, Any] | None:
    p = _path(cid)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def append_message(cid: str, role: str, content: str,
                   trace: list | None = None) -> dict[str, Any] | None:
    conv = get_conversation(cid)
    if conv is None:
        return None
    msg: dict[str, Any] = {"role": role, "content": content, "ts": _now()}
    if trace:
        msg["trace"] = trace
    conv["messages"].append(msg)
    conv["updated"] = _now()
    # title from first user message
    if conv["title"] == "New conversation" and role == "user":
        conv["title"] = (content[:48] + "…") if len(content) > 48 else content
    _path(cid).write_text(json.dumps(conv, ensure_ascii=False, indent=2), encoding="utf-8")
    return conv


def list_conversations(owner: str | None = None) -> list[dict[str, Any]]:
    out = []
    for p in CONV_DIR.glob("C-*.json"):
        c = json.loads(p.read_text(encoding="utf-8"))
        if owner and c.get("owner") != owner:
            continue
        out.append({"id": c["id"], "title": c["title"], "updated": c["updated"],
                    "messages": len(c["messages"])})
    return sorted(out, key=lambda x: x["updated"], reverse=True)


def delete_conversation(cid: str) -> bool:
    p = _path(cid)
    if p.exists():
        p.unlink()
        return True
    return False
