"""Multimodal RFQ ingestion.

Stage 1 (extract_text): any file -> raw text.
  - .pdf            -> pdfplumber (native text); OCR fallback if scanned + ENABLE_OCR
  - .xlsx/.xls/.csv -> pandas table -> text
  - .png/.jpg/...   -> Tesseract OCR (needs ENABLE_OCR + system tesseract)
  - .eml/.txt/.md   -> decoded text

Stage 2 (extract_rfq): raw text -> structured RFQ JSON via DeepSeek.

DeepSeek can't read images directly, so vision is handled by OCR here. Clean
separation: deterministic file->text, then LLM text->schema.
"""
from __future__ import annotations
import io
from pathlib import Path
from typing import Any
from ..config import get_settings

_IMG = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}


def extract_text(filename: str, blob: bytes) -> dict[str, Any]:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return _pdf(blob)
    if ext in {".xlsx", ".xls"}:
        return _excel(blob)
    if ext == ".csv":
        return {"text": blob.decode("utf-8", "ignore"), "method": "csv"}
    if ext in _IMG:
        return _ocr(blob)
    # eml/txt/md/unknown -> decode
    return {"text": blob.decode("utf-8", "ignore"), "method": "plaintext"}


def _pdf(blob: bytes) -> dict[str, Any]:
    import pdfplumber
    parts: list[str] = []
    with pdfplumber.open(io.BytesIO(blob)) as pdf:
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
            for tbl in page.extract_tables() or []:
                parts.append("\n".join("\t".join(c or "" for c in row) for row in tbl))
    text = "\n".join(parts).strip()
    if len(text) < 20 and get_settings().enable_ocr:
        return _ocr_pdf(blob)  # scanned PDF fallback
    return {"text": text, "method": "pdfplumber"}


def _excel(blob: bytes) -> dict[str, Any]:
    import pandas as pd
    xls = pd.ExcelFile(io.BytesIO(blob))
    parts = []
    for sheet in xls.sheet_names:
        df = xls.parse(sheet)
        parts.append(f"# Sheet: {sheet}\n{df.to_csv(index=False)}")
    return {"text": "\n\n".join(parts), "method": "pandas-excel"}


def _ocr(blob: bytes) -> dict[str, Any]:
    s = get_settings()
    if not s.enable_ocr:
        return {"text": "", "method": "ocr-disabled",
                "error": "Image upload needs ENABLE_OCR=true + system Tesseract."}
    import pytesseract
    from PIL import Image
    img = Image.open(io.BytesIO(blob))
    return {"text": pytesseract.image_to_string(img), "method": "tesseract"}


def _ocr_pdf(blob: bytes) -> dict[str, Any]:
    # minimal: render not included to avoid poppler dep; report instead
    return {"text": "", "method": "scanned-pdf",
            "error": "Scanned PDF; enable a PDF->image renderer for OCR."}


_SCHEMA_PROMPT = """You extract a purchase RFQ from raw text into strict JSON.
Return ONLY this shape:
{
  "customer_name": string|null,
  "contact": string|null,
  "delivery_location": string|null,
  "incoterm": string|null,
  "payment_term": string|null,
  "required_date": string|null,
  "items": [
    {"raw_text": string, "product_guess": string, "quantity": number|null, "unit": string|null, "spec_notes": string|null}
  ],
  "notes": string|null
}
Rules: copy quantities/units exactly as written. product_guess = your best
normalized chemical/product name. If a field is absent use null. Never invent items."""


def extract_rfq(raw_text: str) -> dict[str, Any]:
    """Text -> structured RFQ via DeepSeek (JSON mode)."""
    if not raw_text.strip():
        return {"customer_name": None, "items": [], "notes": "empty input"}
    from ..llm import json_complete  # lazy: keep pure helpers import-light
    return json_complete(_SCHEMA_PROMPT, raw_text[:12000])


def compose_rfq_prompt(rfq: dict[str, Any]) -> str:
    """Turn a structured RFQ into a natural-language instruction for the agent,
    so the user never has to retype anything after an upload (auto-chain)."""
    lines = []
    for i, it in enumerate(rfq.get("items", []), 1):
        bits = [str(it.get("product_guess") or it.get("raw_text") or "item")]
        if it.get("quantity") is not None:
            bits.append(f"{it['quantity']} {it.get('unit') or ''}".strip())
        if it.get("spec_notes"):
            bits.append(str(it["spec_notes"]))
        lines.append(f"{i}. " + " - ".join(bits))
    head = []
    if rfq.get("customer_name"):
        head.append(f"Customer: {rfq['customer_name']}")
    if rfq.get("delivery_location"):
        head.append(f"Delivery: {rfq['delivery_location']}")
    if rfq.get("incoterm"):
        head.append(f"Incoterm: {rfq['incoterm']}")
    if rfq.get("payment_term"):
        head.append(f"Payment: {rfq['payment_term']}")
    return (
        "Process this customer RFQ. Match every item to Kemindo catalog products, "
        "check stock, run a compatibility check, then build ONE quotation with "
        "margin guardrails.\n"
        + ("\n".join(head) + "\n" if head else "")
        + "Items:\n" + ("\n".join(lines) if lines else "(no items extracted)")
    )


def ingest_file(filename: str, blob: bytes) -> dict[str, Any]:
    extracted = extract_text(filename, blob)
    rfq = extract_rfq(extracted.get("text", ""))
    n = len(rfq.get("items", []))
    cust = rfq.get("customer_name") or "customer"
    return {
        "file": filename, "extraction": extracted, "rfq": rfq,
        "summary": f"Extracted {n} item(s) from {cust}.",
        "prompt": compose_rfq_prompt(rfq),   # auto-chain instruction
    }
