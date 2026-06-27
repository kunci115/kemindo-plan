# Future Development

Current build = single-user demo, file-backed stores, in-memory right-sizing.
Below is the path to a multi-user enterprise tool. Each phase is gated by ROI of
the prior (see [proposal_v2.md](proposal_v2.md)). Nothing here is built yet —
deliberate, to keep the wedge shippable.

## Already stubbed for this (no rework needed)
- `conversation.owner` field exists (`app/store_conversations.py`) → ready to scope per user.
- Quotation `status` field exists (`DRAFT`) → ready for an approval state machine.
- Deterministic decision engine already computes `approval_required` per margin policy.

---

## 1. Multi-user + auth + roles
**Goal:** real users (Sales Engineer, Sales Manager, Commercial Director), data scoped per user/team.

| Item | Approach |
|---|---|
| Auth | Keycloak / OAuth2 (or simple JWT for pilot). Login page. |
| Identity | `users` table; replace hardcoded "Sales Engineer" chip with real session. |
| Scoping | filter conversations + quotations by `owner` / `team`. |
| RBAC | role gates: who can approve, who sees margins/cost, who exports. |
| Storage | migrate file stores → **PostgreSQL** (users, conversations, quotations, audit). |

## 2. Approval workflow (close the decision-engine loop)
**Goal:** a quote below floor margin actually routes to an approver.

```
Sales builds quote ──> status DRAFT
   margin < floor? ──> status PENDING_APPROVAL ──> notify Sales Manager / Director
        approver acts ──> APPROVED / REJECTED (with reason)
              APPROVED ──> issue PDF + send to customer
```
- Quote status machine: DRAFT → PENDING → APPROVED/REJECTED → SENT → WON/LOST.
- Approval inbox per manager; audit log of who approved what (compliance).

## 3. Email / delivery
**Goal:** issue the quotation to the customer without leaving the tool.

| Item | Approach |
|---|---|
| Draft | agent already writes email prose; add a dedicated `draft_email` tool + editable preview. |
| Send | SMTP / provider (SendGrid, M365 Graph). Attach the generated PDF. |
| Track | log sent timestamp + recipient on the quotation; later: open/reply tracking. |
| Templates | branded HTML email template (matches PDF letterhead). |

## 4. Integrations (replace dummy internal data)
- **ERP** price list + live inventory (replace `pricing.json` / `inventory.json`).
- **CRM** customer + opportunity sync.
- **Document store** for real MSDS / datasheets → feed the RAG index.
- See `data/README.md` — schemas already match; swap source, keep code.

## 5. Retrieval hardening
- Fix dense embeddings (torch meta-tensor bug) → re-enable hybrid (BM25 + bge + reranker).
- Move vectors to **pgvector** once corpus > a few thousand chunks.
- Add datasheet/MSDS ingestion pipeline (PDF → chunk → embed → cite).

## 6. Observability + ops
- Structured logging, request tracing, token/cost metering per conversation.
- Prometheus/Grafana, OpenTelemetry (only when multi-user traffic justifies it).
- Eval in CI already gates correctness; add latency + cost regression checks.

## 7. Further AI agents (after wedge proves ROI)
Procurement negotiation · logistics optimization · executive analytics /
forecasting · predictive demand · cross-sell intelligence. Each is a new tool +
graph node on the **same** monolith — no architectural change required.

---

### Guiding principle
Stay a monolith with file/DB stores until traffic forces otherwise. Add
infrastructure (Postgres, Keycloak, queues, k8s) **only when a concrete need
appears** — never preemptively. The intelligence is the moat, not the YAML.
