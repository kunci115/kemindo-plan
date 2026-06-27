"""FastAPI app. Monolith — one service, one deploy. Serves the demo UI + API."""
from __future__ import annotations
import json
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from .config import get_settings
from .data_store import get_store

app = FastAPI(title="Kemindo Sales Engineer Copilot", version="2.0.0")
WEB = Path(__file__).parent / "web"
ASSETS = WEB / "assets"
if ASSETS.exists():
    app.mount("/assets", StaticFiles(directory=str(ASSETS)), name="assets")


class ChatIn(BaseModel):
    message: str
    session_id: str | None = None


class QuoteLine(BaseModel):
    product_id: str
    qty: float
    discount_pct: float = 0.0


class QuoteIn(BaseModel):
    customer_name: str
    lines: list[QuoteLine]
    payment_term: str = "NET30"
    incoterm: str = "EXW Warehouse"


@app.get("/health")
def health():
    s = get_settings()
    store = get_store()
    return {"ok": True, "llm_configured": s.has_llm, "dense_retrieval": s.enable_dense,
            "ocr": s.enable_ocr, "products": len(store.products),
            "knowledge_chunks": len(store.knowledge)}


@app.get("/", response_class=HTMLResponse)
def index():
    f = WEB / "index.html"
    return f.read_text(encoding="utf-8") if f.exists() else "<h1>UI missing</h1>"


@app.get("/graph", response_class=HTMLResponse)
def graph_page():
    f = WEB / "graph.html"
    return f.read_text(encoding="utf-8") if f.exists() else "<h1>graph UI missing</h1>"


@app.get("/architecture")
def architecture():
    from .architecture import build_architecture
    return build_architecture()


@app.post("/chat")
def chat(body: ChatIn):
    from .agent.graph import run
    return run(body.message)


@app.post("/chat/stream")
def chat_stream(body: ChatIn):
    from .agent.graph import stream
    from .store_conversations import new_conversation, append_message, get_conversation

    sid = body.session_id
    if not sid or get_conversation(sid) is None:
        sid = new_conversation()["id"]
    append_message(sid, "user", body.message)
    conv = get_conversation(sid)
    history = conv["messages"] if conv else [{"role": "user", "content": body.message}]

    def gen():
        yield f"data: {json.dumps({'type': 'session', 'session_id': sid})}\n\n"
        answer, trace = "", []
        for ev in stream(history):
            if ev.get("type") == "assistant":
                answer = ev.get("content", "")
            elif ev.get("type") in ("tool_call", "tool_result"):
                trace.append(ev)
            yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
        append_message(sid, "assistant", answer, trace)
        yield f"data: {json.dumps({'type': 'done', 'session_id': sid})}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


# ---------------- conversations (history) ----------------
@app.get("/conversations")
def conversations():
    from .store_conversations import list_conversations
    return list_conversations()


@app.post("/conversations")
def create_conversation():
    from .store_conversations import new_conversation
    return new_conversation()


@app.get("/conversation/{cid}")
def conversation(cid: str):
    from .store_conversations import get_conversation
    c = get_conversation(cid)
    if not c:
        raise HTTPException(404, f"conversation {cid} not found")
    return c


@app.delete("/conversation/{cid}")
def remove_conversation(cid: str):
    from .store_conversations import delete_conversation
    if not delete_conversation(cid):
        raise HTTPException(404, f"conversation {cid} not found")
    return {"deleted": cid}


@app.post("/ingest")
async def ingest(file: UploadFile = File(...)):
    from .ingest.rfq_parser import ingest_file
    blob = await file.read()
    return JSONResponse(ingest_file(file.filename, blob))


# ---------------- quotations ----------------
@app.post("/quotation")
def create_quotation(body: QuoteIn):
    from .quotation import build_quotation
    lines = [ln.model_dump() for ln in body.lines]
    return build_quotation(body.customer_name, lines, body.payment_term, body.incoterm)


@app.get("/quotations")
def quotations():
    from .store_quotations import list_quotations
    return list_quotations()


@app.get("/quotation/{no}")
def quotation(no: str):
    from .store_quotations import get_quotation
    q = get_quotation(no)
    if not q:
        raise HTTPException(404, f"quotation {no} not found")
    return q


@app.get("/quotation/{no}/pdf")
def quotation_pdf(no: str):
    from .store_quotations import get_quotation
    from .quotation import render_quotation_pdf
    q = get_quotation(no)
    if not q:
        raise HTTPException(404, f"quotation {no} not found")
    pdf = render_quotation_pdf(q)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{no}.pdf"'})
