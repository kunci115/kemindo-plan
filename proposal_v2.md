# Kemindo Sales Engineer Copilot
### AI Proposal v2.0 — Revenue-First, Single Wedge
Tanggal: 2026-06-27

---

## 0. Kenapa v2 (apa yang berubah dari v1)

v1 (SAD + proposal v1) merancang platform raksasa: 5 AI agent, microservice, Kubernetes, MCP, RabbitMQ/Kafka, Keycloak, 4 fase. Masalah:

- **Over-engineering** — arsitektur enterprise untuk perusahaan yang website-nya belum punya harga online. Butuh tim platform besar, resiko **tak pernah ship**.
- **Jawab "HOW" sebelum buktikan "WHAT bikin uang"** — 13 section arsitektur, 0 angka bisnis.
- **Lever revenue sebar tipis** ke 5 agent. Tak ada wedge.
- **Phase-0 (data) hilang** — semua RAG asumsikan data terdigitalisasi. Realita: di spreadsheet/email/PDF.

v2 = **satu produk tajam yang naikkan revenue, demoable dalam minggu, bukan tahun.** Sisanya menyusul setelah terbukti.

---

## 1. Realita Kemindo (basis keputusan)

Dari riset publik (kemindogroup.com, kemindo.id, goldsupplier, LinkedIn):

- **Industrial solution provider**, bukan distributor biasa. Lini: Chemical, Logistics, Energy, Agriculture.
- Group multi-entitas: PT Kemindo International (Jakarta+Singapore), PT Kemindo Artha Jaya (2014), PT Kemindo Jaya Prima (plating), divisi Energy (batubara Riau + PKS), Logistics (barge/trucking/warehouse).
- Katalog ~60 produk: reagent gold (lime, activated carbon, copper sulphate, SMBS, xanthate, Green Lixiviant), nickel (H2SO4, electrode, castable), paper "Star" line (StarLITE/StarSORB/StarPOL/StarMPOL/STARFIX).
- **Maturity digital rendah** — website ©2022, harga "IDR 0.00", tak ada datasheet online. **Implikasi: data internal belum siap → Phase-0 wajib.**

Customer beli **solusi masalah operasional** (gold recovery turun, brightness drop, butuh reagent kontrak), bukan sekadar produk. Itu peluang AI.

---

## 2. Wedge: Sales Engineer Copilot

Satu tool chat untuk **Sales Engineer**. Gabung 2 fungsi paling dekat ke uang:

1. **Konsultan Teknis** — sales ketik masalah customer ("gold recovery turun"), copilot kasih root cause + rekomendasi produk Kemindo + dosage + alternatif.
2. **RFQ → Quotation** — paste email/PDF RFQ, copilot ekstrak item → match produk → tarik harga+stok → cek guardrail margin → draft quotation + email.

Bukan chatbot publik. **Internal tool, 1 user persona, 1 alur.** Itu yang bikin fokus.

### Alur
```
Sales: "Customer gold mine, recovery turun, butuh penawaran"
        ↓
Copilot: root cause (pH? carbon? grind?) + rekomендasi
        ↓  [tool: search_product, knowledge_lookup]
        → Hydrated Lime, Activated Carbon, SMBS + dosage
        ↓  [tool: check_inventory, calc_price]
        → stok WH-Manado, harga, margin check
        ↓  [tool: draft_quotation]
        → Quotation PDF + draft email, flag approval kalau margin < floor
        ↓
Sales: review → kirim
```

---

## 3. Logika Revenue (kenapa ini naikkan duit)

| Lever | Mekanisme | Metrik |
|---|---|---|
| **Quote lebih cepat** | Deal industrial dimenangkan kecepatan respon. Copilot pangkas quote dari hari → menit | Quote cycle time, **win rate** |
| **Cross-sell otomatis** | Knowledge base petakan: gold-lime customer → butuh carbon+SMBS+grinding media. Copilot usul bundle | **Attach rate**, avg order value |
| **Guardrail margin** | Decision engine tolak/eskalasi quote di bawah floor margin → stop underpricing | **Avg margin %**, leakage |
| **Diferensiasi teknis** | Rekomendasi+dosage = jual solusi, bukan adu harga → jaga margin | Win rate di deal non-harga |
| **Capture knowledge** | Pengetahuan sales senior (dosage, aplikasi) jadi aset, tak hilang saat resign | Onboarding time sales baru |

**Target demo:** tunjukkan 1 RFQ nyata diproses < 3 menit + 1 cross-sell + 1 margin-flag. Itu cukup yakinkan management.

---

## 4. Phase 0 — DATA (blocker #1, wajib duluan)

Tanpa ini semua percuma. Paralel dengan build, bukan setelah.

