<div align="center">

# Kemindo Industrial Intelligence Platform

**A two-tier AI for Kemindo Group — a public Solution Advisor that turns visitor problems into qualified leads, and an internal Sales Engineer Copilot that turns RFQs into technically-grounded, margin-guarded, downloadable quotations.**

`DeepSeek` · `LangGraph` · `FastAPI` · deterministic chemical & pricing engines · local hybrid retrieval

</div>

---

## Two products, one platform

| Tier | Who | Does | Sees pricing/margin? | URL |
|---|---|---|---|---|
| **Solution Advisor** (external) | Customers / prospects | Product + technical guidance, company profile, **captures the inquiry as a lead** | ❌ never | `/advisor` |
| **Sales Engineer Copilot** (internal) | Kemindo sales staff | RFQ → product match → dosage → stock → **margin-guarded quotation + PDF** | ✅ full | `/` |

**The funnel:** customer asks on the web → Advisor solves + captures a lead → sales engineer turns it into a quote → deal. One codebase, two agents, two faces.

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
| **Deterministic numbers** | Unit conversion (e.g. 50 MT → 50,000 kg), pricing, dosage all computed by engines; the agent presents a **canonical summary verbatim** — chat figures always equal the quote/PDF |
| **Bilingual ID/EN** | Replies in the user's language (or a forced toggle); retrieval always queries the English catalog with English keywords so matching stays accurate |
| **Grounded by construction** | Every product code comes from `search_product`, every price from a pricing tool, every quote/PDF from `build_quotation` — the agent may not name a product or quote a price from memory |
| **Quotation + PDF** | Persisted, numbered quote → **branded PDF** (Kemindo letterhead) one click away |
| **External advisor + lead capture** | Public agent answers customers without exposing pricing, and files inquiries to `/leads` for sales follow-up |
| **Conversation memory** | Remembers the quote/customer across turns ("draft an email for this quote" just works) |
| **Architecture graph** | Interactive system map at **`/graph`** for presentations |
| **Eval harness + CI** | Golden set: retrieval + engines (deterministic gate) + LLM-judged answers. **Measured, not vibes** |

**Deliberately small infra:** one FastAPI service, file-backed stores, brute-force vectors over a tiny corpus. No Kubernetes, no Kafka. The intelligence lives in the AI/algorithm layer — added only what earns its place.

---

## Run it

```bash
cp .env.example .env        # put your DEEPSEEK_API_KEY in .env
docker compose up -d --build
# internal Copilot : http://127.0.0.1:8000
# external Advisor : http://127.0.0.1:8000/advisor
# architecture map : http://127.0.0.1:8000/graph
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

**5 — External Advisor → lead → quote (the funnel)**
> At `/advisor` (as a customer): *"My gold recovery dropped, what do you recommend?"* → solution + citations, **no prices**. Then *"I'd like a quotation — I'm Budi from PT Vale, budi@vale.example"* → it captures the lead. Switch to the internal Copilot → the sales engineer turns that lead into a quote.

---

## Architecture

Full technical write-up (C4 + sequence diagrams + decisions): **[ARCHITECTURE.md](ARCHITECTURE.md)**. Interactive map: **`/graph`** (Cytoscape — click nodes, drag, zoom).

```
 Customer ─► Solution Advisor (external)            Sales Engineer ─► Sales Copilot (internal)
                 │  no pricing/stock                      │  full tools + memory
            capture_lead ─► leads store ─────────────────►│
                                                          ▼
        ┌───────────────┬───────────────┬────────────────┬────────────────┐
   search_product   calc_dosage    check_inventory  price_quote_line  build_quotation  (+4 more)
        │               │               │               │                │
   Hybrid Retrieval  Chemistry      data_store      Pricing/Decision   Quotation+PDF
   (BM25+dense+rerank)  Engine                         Engine
        └───────────────┴───────────────┴───────────────┴────────────────┘
                         data/*.json (real catalog + dummy internal) · knowledge/*.md
```

**Honest scope:** two ReAct agents (external Advisor + internal Copilot) sharing the same tools/engines — **not** a large multi-agent mesh. Further agents (procurement, logistics, executive, email) are shown **dashed** on `/graph` — planned, not built.

---

## Usage notes & guardrails

- **One conversation per customer / deal.** Each thread carries ~12 turns of memory; mixing several customers or RFQs in one thread can blend context. Use **New conversation** per customer — history is kept in the sidebar. The agent also anchors on the most recent customer/quote and asks a clarifying question when a request is ambiguous.
- **Numbers and product codes are tool-grounded.** The agent cannot quote a price, dosage, stock figure, or product code from memory — they come only from the engines/tools, so chat always matches the quote and PDF.
- **To create or update a quotation / its PDF**, just ask (e.g. *"build a quotation…"*, *"swap item 1 to Quick Lime and make the PDF"*) — the agent re-runs `build_quotation` and a **Download PDF** button appears.
- **Language:** toggle EN/ID in the header, or just write in either language.
- **Dataset is demo-grade:** prices/stock/RFQ history are realistic dummy; validate dosages with a metallurgist + SDS before any field use.

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
pytest tests/ -q                    # 13/13 — quotation+unit-conversion, API flow, conversations, ingest, advisor/leads, architecture
python -m eval.run_eval --no-llm    # deterministic gate: retrieval 8/8 + engines 5/5
python -m eval.run_eval             # + LLM-judged answer quality (needs API key)
```

CI runs the deterministic gate + unit tests on every push ([.github/workflows/eval.yml](.github/workflows/eval.yml)).

---

## Repo layout

```
app/
  api.py              FastAPI + SSE streaming + endpoints (copilot, advisor, leads, quotation, graph)
  agent/              tools.py (internal + external toolsets) + graph.py (two ReAct agents, memory)
  reasoning/          chemistry · compatibility · pricing (unit conversion, margin)  (deterministic)
  retrieval/          hybrid.py (BM25 + dense + reranker, cited)
  ingest/             multimodal RFQ → structured (auto-chain)
  quotation.py        quote build + canonical summary + reportlab PDF
  store_*.py          conversations · quotations · leads persistence
  architecture.py     /graph data (two-tier)
  web/                index.html (internal) · advisor.html (external) · graph.html (architecture)
data/                 hybrid dataset (real catalog + dummy internal) + knowledge/ (incl. company_profile.md)
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
| Internal Copilot: agent + 9 tools, memory, citations | Multi-user auth + RBAC |
| External Advisor + lead capture (`/advisor`, `/leads`) | Approval workflow (quote state machine) |
| Chemical / compatibility / pricing engines (+ unit conversion) | Email draft + SMTP send |
| Quotation persistence + branded PDF + canonical summary | ERP / CRM integration (replace dummy data) |
| Hybrid retrieval (BM25 active; dense pending a torch fix) | Procurement / logistics / executive agents |
| Conversation history + enterprise UI | Auto-route a captured lead into a quote |
| Bilingual ID/EN (toggle + language-aware agents) | |
| Tool-grounded guardrails (no memory-quoted prices/codes) | |
| Multimodal ingest + auto-chain · architecture graph · eval + CI | |

> Dataset note: catalog names/brands are **real** (scraped from Kemindo sites); prices, stock, and RFQ history are **realistic dummy** — swap for ERP data before production. Details in [data/README.md](data/README.md).
