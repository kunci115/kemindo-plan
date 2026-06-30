# Components Reference

What every node in the [`/graph`](http://127.0.0.1:8000/graph) architecture map does.
Companion to [ARCHITECTURE.md](ARCHITECTURE.md). Grouped by layer.

---

## Agents

| Agent | Tier | Purpose | Toolset |
|---|---|---|---|
| **Sales Engineer Copilot** | internal | Turns RFQs / questions into margin-guarded, cited quotations + PDF | all tools below |
| **Solution Advisor** | external (public) | Answers customers, gives technical guidance + company info, captures leads. No pricing/stock | `search_product`, `knowledge_lookup`, `calc_dosage`, `stoichiometry`, `check_compatibility`, `capture_lead` |

Both are LangGraph ReAct agents over DeepSeek; they differ only by toolset + system prompt.

---

## Agent tools

Each tool wraps a **deterministic engine** so the LLM orchestrates but never invents numbers.

| Tool | What it does | Input → Output | Backed by |
|---|---|---|---|
| **search_product** | Finds Kemindo products by problem, name, or industry | query → top product matches **with citations** | Hybrid Retrieval |
| **knowledge_lookup** | Looks up technical root-cause / application guidance | query → cited snippets from handbooks | Hybrid Retrieval |
| **calc_dosage** | Recommends a dosage deterministically (lime→pH, HPAL acid, SMBS detox, activated carbon) | kind + value → dose range + total + note | Chemistry Engine |
| **stoichiometry** | Acid/base neutralization mass balance | acid_kg + acid + base → base kg required | Chemistry Engine |
| **check_compatibility** | Flags hazardous co-storage (oxidizer+flammable, acid+base, water-reactive…) | product ids → safe/unsafe + warnings | Compatibility Engine |
| **check_inventory** | Stock on hand per warehouse + lead time | product id → warehouses, qty, lead time | data_store (inventory) |
| **price_quote_line** | Prices one line with **unit conversion** + margin guardrail | product, qty, **unit**, discount, term → unit price, margin, floor breach, approval | Pricing / Decision Engine |
| **win_loss_hint** | Historical win/loss + avg won-margin, to price competitively | product id → won/lost count, avg won margin, hint | Pricing Engine (rfq_history) |
| **build_quotation** | Assembles + **persists** a quotation, returns number + canonical summary + PDF link | customer + lines (with units) → quotation_no, summary_markdown, approval | Quotation + Pricing |
| **get_lead** *(internal)* | Loads a captured lead by ID to quote from it | "L-xxxx" → company, contact, need, products | leads store |
| **list_new_leads** *(internal)* | Browse recent captured leads | — → list of leads (newest first) | leads store |
| **capture_lead** *(external)* | Files a customer inquiry for sales follow-up | company, contact, need, products → lead_id | leads store |

---

## Deterministic engines

Pure logic — **no LLM**. This is where every figure is actually computed.

| Engine | File | Responsibility |
|---|---|---|
| **Chemistry Engine** | `app/reasoning/chemistry.py` | Dosage formulas (pH→lime, HPAL acid, SMBS detox, carbon), stoichiometry, unit conversion |
| **Compatibility Engine** | `app/reasoning/compatibility.py` | Hazard-class segregation matrix; flags unsafe co-storage/shipping pairs |
| **Pricing / Decision Engine** | `app/reasoning/pricing.py` | Unit→catalog conversion, list/floor pricing, volume + payment-term tiers, **margin floor + approval routing** (Sales Manager / Commercial Director), win/loss hint |
| **Hybrid Retrieval** | `app/retrieval/hybrid.py` | BM25 (lexical) + dense bge (semantic) fused by RRF, then cross-encoder rerank; returns hits **with citations** |
| **Quotation + PDF** | `app/quotation.py` | Builds the quotation object, a canonical markdown summary, and the branded reportlab **PDF** |

> Rule: *LLM proposes, rules dispose.* The agent may suggest a discount or a product; the engines decide the price, margin, approval, and compatibility.

---

## Data sources

| Node | File | Contents |
|---|---|---|
| **products.json** | `data/products.json` | Catalog (48) — **real** names/brands/categories/applications |
| **pricing.json** | `data/pricing.json` | Price list + `margin_rules` (floor, tiers, approval thresholds) |
| **inventory.json** | `data/inventory.json` | Stock per warehouse + lead time |
| **rfq_history.json** | `data/rfq_history.json` | Won/lost quotes → feeds `win_loss_hint` |
| **knowledge/\*.md** | `data/knowledge/` | Gold/nickel/paper handbooks + **company_profile.md**, chunked by heading → cited |
| **quotations store** | `data/quotations/` | Persisted quotations (DRAFT…) |
| **leads store** | `data/leads/` | Captured customer inquiries |
| **conversations** | `data/conversations/` | Chat history (memory + sidebar) |

> Provenance: product names/brands/categories are real (scraped from Kemindo sites); prices, stock, RFQ history are realistic **dummy** — replace with ERP data before production. See [data/README.md](data/README.md).
