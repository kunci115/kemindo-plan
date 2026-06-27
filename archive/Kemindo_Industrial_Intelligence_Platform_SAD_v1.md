# Software Architecture Document (SAD)
## Kemindo Industrial Intelligence Platform
Version: 1.0

# 1. Purpose

This document defines the proposed software architecture for the Kemindo Industrial Intelligence Platform. The platform is designed to augment Kemindo's commercial, technical sales, and supply chain processes using AI agents.

---

# 2. Business Vision

Kemindo is an industrial solution provider across:

- Chemical
- Mining
- Nickel
- Logistics
- Energy
- Agriculture

AI should support the complete commercial lifecycle:

```text
Customer Inquiry
      ↓
Technical Consultation
      ↓
RFQ
      ↓
Quotation
      ↓
Purchase Order
      ↓
Delivery
      ↓
After Sales
```

---

# 3. Business Domains

- Commercial Domain
- Product Domain
- Supply Chain Domain
- Knowledge Domain
- Executive Analytics Domain

---

# 4. C4 Model

## Level 1 - Context

```text
Customers
Sales
Management
Warehouse
Procurement
        │
        ▼
Kemindo Industrial Intelligence Platform
        │
────────────────────────────────────────────
ERP
CRM
Warehouse
Email
Document Storage
LLM Providers
```

---

## Level 2 - Container

```text
Web Portal
Customer Portal
Internal Dashboard
          │
      API Gateway
          │
AI Orchestrator Service
          │
────────────────────────────────────────
Commercial AI
Product AI
Supply AI
Executive AI
          │
Business Services
          │
PostgreSQL
Vector DB
Object Storage
ERP
```

---

## Level 3 - Components

Commercial AI

- RFQ Parser
- Product Matcher
- Pricing Engine
- Quotation Generator

Product AI

- Product Search
- Technical Datasheet
- MSDS Retrieval
- Product Recommendation

Supply Chain AI

- Inventory Checker
- Supplier Selector
- Logistics Optimizer

Executive AI

- KPI Analyzer
- Forecast Engine
- Executive Dashboard

---

# 5. AI Agents

## Industrial Consultant Agent

Responsibilities

- Diagnose industrial problems
- Recommend chemicals
- Explain technical rationale

Inputs

- Industry
- Production
- Problem
- Existing chemical

Outputs

- Diagnosis
- Recommended products
- Suggested dosage

---

## Product Intelligence Agent

Responsibilities

- Product lookup
- Datasheet
- MSDS
- Alternatives
- Application guidance

---

## Commercial Intelligence Agent

Responsibilities

- RFQ extraction
- Product matching
- Pricing
- Margin analysis
- Quotation generation

---

## Supply Chain Intelligence Agent

Responsibilities

- Inventory lookup
- Warehouse selection
- Supplier recommendation
- Shipment recommendation

---

## Executive Agent

Responsibilities

- KPI summary
- Sales insight
- Margin analysis
- Forecasting

---

# 6. Sequence Diagrams

## RFQ Agent

```text
User
 ↓
Upload RFQ
 ↓
RFQ Parser
 ↓
Product Matcher
 ↓
Pricing Service
 ↓
Decision Engine
 ↓
Quotation Generator
 ↓
Approval
 ↓
Customer
```

---

## Industrial Consultant Agent

```text
Sales
 ↓
Describe customer problem
 ↓
AI Orchestrator
 ↓
Knowledge Retrieval
 ↓
Technical Reasoning
 ↓
Product Recommendation
 ↓
Sales Response
```

---

## Supply Chain Agent

```text
Commercial AI
 ↓
Inventory Service
 ↓
Supplier Service
 ↓
Warehouse Service
 ↓
Logistics Service
 ↓
Recommendation
```

---

# 7. Tool Calling Flow

```text
LLM
 │
 ├── search_product()
 ├── check_inventory()
 ├── calculate_pricing()
 ├── create_quotation()
 ├── search_supplier()
 ├── search_customer()
 └── create_email()
```

Tool flow

```text
User
 ↓
AI Orchestrator
 ↓
Tool Selection
 ↓
Business Service
 ↓
Repository
 ↓
Database
```

---

# 8. Database Design

## product

- id
- sku
- name
- category
- specification
- application
- msds_path
- datasheet_path

## customer

- id
- company_name
- industry
- address
- sales_owner

## supplier

- id
- company_name
- lead_time
- quality_score

## inventory

- id
- warehouse
- product_id
- quantity

## quotation

- id
- customer_id
- quotation_no
- status
- total_amount

## rfq

- id
- customer_id
- uploaded_document
- extracted_json

## conversation

- id
- user_id
- agent
- prompt
- response

## knowledge_document

- id
- title
- source
- embedding_id

---

# 9. Knowledge Base

- Product Catalog
- Technical Datasheets
- MSDS
- Historical RFQ
- Historical Quotations
- Customer Visit Reports
- Mining Handbook
- Nickel Handbook
- Paper Chemical Handbook
- SOP
- Pricing Rules
- Incoterms

---

# 10. Deployment Architecture

```text
                    Internet
                       │
                 Ingress / LoadBalancer
                       │
                 API Gateway (Kong/APISIX)
                       │
──────────────────────────────────────────────────────
             Kubernetes Cluster
──────────────────────────────────────────────────────

AI Orchestrator

Commercial AI Service
Product AI Service
Supply AI Service
Executive AI Service

Business Services

Product Service
Inventory Service
Pricing Service
Supplier Service
Quotation Service
Knowledge Service

Tool Server (MCP)

search_product
pricing_tool
inventory_tool
quotation_tool
supplier_tool

Infrastructure

Redis
RabbitMQ
PostgreSQL
Vector Database
Object Storage

Monitoring

Prometheus
Grafana
OpenTelemetry

External

ERP
CRM
Email
LLM Providers
```

---

# 11. Recommended Technology

Backend

- Python
- FastAPI

AI

- OpenAI Agents SDK
- LangGraph

Database

- PostgreSQL
- pgvector

Messaging

- RabbitMQ

Storage

- MinIO / S3

Deployment

- Docker
- Kubernetes

Observability

- Prometheus
- Grafana
- OpenTelemetry

Authentication

- Keycloak

---

# 12. Roadmap

Phase 1

- Product Intelligence
- RFQ Agent
- Quotation Generator

Phase 2

- Industrial Consultant
- Product Expert
- Knowledge Platform

Phase 3

- Inventory
- Procurement
- Logistics

Phase 4

- Executive Analytics
- Forecasting
- Cross-selling Intelligence

---

# 13. Future Enhancements

- Customer Account Intelligence
- Predictive Demand
- AI Negotiation Assistant
- Sustainability Agent
- Carbon Reporting
- Predictive Maintenance
- Voice Sales Assistant

