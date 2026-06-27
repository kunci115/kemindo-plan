"""
Deterministic dummy-data generator for Kemindo demo dataset.
Reads products.json (real catalog) -> writes pricing.json, inventory.json,
customers.json, rfq_history.json.

ALL OUTPUT IS DUMMY (internal data Kemindo never publishes). Realistic ranges
only. Swap with real data before production. Seeded => stable across runs.
"""
import json, random, os, datetime

random.seed(42)
HERE = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(HERE, "products.json"), encoding="utf-8") as f:
    products = json.load(f)["products"]

# ---- base cost anchors per unit (IDR), rough industrial ranges ----
UNIT_COST = {  # IDR per unit, dummy but plausible
    "kg": (3000, 35000),
    "MT": (2_500_000, 32_000_000),
    "L": (25000, 120000),
}
# category margin policy (target % over cost)
CATEGORY_MARGIN = {
    "Gold Mine": (0.18, 0.35),
    "Mining Chemical": (0.15, 0.30),
    "Nickel": (0.12, 0.28),
    "Paper Chemical": (0.20, 0.40),
    "Chemical": (0.12, 0.25),
    "Agriculture": (0.08, 0.18),
    "Energy": (0.06, 0.14),
    "Others": (0.10, 0.22),
}

WAREHOUSES = ["WH-Jakarta", "WH-Surabaya", "WH-Sulut(Manado)", "WH-Morowali", "WH-Batam"]

# ---------- PRICING ----------
pricing = {
    "_meta": {
        "description": "DUMMY pricing + margin/discount rules. NOT Kemindo real prices.",
        "currency": "IDR",
        "data_source": "dummy (seeded). Replace with ERP price list before production.",
        "generated": str(datetime.date.today()),
    },
    "margin_rules": {
        "floor_margin_pct": 0.08,
        "approval_thresholds": [
            {"if_margin_below_pct": 0.12, "approval": "Sales Manager"},
            {"if_margin_below_pct": 0.08, "approval": "Commercial Director"},
            {"if_discount_above_pct": 0.10, "approval": "Sales Manager"},
            {"if_order_value_above_idr": 500_000_000, "approval": "Commercial Director"},
        ],
        "volume_discount_tiers": [
            {"min_qty_ratio_vs_typical": 1.0, "discount_pct": 0.00},
            {"min_qty_ratio_vs_typical": 3.0, "discount_pct": 0.03},
            {"min_qty_ratio_vs_typical": 5.0, "discount_pct": 0.05},
            {"min_qty_ratio_vs_typical": 10.0, "discount_pct": 0.08},
        ],
        "payment_term_adjust": {"CBD": -0.02, "NET30": 0.0, "NET60": 0.015, "NET90": 0.03},
        "incoterm_note": "List prices are EXW WH. Add freight per incoterm (see logistics).",
    },
    "price_list": [],
}
for p in products:
    lo, hi = UNIT_COST.get(p["unit"], (3000, 35000))
    cost = round(random.uniform(lo, hi), -2)
    m_lo, m_hi = CATEGORY_MARGIN.get(p["category"], (0.12, 0.25))
    margin = random.uniform(m_lo, m_hi)
    list_price = round(cost * (1 + margin), -2)
    pricing["price_list"].append({
        "product_id": p["id"], "name": p["name"], "unit": p["unit"],
        "cost_idr": cost, "list_price_idr": list_price,
        "target_margin_pct": round(margin, 3),
        "floor_price_idr": round(cost * 1.08, -2),
    })

# ---------- INVENTORY ----------
inventory = {
    "_meta": {"description": "DUMMY stock per warehouse. NOT real.", "data_source": "dummy (seeded)",
              "generated": str(datetime.date.today())},
    "stock": [],
}
for p in products:
    # each product stocked in 1-3 warehouses
    whs = random.sample(WAREHOUSES, random.randint(1, 3))
    for wh in whs:
        if p["unit"] == "MT":
            qty = random.choice([0, 0, 25, 50, 120, 300, 600])
        elif p["unit"] == "L":
            qty = random.choice([0, 500, 1000, 4000, 8000])
        else:
            qty = random.choice([0, 0, 500, 2000, 8000, 25000, 60000])
        inventory["stock"].append({
            "product_id": p["id"], "name": p["name"], "warehouse": wh,
            "qty_on_hand": qty, "unit": p["unit"],
            "reorder_point": random.choice([500, 1000, 5000]) if p["unit"] == "kg" else random.choice([20, 50, 100]),
            "lead_time_days": random.choice([3, 7, 14, 21, 30, 45]),
        })

