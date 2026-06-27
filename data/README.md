# Kemindo Demo Dataset — HYBRID (real + dummy)

Seed data for the **Sales Engineer Copilot** MVP. Built 2026-06-27.

## What's REAL vs DUMMY

| File | Real part | Dummy part |
|---|---|---|
| `products.json` | Product **names, brands** (StarLITE, StarSORB PNP, StarBULK, StarMPOL, StarPOL, StarHLime, STARFIX, Green Lixiviant), **categories, industries, applications** — scraped from Kemindo sites | `internal_code`, `unit`, `package`, `dosage_guideline`, `hazard_class` (realistic, public-spec-based, NOT Kemindo internal) |
| `pricing.json` | — | **All prices + margin/discount/approval rules** (seeded, plausible IDR) |
| `inventory.json` | Warehouse locations plausible (Sulut, Morowali real Kemindo areas) | **All stock qty, lead times** |
| `customers.json` | Company **names** are real Indonesian industrial firms (for demo realism) | **Relationship, owner, credit, revenue** all fabricated |
| `rfq_history.json` | — | **All 40 RFQ/quotation records** (seeded) |
| `knowledge/*.md` | Metallurgy/paper chemistry is public industry knowledge, mapped to real Kemindo products | Specific dosage numbers — validate before field use |

> ⚠️ Anything dummy MUST be replaced with Kemindo ERP/internal data before production. Prices and dosages are demo-only. Chemical = safety-critical.

## Real-data sources (scraped)

- https://kemindogroup.com/products — main catalog (~60 SKU)
- https://kemindogroup.com/business-area/chemical/mining-chemical/gold-mine
- https://kemindogroup.com/business-area/chemical/paper-chemical
- https://kemindo.goldsupplier.com/ — export listing (StarHLime, MOQ, starch/lime)
- https://kemindo.id/business-area — divisions (Chemical/Logistic/Energy/Agriculture)
- https://kemindo.co.id/ — sister co PT Kemindo Jaya Prima (plating/screen-print; NOT in this catalog)
- LinkedIn / RocketReach — group structure, scale

## Group structure found (context)

- **PT Kemindo International** — specialty chem, Jakarta + Singapore, since ~2008
- **PT Kemindo Artha Jaya** (2014) — agri/feed/paper/textile/oil&gas
- **PT Kemindo Jaya Prima** — plating + screen printing (brands Growel, Matsui)
- **Energy** (2013) — coal trading → own coal mine Riau + PKS biomass
- **Logistics** — barge/vessel, trucking, warehouse

## Regenerate dummy files

```
python data/_generate.py
```
Seeded (`random.seed(42)`) → stable output. Edit ranges in `_generate.py` to taste. `products.json` is hand-curated, not regenerated.

## Counts

- 48 products · 48 price rows · 103 inventory rows · 20 customers · 40 RFQ/quote records · 3 knowledge docs