| Aset | Status sekarang (asumsi) | Aksi |
|---|---|---|
| Katalog produk | Ada di web, tak terstruktur | ✅ **sudah** di-scrape → `data/products.json` (48) |
| Harga + margin rules | Internal (ERP/Excel) | Minta export price list + aturan margin |
| Stok/warehouse | Internal | Export ERP / WMS |
| Datasheet/MSDS | PDF tersebar | Kumpulkan, index ke vector DB |
| Historical RFQ/quote | Email/folder | Kumpulkan 50–100 untuk training match + pricing |
| Dosage/aplikasi | Di kepala sales senior | Wawancara → knowledge doc |

**Untuk demo SEKARANG:** sudah ada dataset hybrid di `data/` (produk nyata + dummy harga/stok/RFQ + knowledge). Demo jalan tanpa nunggu data internal. Go-live = swap dummy → real (schema sama).

---

## 5. Arsitektur (sengaja kecil)

```
        Sales (web chat, internal)
                │
        FastAPI MONOLITH  ── 1 deploy, 1 VM/Docker Compose
                │
        Agent loop (1 framework: LangGraph ATAU OpenAI SDK — pilih satu)
                │
   ┌────────────┼─────────────┬──────────────┐
 search_   check_      calc_price       draft_
 product   inventory  (+margin guard)   quotation
   │          │            │               │
        Business Service layer (LLM TAK sentuh DB langsung)
                │
        PostgreSQL + pgvector  (1 DB: katalog + RAG)
```

**Yang SENGAJA dibuang dari v1** (sampai terbukti perlu): Kubernetes, RabbitMQ, Kafka, Keycloak, MCP server, 5 microservice terpisah, multi-portal.

**Dipertahankan dari v1** (benar): pola LLM → Business Service → Repository → DB; decision engine untuk margin rules; domain decomposition.

### Stack
- Backend: **Python + FastAPI** (monolith)
- AI: **1 agent framework** + tool calling. LLM: Claude / GPT (pilih saat build)
- DB: **PostgreSQL + pgvector** (satu, bukan vector DB terpisah)
- Deploy: **Docker Compose** di 1 VM. Tanpa k8s.
- Auth: session sederhana dulu (internal users)

---

## 6. Decision Engine (bagian bernilai, jangan di-handwave)

LLM **tak** putuskan harga/diskon. Rule engine deterministik:

- **Floor margin** 8% — quote di bawah → blok/eskalasi.
- **Approval threshold**: margin < 12% → Sales Manager; < 8% atau order > Rp500jt → Commercial Director.
- **Volume discount tier** + **payment term adjust**.
- Sudah ter-encode di `data/pricing.json → margin_rules`.

Ini yang stop margin leakage — lever revenue paling konkret.

---

## 7. Metrik Sukses (ukur dari hari-1, bukan belakangan)

Baseline dulu (tanya Kemindo), lalu ukur delta:

| Metrik | Baseline (?) | Target 3 bln |
|---|---|---|
| Quote cycle time | ? hari | < 1 jam |
| Win rate | ? % | +5–10% |
| Avg margin % | ? % | +2–3 pts (kurangi leakage) |
| Cross-sell attach | ? | +1 item/quote |
| Quote volume/sales/bulan | ? | 2× |

**Tanpa baseline = proyek mati di rapat.** Angka "?" itu pertanyaan pertama ke Kemindo.

---

## 8. Roadmap (wedge dulu, ekspansi kalau terbukti)

| Fase | Isi | Kondisi lanjut |
|---|---|---|
| **0** | Data prep + dataset hybrid demo | ✅ sebagian jalan |
| **1 (WEDGE)** | Sales Engineer Copilot (consult + RFQ→quote + margin guard) | — |
| **2** | Product Knowledge expert + MSDS/datasheet RAG penuh | jika fase-1 naikkan win rate |
| **3** | Supply chain (inventory/procurement/logistics agent) | jika ops minta |
| **4** | Executive analytics + forecasting | jika data historis cukup |

Tiap fase **gated by ROI fase sebelum**. Tak bangun fase-4 sebelum fase-1 buktikan uang.

---

## 9. Risiko + mitigasi

| Risiko | Mitigasi |
|---|---|
| Data internal belum siap | Demo pakai dataset hybrid; Phase-0 paralel |
| Halusinasi dosage (safety-critical!) | Dosage dari knowledge base ter-sourcing, bukan LLM bebas; selalu flag "validate w/ metallurgist" |
| Harga salah → margin bocor | Decision engine deterministik, bukan LLM |
| Adopsi sales rendah | 1 persona, alur sederhana, hemat waktu nyata mereka |
| Scope creep balik ke v1 | Roadmap gated by ROI |

---

## 10. Next step konkret

1. **Demo MVP** dari dataset `data/` (sudah ada) — bangun copilot, target 1 RFQ < 3 menit.
2. **Pitch ke Kemindo** dengan demo → minta: price list, margin rules, 50 historical RFQ, baseline metrik.
3. **Swap dummy → real**, pilot dengan 2–3 sales engineer.
4. Ukur 4–6 minggu → keputusan lanjut fase-2.

> Prinsip: bukan "Industrial Intelligence Platform" besar dulu. Satu copilot yang **terbukti naikkan win rate + margin**, lalu ekspansi dari bukti.