# ---------- CUSTOMERS ----------
CUST_SEED = [
    ("PT Agincourt Resources", "Gold Mine", "Batangtoru, Sumut"),
    ("PT Bumi Suksesindo", "Gold Mine", "Banyuwangi, Jatim"),
    ("PT Nusa Halmahera Minerals", "Gold Mine", "Halmahera, Malut"),
    ("PT Vale Indonesia", "Nickel", "Sorowako, Sulsel"),
    ("PT IMIP (Indonesia Morowali)", "Nickel", "Morowali, Sulteng"),
    ("PT Huadi Nickel-Alloy", "Nickel", "Bantaeng, Sulsel"),
    ("PT Indah Kiat Pulp & Paper", "Paper", "Serang, Banten"),
    ("PT Pindo Deli Pulp & Paper", "Paper", "Karawang, Jabar"),
    ("PT Fajar Surya Wisesa", "Paper", "Bekasi, Jabar"),
    ("PT Tjiwi Kimia", "Paper", "Mojokerto, Jatim"),
    ("PT Pabrik Kertas Tjiwi", "Paper", "Sidoarjo, Jatim"),
    ("PT Antam Tbk (UBPP)", "Gold Mine", "Pongkor, Jabar"),
    ("PT Weda Bay Nickel", "Nickel", "Halmahera, Malut"),
    ("PT Smelting Gresik", "Alumina Smelter", "Gresik, Jatim"),
    ("PT Adaro Energy", "Energy", "Tabalong, Kalsel"),
    ("PT Cargill Indonesia", "Agriculture", "Pasuruan, Jatim"),
    ("PT Charoen Pokphand", "Animal Feed", "Jakarta"),
    ("PT Aneka Tambang Nickel", "Nickel", "Kolaka, Sultra"),
    ("PT Merdeka Copper Gold", "Gold Mine", "Banyuwangi, Jatim"),
    ("PT Kawasan Industri Terpadu", "General", "Batam, Kepri"),
]
customers = {"_meta": {"description": "DUMMY customers (names are real Indonesian industrial cos for realism; "
                       "relationship/owner/credit data is fabricated).", "data_source": "dummy (seeded)",
                       "generated": str(datetime.date.today())}, "customers": []}
owners = ["Refriza H.", "Andi P.", "Budi S.", "Citra L.", "Dewi K.", "Eko W."]
for i, (name, ind, loc) in enumerate(CUST_SEED, 1):
    customers["customers"].append({
        "id": f"C{i:03d}", "company_name": name, "industry": ind, "location": loc,
        "sales_owner": random.choice(owners),
        "credit_term": random.choice(["CBD", "NET30", "NET30", "NET60", "NET90"]),
        "credit_limit_idr": random.choice([200_000_000, 500_000_000, 1_000_000_000, 2_500_000_000]),
        "tier": random.choice(["A", "A", "B", "B", "C"]),
        "ytd_revenue_idr": random.randint(50, 8000) * 1_000_000,
    })

# ---------- RFQ + QUOTATION HISTORY ----------
PROBLEM_BY_IND = {
    "Gold Mine": ["Gold recovery turun di CIL circuit", "Butuh reagent leaching bulanan",
                  "Cyanide detox effluent over limit", "Grinding media wear tinggi"],
    "Nickel": ["Butuh asam sulfat HPAL kontrak", "Refractory smelter perlu reline", "Flokulan tailing thickener"],
    "Paper": ["Brightness menurun di mesin 2", "Retention drainage drop", "Pitch/stickies deposit naik",
              "Butuh surface size starch"],
    "Alumina Smelter": ["Quick lime flux supply"], "Energy": ["PKS biomass supply"],
    "Agriculture": ["Native starch food grade", "Organic fertilizer trial"], "Animal Feed": ["PKE bulanan"],
    "General": ["Water treatment coagulant"],
}
statuses = ["WON", "WON", "WON", "LOST", "PENDING", "PENDING"]
lost_reasons = ["Harga kompetitor lebih murah", "Lead time terlalu lama", "Spec tidak sesuai", "Budget customer dipotong"]
rfqs = {"_meta": {"description": "DUMMY historical RFQ + quotation. NOT real Kemindo deals.",
                  "data_source": "dummy (seeded)", "generated": str(datetime.date.today())}, "rfqs": []}
pl = {x["product_id"]: x for x in pricing["price_list"]}
prod_by_ind = {}
for p in products:
    for ind in p["industries"]:
        prod_by_ind.setdefault(ind, []).append(p)

base_date = datetime.date(2025, 7, 1)
for n in range(1, 41):
    cust = random.choice(customers["customers"])
    ind = cust["industry"]
    cand = prod_by_ind.get(ind) or products
    items = random.sample(cand, min(len(cand), random.randint(1, 3)))
    line_items, total = [], 0
    for it in items:
        price = pl[it["id"]]
        typ = 50 if it["unit"] == "MT" else (4000 if it["unit"] == "L" else 20000)
        qty = random.choice([typ, typ * 2, typ * 5, typ // 2 or 1])
        disc = random.choice([0, 0, 0.03, 0.05])
        line_total = round(price["list_price_idr"] * qty * (1 - disc))
        margin = 1 - (price["cost_idr"] / (price["list_price_idr"] * (1 - disc)))
        total += line_total
        line_items.append({"product_id": it["id"], "name": it["name"], "qty": qty, "unit": it["unit"],
                           "unit_price_idr": price["list_price_idr"], "discount_pct": disc,
                           "line_total_idr": line_total, "realized_margin_pct": round(margin, 3)})
    d = base_date + datetime.timedelta(days=random.randint(0, 330))
    st = random.choice(statuses)
    rec = {
        "rfq_no": f"RFQ-2025-{n:03d}", "quotation_no": f"QT-2025-{n:03d}",
        "customer_id": cust["id"], "customer": cust["company_name"], "industry": ind,
        "received_date": str(d), "problem_statement": random.choice(PROBLEM_BY_IND.get(ind, ["General inquiry"])),
        "response_days": random.choice([1, 1, 2, 3, 5, 8]),
        "items": line_items, "total_idr": total, "status": st,
    }
    if st == "LOST":
        rec["lost_reason"] = random.choice(lost_reasons)
    rfqs["rfqs"].append(rec)

# ---------- WRITE ----------
def dump(name, obj):
    with open(os.path.join(HERE, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    print(f"wrote {name}: {len(obj.get('price_list') or obj.get('stock') or obj.get('customers') or obj.get('rfqs') or [])} rows")

dump("pricing.json", pricing)
dump("inventory.json", inventory)
dump("customers.json", customers)
dump("rfq_history.json", rfqs)
print("done")
