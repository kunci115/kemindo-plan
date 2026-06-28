"""Quotation assembly + persistence + PDF. Numbers come from the deterministic
pricing engine; the PDF renders that structure (never LLM prose) so figures
can't drift."""
from __future__ import annotations
import datetime
import io
import uuid
from typing import Any
from .reasoning.pricing import quote_line
from .store_quotations import save_quotation

COMPANY = {
    "name": "KEMINDO GROUP",
    "tagline": "Your Solution Partner®  ·  Industrial Chemicals · Mining · Paper · Nickel",
    "contact": "marketing@kemindogroup.com  ·  kemindogroup.com",
}


def _quotation_no() -> str:
    return f"QT-{datetime.date.today():%Y%m%d}-{uuid.uuid4().hex[:4].upper()}"


def build_quotation(customer_name: str, lines: list[dict[str, Any]],
                    payment_term: str = "NET30",
                    incoterm: str = "EXW Warehouse") -> dict[str, Any]:
    """lines: [{product_id, qty, discount_pct?}] -> full quotation, persisted."""
    decided, total, max_approval = [], 0, None
    order = [None, "Sales Manager", "Commercial Director"]
    for ln in lines:
        d = quote_line(ln["product_id"], ln["qty"],
                       ln.get("discount_pct", 0.0), payment_term,
                       unit=ln.get("unit"))
        decided.append(d.dict())
        total += d.line_total
        if order.index(d.approval_required) > order.index(max_approval):
            max_approval = d.approval_required

    quote = {
        "quotation_no": _quotation_no(),
        "date": str(datetime.date.today()),
        "customer": customer_name,
        "payment_term": payment_term,
        "incoterm": incoterm,
        "lines": decided,
        "subtotal_idr": total,
        "currency": "IDR",
        "approval_required": max_approval,
        "validity_days": 14,
        "status": "DRAFT",
        "disclaimer": "Demo prices (dummy dataset). Dosage/spec must be validated "
                      "with metallurgist + SDS before field use.",
    }
    # canonical summary the agent must present verbatim (prevents prose drift)
    quote["summary_markdown"] = _summary_md(quote)
    return save_quotation(quote)


def _summary_md(q: dict[str, Any]) -> str:
    rows = ["| # | Product | Qty | Unit Price (IDR) | Line Total (IDR) | Margin |",
            "|---|---------|-----|------------------|------------------|--------|"]
    for i, ln in enumerate(q["lines"], 1):
        rows.append(f"| {i} | {ln['name']} | {ln['qty']:g} {ln['unit']} | "
                    f"{ln['unit_price']:,.0f} | {ln['line_total']:,.0f} | {ln['margin_pct']:.1%} |")
    appr = q["approval_required"] or "None (auto-approve)"
    return ("\n".join(rows) +
            f"\n\n**Subtotal: Rp {q['subtotal_idr']:,.0f}** · Terms {q['payment_term']} · "
            f"{q['incoterm']} · valid {q['validity_days']} days\n\n"
            f"**Approval required:** {appr} · Quotation **{q['quotation_no']}** (DRAFT)")


def render_quotation_text(q: dict[str, Any]) -> str:
    rows = []
    for ln in q["lines"]:
        flag = "  ! " + "; ".join(ln["flags"]) if ln["flags"] else ""
        rows.append(
            f"- {ln['name']} x {ln['qty']:g} {ln['unit']} @ Rp{ln['unit_price']:,.0f} "
            f"(disc {ln['discount_pct']:.0%}, margin {ln['margin_pct']:.0%}) "
            f"= Rp{ln['line_total']:,.0f}{flag}")
    approval = q["approval_required"] or "None (auto-approve)"
    return (f"QUOTATION {q['quotation_no']}  ({q['date']})\nCustomer: {q['customer']}\n"
            f"Terms: {q['payment_term']} | {q['incoterm']} | valid {q['validity_days']} days\n\n"
            + "\n".join(rows) +
            f"\n\nSubtotal: Rp{q['subtotal_idr']:,.0f}\nApproval required: {approval}\n\n{q['disclaimer']}")


