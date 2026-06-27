<div align="center">

# Kemindo Sales Engineer Copilot

**Turn a customer problem or a messy RFQ into a technically-grounded, margin-guarded, downloadable quotation — with cited reasoning.**

`DeepSeek` · `LangGraph` · `FastAPI` · deterministic chemical & pricing engines · local hybrid retrieval

</div>

---

## The problem it solves

Kemindo sells industrial chemicals for **gold mining, nickel, paper, agriculture**. Customers don't buy products — they buy solutions to operational problems ("gold recovery dropped", "paper brightness down", "need HPAL reagents"). Today a sales engineer answering an RFQ has to: diagnose the problem, find the right products, recall dosages, check stock, price it, protect margin, write a quote. That takes **hours to days** and leans on a few senior people.

This copilot does it in **minutes** — and increases revenue on four levers:

| Lever | How |
|---|---|
| **Faster quotes** | Industrial deals are won on response speed → higher win rate |
| **Cross-sell** | Knowledge base maps problems → complementary products (lime buyer also needs carbon, SMBS, flocculant) |
| **Margin protection** | Deterministic decision engine blocks under-floor pricing, routes approvals |
| **Technical differentiation** | Recommendation + dosage → sell solutions, not price → defend margin |

> Business case: [proposal_v2.md](proposal_v2.md) · Roadmap: [FUTURE_DEVELOPMENT.md](FUTURE_DEVELOPMENT.md)

---

## What makes it strong (the engineering)

| Capability | What it does |
|---|---|
| **Multimodal RFQ ingest** | PDF / Excel / CSV / image(OCR) → structured RFQ, then **auto-runs** into the agent (no retyping) |
| **Chemical reasoning engine** | Dosage (pH→lime, HPAL acid, SMBS detox), stoichiometry, unit conversion — **deterministic**, never hallucinated |
| **Compatibility / safety check** | Hazard-class segregation (oxidizer+flammable, acid+base…) before co-storage |
| **Hybrid retrieval + citations** | BM25 + dense + reranker (RRF) — every product, dosage, and fact is **cited to its source** |
| **Margin decision engine** | Floor margin, volume/payment tiers, approval routing — *LLM proposes, rules dispose* |
| **Quotation + PDF** | Persisted, numbered quote → **branded PDF** (Kemindo letterhead) one click away |
| **Conversation memory** | Remembers the quote/customer across turns ("draft an email for this quote" just works) |
| **Architecture graph** | Interactive system map at **`/graph`** for presentations |
| **Eval harness + CI** | Golden set: retrieval + engines (deterministic gate) + LLM-judged answers. **Measured, not vibes** |

**Deliberately small infra:** one FastAPI service, file-backed stores, brute-force vectors over a tiny corpus. No Kubernetes, no Kafka. The intelligence lives in the AI/algorithm layer — added only what earns its place.

---

## Run it

```bash
cp .env.example .env        # put your DEEPSEEK_API_KEY in .env
docker compose up -d --build
# open http://127.0.0.1:8000     (architecture map: http://127.0.0.1:8000/graph)
```

Health check: `curl http://127.0.0.1:8000/health`

---

## Demo flows (for the presentation)

**1 — Technical consult → quote**
> `Quote 50 MT sulfuric acid for HPAL nickel, NET60`
Watches the agent (right "audit" panel) call tools → product match, dosage, inventory, margin check → quotation + **Download PDF**.

**2 — Conversation memory**
> Then click **"Draft a customer email for this quotation"** → it remembers the quote and writes the email. No re-asking.

**3 — Upload an RFQ (auto-chain)**
> 📎 upload `samples/sample_rfq.pdf` → it extracts 5 items, matches them, checks stock, runs a compatibility check, and builds one quotation — automatically.

**4 — Audit trail**
> Every number in the answer traces to a tool call in the right panel → it's auditable, not a black box.

---

## Architecture

Interactive map: **`/graph`** (Cytoscape — click nodes, drag, zoom).

```
 Sales Engineer ──(NL or RFQ upload)──► Orchestrator Agent  (LangGraph ReAct · DeepSeek)
                                              │  tool calls + conversation memory
        ┌───────────────┬───────────────┬─────┴─────────┬────────────────┐
   search_product   calc_dosage    check_inventory  price_quote_line  build_quotation  (+4 more)
        │               │               │               │                │
   Hybrid Retrieval  Chemistry      data_store      Pricing/Decision   Quotation+PDF
   (BM25+dense+rerank)  Engine                         Engine
        └───────────────┴───────────────┴───────────────┴────────────────┘
                         data/*.json (real catalog + dummy internal) · knowledge/*.md
```

**Honest scope:** this is **one orchestrator agent + 9 tools**, not a multi-agent mesh. Future agents (procurement, logistics, executive, email) are shown **dashed** on `/graph` — planned, not built.

---

## Tech stack

- **LLM:** DeepSeek (`deepseek-chat` tools + `deepseek-reasoner`), OpenAI-compatible
- **Agent:** LangGraph ReAct + tool calling
- **Retrieval:** `rank-bm25` + `bge` embeddings/reranker (local); RRF fusion
- **Backend:** FastAPI (monolith) · **PDF:** reportlab · **Ingest:** pdfplumber / pandas / Tesseract
- **Storage:** JSON files (right-sized) → Postgres/pgvector when volume demands
- **Deploy:** Docker Compose, single image

---

## Tests & eval

```bash
pytest tests/ -q                    # 10/10 — quotation, API flow, conversations, ingest, architecture
python -m eval.run_eval --no-llm    # deterministic gate: retrieval 8/8 + engines 5/5
python -m eval.run_eval             # + LLM-judged answer quality (needs API key)
```

CI runs the deterministic gate + unit tests on every push ([.github/workflows/eval.yml](.github/workflows/eval.yml)).

---

## Repo layout

```
app/
  api.py              FastAPI + SSE streaming + endpoints
  agent/              tools.py (9 tools) + graph.py (LangGraph ReAct, memory)
  reasoning/          chemistry · compatibility · pricing   (deterministic)
  retrieval/          hybrid.py (BM25 + dense + reranker, cited)
  ingest/             multimodal RFQ → structured (auto-chain)
  quotation.py        quote build + reportlab PDF
  store_*.py          conversations + quotations persistence
  architecture.py     /graph data
  web/                index.html (chat UI) + graph.html (architecture)
data/                 hybrid dataset (real catalog + dummy internal) + knowledge/  (see data/README.md)
eval/                 golden_set.json + run_eval.py
tests/                pytest suite
samples/              sample RFQ files for the upload demo
proposal_v2.md        business case   ·   FUTURE_DEVELOPMENT.md   roadmap
archive/              superseded v1 design docs
```

---

## Status

| Built & running | Planned (roadmap) |
|---|---|
| Agent + 9 tools, memory, citations | Multi-user auth + RBAC |
| Chemical / compatibility / pricing engines | Approval workflow (quote state machine) |
| Hybrid retrieval (BM25 active; dense pending a torch fix) | Email draft + SMTP send |
| Quotation persistence + branded PDF | ERP / CRM integration (replace dummy data) |
| Conversation history + enterprise UI | Procurement / logistics / executive agents |
| Multimodal ingest + auto-chain | |
| Architecture graph · eval harness · CI | |

> Dataset note: catalog names/brands are **real** (scraped from Kemindo sites); prices, stock, and RFQ history are **realistic dummy** — swap for ERP data before production. Details in [data/README.md](data/README.md).