# ---------------- PDF (reportlab) ----------------
def render_quotation_pdf(q: dict[str, Any]) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle, Paragraph,
                                    Spacer, HRFlowable)
    from reportlab.lib.enums import TA_RIGHT

    NAVY = colors.HexColor("#10243f")
    ACC = colors.HexColor("#1f6fd6")
    LIGHT = colors.HexColor("#eef3fb")
    GREY = colors.HexColor("#6b7785")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=18 * mm, bottomMargin=16 * mm,
                            leftMargin=16 * mm, rightMargin=16 * mm,
                            title=f"Quotation {q['quotation_no']}")
    ss = getSampleStyleSheet()
    h_co = ParagraphStyle("co", parent=ss["Title"], fontSize=20, textColor=NAVY, spaceAfter=2, leading=22)
    h_tag = ParagraphStyle("tag", parent=ss["Normal"], fontSize=8, textColor=GREY, spaceAfter=1)
    small = ParagraphStyle("small", parent=ss["Normal"], fontSize=8.5, textColor=GREY)
    lbl = ParagraphStyle("lbl", parent=ss["Normal"], fontSize=8, textColor=GREY)
    val = ParagraphStyle("val", parent=ss["Normal"], fontSize=10, textColor=NAVY)
    rightbig = ParagraphStyle("rb", parent=ss["Normal"], fontSize=11, alignment=TA_RIGHT, textColor=NAVY)
    flagst = ParagraphStyle("flag", parent=ss["Normal"], fontSize=7.5, textColor=colors.HexColor("#b06a00"))
    el: list = []

    # --- letterhead (real Kemindo logo if present) ---
    from reportlab.platypus import Image as RLImage
    from .config import ROOT
    logo_path = ROOT / "app" / "web" / "assets" / "kemindo.png"
    if logo_path.exists():
        brand = RLImage(str(logo_path), width=46 * mm, height=46 * mm / (960 / 260))
        brand.hAlign = "LEFT"
        contact = Paragraph(COMPANY["tagline"] + "<br/>" + COMPANY["contact"],
                            ParagraphStyle("ct", parent=h_tag, alignment=TA_RIGHT))
        head = Table([[brand, contact]], colWidths=[None, 78 * mm])
        head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        el += [head, Spacer(1, 4), HRFlowable(width="100%", thickness=2, color=NAVY), Spacer(1, 8)]
    else:
        el += [Paragraph(COMPANY["name"], h_co),
               Paragraph(COMPANY["tagline"] + "<br/>" + COMPANY["contact"], h_tag),
               Spacer(1, 4), HRFlowable(width="100%", thickness=2, color=NAVY), Spacer(1, 8)]

    # --- title + meta ---
    el.append(Paragraph("QUOTATION", ParagraphStyle("qt", parent=ss["Title"], fontSize=15,
              textColor=ACC, spaceAfter=6)))
    meta = Table([
        [Paragraph("BILL TO", lbl), Paragraph("QUOTATION NO", lbl), Paragraph("DATE", lbl)],
        [Paragraph(f"<b>{q['customer']}</b>", val), Paragraph(q["quotation_no"], val), Paragraph(q["date"], val)],
        [Paragraph("PAYMENT TERM", lbl), Paragraph("INCOTERM", lbl), Paragraph("VALIDITY", lbl)],
        [Paragraph(q["payment_term"], val), Paragraph(q["incoterm"], val),
         Paragraph(f"{q['validity_days']} days", val)],
    ], colWidths=[None, None, None])
    meta.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), LIGHT), ("BOX", (0, 0), (-1, -1), 0.5, colors.white),
                              ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                              ("LEFTPADDING", (0, 0), (-1, -1), 8)]))
    el += [meta, Spacer(1, 10)]

    # --- line items ---
    header = ["#", "Product", "Qty", "Unit Price", "Disc", "Line Total (IDR)"]
    data = [header]
    for i, ln in enumerate(q["lines"], 1):
        name = ln["name"]
        if ln.get("flags"):
            name += "<br/>" + Paragraph("⚠ " + "; ".join(ln["flags"]), flagst).text
        cell = Paragraph(name, ParagraphStyle("pn", parent=ss["Normal"], fontSize=9, leading=11))
        data.append([str(i), cell, f"{ln['qty']:g} {ln['unit']}",
                     f"{ln['unit_price']:,.0f}", f"{ln['discount_pct']:.0%}",
                     f"{ln['line_total']:,.0f}"])
    tbl = Table(data, colWidths=[8 * mm, None, 24 * mm, 26 * mm, 13 * mm, 34 * mm], repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"), ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#d4deeb")),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (1, 0), (1, -1), 8),
    ]))
    el += [tbl, Spacer(1, 8)]

    # --- subtotal ---
    sub = Table([[Paragraph("SUBTOTAL", ParagraphStyle("st", parent=ss["Normal"], fontSize=9,
                 textColor=colors.white, alignment=TA_RIGHT)),
                 Paragraph(f"Rp {q['subtotal_idr']:,.0f}", ParagraphStyle("sv", parent=ss["Normal"],
                 fontSize=12, textColor=colors.white, alignment=TA_RIGHT))]],
                colWidths=[None, 60 * mm])
    sub.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), NAVY), ("TOPPADDING", (0, 0), (-1, -1), 7),
                             ("BOTTOMPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (-1, 0), (-1, -1), 10)]))
    el += [sub, Spacer(1, 10)]

    # --- approval box ---
    if q.get("approval_required"):
        appr = Table([[Paragraph(f"<b>Internal approval required:</b> {q['approval_required']} "
                      f"(per margin policy). Not valid until approved.",
                      ParagraphStyle("ap", parent=ss["Normal"], fontSize=8.5,
                      textColor=colors.HexColor("#8a5a00")))]])
        appr.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fff3da")),
                                  ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0b25a")),
                                  ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 6),
                                  ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
        el += [appr, Spacer(1, 10)]

    # --- terms + signature ---
    el.append(Paragraph(f"<b>Disclaimer:</b> {q['disclaimer']}", small))
    el.append(Spacer(1, 18))
    sig = Table([[Paragraph("Prepared by<br/><br/>_____________________<br/>Sales Engineer, Kemindo", small),
                  Paragraph("Customer acceptance<br/><br/>_____________________<br/>Name / Date", small)]],
                colWidths=[None, None])
    sig.setStyle(TableStyle([("TOPPADDING", (0, 0), (-1, -1), 4)]))
    el.append(sig)

    doc.build(el)
    return buf.getvalue()
