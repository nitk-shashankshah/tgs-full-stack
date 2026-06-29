import base64
import io
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Optional

import anthropic
import pypdfium2 as pdfium
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
pt = 1.0  # ReportLab's native unit is points
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

CATALOGS_DIR = Path("data/catalogs")
CATALOGS_DIR.mkdir(parents=True, exist_ok=True)

PRICELISTS_DIR = Path("data/pricelists")
PRICELISTS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI()

# Default to local Vite dev servers; extra origins (e.g. the deployed frontend)
# can be added via the ALLOWED_ORIGINS env var as a comma-separated list.
_default_origins = ["http://localhost:5173", "http://localhost:5174", "http://localhost:5175"]
_extra_origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_default_origins + _extra_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = anthropic.AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


# ---------------------------------------------------------------------------
# PDF helpers
# ---------------------------------------------------------------------------

def render_pdf_pages(pdf_bytes: bytes, scale: float = 1.5) -> list[tuple[str, int, int]]:
    """Render each PDF page to base64 JPEG. Returns list of (b64_jpeg, width, height)."""
    doc = pdfium.PdfDocument(pdf_bytes)
    pages = []
    for i in range(len(doc)):
        page = doc[i]
        bitmap = page.render(scale=scale)
        pil_img = bitmap.to_pil().convert("RGB")
        buf = io.BytesIO()
        pil_img.save(buf, format="JPEG", quality=82)
        b64 = base64.standard_b64encode(buf.getvalue()).decode("utf-8")
        pages.append((b64, pil_img.width, pil_img.height))
    return pages


def crop_product_image(page_b64: str, crop: dict, page_w: int, page_h: int) -> str | None:
    """Crop {x,y,w,h} percentages from a base64 JPEG page. Returns base64 JPEG or None."""
    try:
        img = Image.open(io.BytesIO(base64.standard_b64decode(page_b64))).convert("RGB")
        x = max(0, int(crop["x"] / 100 * page_w))
        y = max(0, int(crop["y"] / 100 * page_h))
        w = max(20, int(crop["w"] / 100 * page_w))
        h = max(20, int(crop["h"] / 100 * page_h))
        cropped = img.crop((x, y, min(x + w, page_w), min(y + h, page_h)))
        buf = io.BytesIO()
        cropped.save(buf, format="JPEG", quality=88)
        return base64.standard_b64encode(buf.getvalue()).decode("utf-8")
    except Exception:
        return None


def make_thumbnail(data_uri: str, size: int = 64) -> str:
    """Resize a data-URI image to a square thumbnail. Returns base64 JPEG."""
    b64 = data_uri.split(",", 1)[1] if "," in data_uri else data_uri
    img = Image.open(io.BytesIO(base64.standard_b64decode(b64))).convert("RGB")
    w, h = img.size
    m = min(w, h)
    img = img.crop(((w - m) // 2, (h - m) // 2, (w + m) // 2, (h + m) // 2))
    img = img.resize((size, size), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=72)
    return "data:image/jpeg;base64," + base64.standard_b64encode(buf.getvalue()).decode()


def clean_json_response(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Catalog file helpers
# ---------------------------------------------------------------------------

def catalog_path(catalog_id: str) -> Path:
    return CATALOGS_DIR / f"{catalog_id}.json"


def read_catalog(catalog_id: str) -> dict:
    p = catalog_path(catalog_id)
    if not p.exists():
        raise HTTPException(status_code=404, detail="Catalog not found")
    return json.loads(p.read_text())


def write_catalog(data: dict) -> None:
    catalog_path(data["id"]).write_text(json.dumps(data, ensure_ascii=False, indent=2))


def list_all_catalogs() -> list[dict]:
    files = sorted(CATALOGS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    result = []
    for f in files:
        try:
            result.append(json.loads(f.read_text()))
        except Exception:
            pass
    return result


# ---------------------------------------------------------------------------
# Claude extraction prompt
# ---------------------------------------------------------------------------

EXTRACTION_PROMPT = """You are a product catalog extraction specialist. The rendered page images follow the PDF document — image block 0 = page 1, image block 1 = page 2, etc.

Carefully analyze this supplier catalog and extract ALL information including product images.

Return a single valid JSON object:
{
  "supplier": {
    "name": "Supplier company name",
    "contact": "Primary contact person name or empty string",
    "email": "contact email or empty string",
    "phone": "phone number or empty string",
    "location": "city, country or empty string",
    "terms": "payment/shipping terms or empty string",
    "conf": {
      "name": "high|med|low",
      "contact": "high|med|low",
      "email": "high|med|low",
      "phone": "high|med|low",
      "location": "high|med|low",
      "terms": "high|med|low"
    }
  },
  "products": [
    {
      "id": "p1",
      "name": "Full product name",
      "sku": "SKU/product code or empty string",
      "price": "numeric price as string e.g. '74.00'",
      "currency": "currency symbol e.g. '€' '₹' '$'",
      "moq": "minimum order quantity as string or empty string",
      "specs": "key product specifications materials dimensions features",
      "lead": "lead time e.g. '3 wks' or empty string",
      "categories": ["category1", "category2"],
      "page_index": 0,
      "image_crop": {"x": 10.5, "y": 20.0, "w": 35.0, "h": 40.0},
      "conf": {
        "name": "high|med|low",
        "sku": "high|med|low",
        "price": "high|med|low",
        "moq": "high|med|low",
        "specs": "high|med|low"
      }
    }
  ]
}

For image_crop: look at the rendered page images and identify where the product photo/image is. Use percentages (0-100) from the top-left. Set image_crop to null if no product image is visible.

Confidence: "high" = clearly stated, "med" = inferred, "low" = not found (use empty string for value).
Extract EVERY product. Use "₹" for Indian catalogs. Increment ids p1, p2, p3...
Return ONLY the JSON object, no markdown."""


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.post("/api/upload-catalog")
async def upload_catalog(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File exceeds 50 MB limit")

    pdf_b64 = base64.standard_b64encode(content).decode("utf-8")

    pages = render_pdf_pages(content, scale=1.5)
    total_page_count = len(pages)
    pages = pages[:12]

    message_content: list[Any] = [
        {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": pdf_b64}}
    ]
    for page_b64, _w, _h in pages:
        message_content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": page_b64},
        })
    message_content.append({"type": "text", "text": EXTRACTION_PROMPT})

    try:
        async with client.messages.stream(
            model="claude-opus-4-8",
            max_tokens=32000,
            messages=[{"role": "user", "content": message_content}],
        ) as stream:
            message = await stream.get_final_message()

        raw_text = next((b.text for b in message.content if b.type == "text"), "")
        data = json.loads(clean_json_response(raw_text))

        # Normalize supplier
        supplier = data.setdefault("supplier", {})
        for field in ["name", "contact", "email", "phone", "location", "terms"]:
            supplier.setdefault(field, "")
        supplier.setdefault("conf", {})
        for field in ["name", "contact", "email", "phone", "location", "terms"]:
            supplier["conf"].setdefault(field, "low")

        # Normalize products and crop images
        for i, product in enumerate(data.get("products", [])):
            product.setdefault("id", f"p{i+1}")
            for field in ["name", "sku", "price", "currency", "moq", "specs", "lead"]:
                product.setdefault(field, "")
            product.setdefault("categories", [])
            product.setdefault("reviewed", False)
            product.setdefault("conf", {})
            for field in ["name", "sku", "price", "moq", "specs"]:
                product["conf"].setdefault(field, "low")

            product["image"] = None
            product["thumbnail"] = None
            page_idx = product.pop("page_index", None)
            image_crop = product.pop("image_crop", None)
            if image_crop and page_idx is not None and 0 <= page_idx < len(pages):
                page_b64, page_w, page_h = pages[page_idx]
                cropped = crop_product_image(page_b64, image_crop, page_w, page_h)
                if cropped:
                    product["image"] = f"data:image/jpeg;base64,{cropped}"
                    product["thumbnail"] = make_thumbnail(product["image"])

        catalog_id = f"c_{int(time.time() * 1000)}"
        products = data.get("products", [])
        # Store first available product image as a catalog-level cover
        first_img = next((p["image"] for p in products if p.get("image")), None)
        cover_image = make_thumbnail(first_img, size=80) if first_img else None
        catalog_record = {
            "id": catalog_id,
            "file": file.filename,
            "uploadedAt": int(time.time() * 1000),
            "pageCount": total_page_count,
            "status": "in_review",
            "coverImage": cover_image,
            "supplier": data["supplier"],
            "products": products,
        }
        write_catalog(catalog_record)

        return {
            "success": True,
            "catalogId": catalog_id,
            "fileName": file.filename,
            "pageCount": total_page_count,
            "coverImage": cover_image,
            "supplier": data["supplier"],
            "products": data.get("products", []),
        }

    except json.JSONDecodeError as e:
        # Truncation produces unterminated JSON — surface it clearly
        detail = f"Claude response was cut off (catalog too large or too many products). Try again. Detail: {str(e)}"
        raise HTTPException(status_code=500, detail=detail)
    except anthropic.APIError as e:
        raise HTTPException(status_code=502, detail=f"Claude API error: {str(e)}")


@app.get("/api/catalogs")
def get_catalogs():
    """Return all saved catalogs. coverImage kept; per-product images stripped."""
    all_catalogs = list_all_catalogs()
    slim = []
    for c in all_catalogs:
        slim.append({
            **c,
            "products": [
                {k: v for k, v in p.items() if k != "image"}  # keep thumbnail, strip full image
                for p in c.get("products", [])
            ],
        })
    return slim


@app.get("/api/catalogs/{catalog_id}")
def get_catalog(catalog_id: str):
    """Return a single catalog including product images."""
    return read_catalog(catalog_id)


class StatusUpdate(BaseModel):
    status: str


@app.patch("/api/catalogs/{catalog_id}")
def update_catalog_status(catalog_id: str, body: StatusUpdate):
    """Update catalog status (e.g. in_review → reviewed)."""
    data = read_catalog(catalog_id)
    data["status"] = body.status
    write_catalog(data)
    return {"id": catalog_id, "status": data["status"]}


PRICELIST_PROMPT = """Extract all product pricing from this price list PDF.

Return a single valid JSON object:
{
  "supplier_name": "Supplier company name or empty string",
  "products": [
    {
      "name": "Product name",
      "sku": "SKU or product code or empty string",
      "price": "numeric price as string e.g. '74.00' or empty string",
      "currency": "currency symbol e.g. '₹' '€' '$'",
      "moq": "minimum order quantity as string or empty string"
    }
  ]
}

Extract EVERY product entry with a price. Return ONLY the JSON object, no markdown."""


def _name_words(name: str) -> set[str]:
    """Lowercase words of 3+ chars for fuzzy name matching."""
    return {w for w in re.sub(r"[^a-z0-9 ]", " ", name.lower()).split() if len(w) >= 3}


def match_and_update_catalogs(pl_products: list[dict]) -> list[dict]:
    """
    For each price-list product, find catalog products with missing price and update them.
    Match priority: exact SKU > name word-overlap ≥ 60%.
    Returns list of update records.
    """
    catalogs = list_all_catalogs()
    updates: list[dict] = []

    # Build lookup maps
    sku_map: dict[str, list[tuple[dict, dict]]] = {}   # sku -> [(catalog, product)]
    for cat in catalogs:
        for prod in cat.get("products", []):
            sku = prod.get("sku", "").strip().upper()
            if sku:
                sku_map.setdefault(sku, []).append((cat, prod))

    for pl_item in pl_products:
        new_price = pl_item.get("price", "").strip()
        new_currency = pl_item.get("currency", "").strip()
        new_moq = pl_item.get("moq", "").strip()
        if not new_price:
            continue

        pl_sku = pl_item.get("sku", "").strip().upper()
        pl_words = _name_words(pl_item.get("name", ""))

        candidates: list[tuple[dict, dict, str]] = []  # (catalog, product, match_type)

        # 1. SKU match
        if pl_sku and pl_sku in sku_map:
            for cat, prod in sku_map[pl_sku]:
                candidates.append((cat, prod, "sku"))

        # 2. Name similarity match (only if no SKU match)
        if not candidates and pl_words:
            for cat in catalogs:
                for prod in cat.get("products", []):
                    prod_words = _name_words(prod.get("name", ""))
                    if not prod_words:
                        continue
                    overlap = len(pl_words & prod_words)
                    ratio = overlap / min(len(pl_words), len(prod_words))
                    if ratio >= 0.60:
                        candidates.append((cat, prod, "name"))

        for cat, prod, match_type in candidates:
            old_price = prod.get("price", "").strip()
            old_currency = prod.get("currency", "").strip()
            # Only update if price is missing
            if old_price:
                continue

            prod["price"] = new_price
            if new_currency and not old_currency:
                prod["currency"] = new_currency
            if new_moq and not prod.get("moq", "").strip():
                prod["moq"] = new_moq

            updates.append({
                "catalogId": cat["id"],
                "catalogFile": cat.get("file", ""),
                "productId": prod["id"],
                "productName": prod["name"],
                "oldPrice": old_price,
                "newPrice": new_price,
                "currency": prod["currency"],
                "matchType": match_type,
            })

    # Persist modified catalogs
    modified_ids = {u["catalogId"] for u in updates}
    for cat in catalogs:
        if cat["id"] in modified_ids:
            write_catalog(cat)

    return updates


@app.post("/api/upload-pricelist")
async def upload_pricelist(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    content = await file.read()
    pdf_b64 = base64.standard_b64encode(content).decode("utf-8")

    try:
        async with client.messages.stream(
            model="claude-opus-4-8",
            max_tokens=32000,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": pdf_b64}},
                    {"type": "text", "text": PRICELIST_PROMPT},
                ],
            }],
        ) as stream:
            message = await stream.get_final_message()

        raw_text = next((b.text for b in message.content if b.type == "text"), "")
        data = json.loads(clean_json_response(raw_text))

        pl_products = data.get("products", [])
        supplier_name = data.get("supplier_name", "")

        updates = match_and_update_catalogs(pl_products)

        pricelist_id = f"pl_{int(time.time() * 1000)}"
        record = {
            "id": pricelist_id,
            "file": file.filename,
            "uploadedAt": int(time.time() * 1000),
            "supplierName": supplier_name,
            "productsExtracted": len(pl_products),
            "updates": updates,
        }
        (PRICELISTS_DIR / f"{pricelist_id}.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2)
        )

        return record

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse price list response: {str(e)}")
    except anthropic.APIError as e:
        raise HTTPException(status_code=502, detail=f"Claude API error: {str(e)}")


@app.get("/api/pricelists")
def get_pricelists():
    files = sorted(PRICELISTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    result = []
    for f in files:
        try:
            result.append(json.loads(f.read_text()))
        except Exception:
            pass
    return result


class CombinationsRequest(BaseModel):
    query: str


COMBINATIONS_PROMPT = """You are a product sourcing assistant. A buyer has described what they want. Your job is to suggest the best product combinations from the available catalog.

Buyer's request:
{query}

Available products (format: [productId|catalogId] name | price | categories | supplier):
{products_list}

Return a JSON object with up to 3 distinct combinations that satisfy the request:
{{
  "query_understanding": "one sentence summary of what the buyer wants",
  "budget": 5000,
  "currency": "₹",
  "combinations": [
    {{
      "title": "Short combination name",
      "description": "1-2 sentence explanation of why this combination works",
      "total": 4750,
      "products": [
        {{
          "productId": "p1",
          "catalogId": "c_123",
          "name": "Product name",
          "price": 245.0,
          "currency": "₹",
          "quantity": 1,
          "supplier": "Supplier name",
          "categories": ["category"]
        }}
      ]
    }}
  ]
}}

Rules:
- Each combination must stay within the stated budget (if one is mentioned)
- If no budget is mentioned, aim for balanced value
- Only use products from the list — do not invent products
- Vary the combinations — each should offer a meaningfully different selection
- If the buyer specified product types (e.g. "shirts and wallets"), respect that filter
- Keep combinations practical (2–8 products, realistic quantities)
- Return ONLY the JSON object, no markdown"""


@app.post("/api/combinations")
async def find_combinations(body: CombinationsRequest):
    catalogs = list_all_catalogs()

    # Build flat product list — only include products with a price
    all_products = []
    for cat in catalogs:
        supplier_name = cat.get("supplier", {}).get("name", "Unknown")
        for p in cat.get("products", []):
            price_str = p.get("price", "").strip()
            if not price_str:
                continue
            try:
                float(price_str)
            except ValueError:
                continue
            all_products.append({
                "productId": p["id"],
                "catalogId": cat["id"],
                "name": p.get("name", ""),
                "sku": p.get("sku", ""),
                "price": price_str,
                "currency": p.get("currency", ""),
                "moq": p.get("moq", ""),
                "categories": p.get("categories", []),
                "supplier": supplier_name,
                "thumbnail": p.get("thumbnail"),
            })

    if not all_products:
        raise HTTPException(status_code=400, detail="No priced products found. Upload and approve some catalogs first.")

    products_list = "\n".join(
        f"[{p['productId']}|{p['catalogId']}] {p['name']} | {p['currency']}{p['price']} | {', '.join(p['categories'])} | {p['supplier']}"
        for p in all_products
    )

    prompt = COMBINATIONS_PROMPT.format(query=body.query, products_list=products_list)

    try:
        async with client.messages.stream(
            model="claude-opus-4-8",
            max_tokens=8000,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            message = await stream.get_final_message()

        raw_text = next((b.text for b in message.content if b.type == "text"), "")
        data = json.loads(clean_json_response(raw_text))

        # Enrich returned products with thumbnail from our catalog data
        thumbnail_map = {(p["productId"], p["catalogId"]): p.get("thumbnail") for p in all_products}
        for combo in data.get("combinations", []):
            for prod in combo.get("products", []):
                key = (prod.get("productId"), prod.get("catalogId"))
                prod["thumbnail"] = thumbnail_map.get(key)

        return data

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse combinations response: {str(e)}")
    except anthropic.APIError as e:
        raise HTTPException(status_code=502, detail=f"Claude API error: {str(e)}")


class BrochureProduct(BaseModel):
    name: str
    price: float
    currency: str = "₹"
    quantity: int = 1
    supplier: str = ""
    categories: list[str] = []
    thumbnail: Optional[str] = None


class BrochureRequest(BaseModel):
    title: str
    description: str = ""
    currency: str = "₹"
    total: float
    products: list[BrochureProduct]


def _decode_thumbnail(data_uri: str | None) -> Image.Image | None:
    """Decode a data URI thumbnail into a PIL Image, or return None."""
    if not data_uri or not data_uri.startswith("data:"):
        return None
    try:
        header, b64data = data_uri.split(",", 1)
        raw = base64.standard_b64decode(b64data)
        return Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception:
        return None


def _draw_rounded_rect(c: rl_canvas.Canvas, x: float, y: float, w: float, h: float,
                        r: float, fill_color: HexColor, stroke_color: HexColor | None = None):
    p = c.beginPath()
    p.roundRect(x, y, w, h, r)
    c.setFillColor(fill_color)
    if stroke_color:
        c.setStrokeColor(stroke_color)
        c.drawPath(p, fill=1, stroke=1)
    else:
        c.drawPath(p, fill=1, stroke=0)


def generate_brochure_pdf(req: BrochureRequest) -> bytes:
    """Generate a warm-luxury styled PDF brochure for a product combination."""
    buf = io.BytesIO()
    PAGE_W, PAGE_H = A4  # 595.27 x 841.89 pts
    MARGIN = 36 * pt  # ~12.7mm

    # ── Palette ──────────────────────────────────────────────────────────────
    CREAM       = HexColor("#FAF6F0")
    BROWN_DARK  = HexColor("#2C1A0E")
    GOLD        = HexColor("#B8860B")
    GOLD_LIGHT  = HexColor("#F5EDD8")
    RULE_COLOR  = HexColor("#D4B483")
    CARD_BG     = HexColor("#FFFFFF")
    CARD_BORDER = HexColor("#EDE5D8")
    MUTED       = HexColor("#8A7A68")
    FOOTER_BG   = HexColor("#F0E8D8")

    c = rl_canvas.Canvas(buf, pagesize=A4)

    # ── Background ────────────────────────────────────────────────────────────
    c.setFillColor(CREAM)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    # ── Top decorative band ───────────────────────────────────────────────────
    BAND_H = 6 * pt
    c.setFillColor(BROWN_DARK)
    c.rect(0, PAGE_H - BAND_H, PAGE_W, BAND_H, fill=1, stroke=0)

    # Thin gold rule below band
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.8)
    c.line(MARGIN, PAGE_H - BAND_H - 6, PAGE_W - MARGIN, PAGE_H - BAND_H - 6)

    # ── Header text ───────────────────────────────────────────────────────────
    HEADER_TOP = PAGE_H - BAND_H - 28 * pt

    # Title (large, serif-bold)
    c.setFont("Times-Bold", 28)
    c.setFillColor(BROWN_DARK)
    # Word-wrap title if needed
    max_title_w = PAGE_W - 2 * MARGIN
    words = req.title.split()
    lines, line = [], []
    for word in words:
        test = " ".join(line + [word])
        if c.stringWidth(test, "Times-Bold", 28) <= max_title_w:
            line.append(word)
        else:
            if line:
                lines.append(" ".join(line))
            line = [word]
    if line:
        lines.append(" ".join(line))

    y_cursor = HEADER_TOP
    for i, text_line in enumerate(lines):
        # First word of each line in dark brown, rest in gold — like the sample PDFs
        title_words = text_line.split(" ", 1)
        x = MARGIN
        c.setFont("Times-Bold", 28)
        c.setFillColor(BROWN_DARK)
        c.drawString(x, y_cursor, title_words[0])
        if len(title_words) > 1:
            x += c.stringWidth(title_words[0] + " ", "Times-Bold", 28)
            c.setFillColor(GOLD)
            c.drawString(x, y_cursor, title_words[1])
        y_cursor -= 34 * pt

    # Gold rule with dot
    y_cursor -= 4 * pt
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.7)
    rule_y = y_cursor + 6 * pt
    c.line(MARGIN, rule_y, PAGE_W - MARGIN, rule_y)
    # Centre diamond
    mid_x = PAGE_W / 2
    c.setFillColor(GOLD)
    c.circle(mid_x, rule_y, 2.5, fill=1, stroke=0)
    y_cursor -= 6 * pt

    # Description (italic serif)
    if req.description:
        c.setFont("Times-Italic", 11)
        c.setFillColor(MUTED)
        desc_words = req.description.split()
        desc_lines, dl = [], []
        for w in desc_words:
            test = " ".join(dl + [w])
            if c.stringWidth(test, "Times-Italic", 11) <= max_title_w:
                dl.append(w)
            else:
                if dl:
                    desc_lines.append(" ".join(dl))
                dl = [w]
        if dl:
            desc_lines.append(" ".join(dl))
        for dl_line in desc_lines:
            c.drawString(MARGIN, y_cursor, dl_line)
            y_cursor -= 15 * pt

    y_cursor -= 8 * pt

    # ── Product cards ─────────────────────────────────────────────────────────
    COLS = 2
    GUTTER = 12 * pt
    CARD_W = (PAGE_W - 2 * MARGIN - GUTTER) / 2
    IMG_SIZE = 56 * pt
    CARD_H = IMG_SIZE + 24 * pt  # image + text padding

    products = req.products
    rows = (len(products) + COLS - 1) // COLS

    for row_idx in range(rows):
        if y_cursor - CARD_H < 60 * pt:
            c.showPage()
            c.setFillColor(CREAM)
            c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
            y_cursor = PAGE_H - 30 * pt

        for col_idx in range(COLS):
            p_idx = row_idx * COLS + col_idx
            if p_idx >= len(products):
                break
            p = products[p_idx]

            card_x = MARGIN + col_idx * (CARD_W + GUTTER)
            card_y = y_cursor - CARD_H

            # Card background
            _draw_rounded_rect(c, card_x, card_y, CARD_W, CARD_H, 6 * pt,
                                CARD_BG, CARD_BORDER)

            # Product thumbnail
            img_pad = 10 * pt
            img_x = card_x + img_pad
            img_y = card_y + (CARD_H - IMG_SIZE) / 2
            thumb_pil = _decode_thumbnail(p.thumbnail)
            if thumb_pil:
                # Fit image into square, preserving aspect
                thumb_pil.thumbnail((int(IMG_SIZE), int(IMG_SIZE)), Image.LANCZOS)
                img_buf = io.BytesIO()
                thumb_pil.save(img_buf, format="JPEG", quality=85)
                img_buf.seek(0)
                # Draw rounded clip region (approximated with rect)
                c.saveState()
                from reportlab.lib.utils import ImageReader
                c.drawImage(ImageReader(img_buf), img_x, img_y, IMG_SIZE, IMG_SIZE,
                            preserveAspectRatio=True, anchor="c", mask="auto")
                c.restoreState()
            else:
                # Placeholder pattern
                c.setFillColor(GOLD_LIGHT)
                c.rect(img_x, img_y, IMG_SIZE, IMG_SIZE, fill=1, stroke=0)
                c.setFillColor(RULE_COLOR)
                c.setFont("Helvetica", 8)
                c.drawCentredString(img_x + IMG_SIZE / 2, img_y + IMG_SIZE / 2 - 4, "No image")

            # Text area to the right of image
            text_x = img_x + IMG_SIZE + 8 * pt
            text_max_w = CARD_W - IMG_SIZE - img_pad - 8 * pt - 8 * pt
            text_y = card_y + CARD_H - 16 * pt

            # Product name (wrap if needed)
            c.setFont("Helvetica-Bold", 10)
            c.setFillColor(BROWN_DARK)
            name_words = p.name.split()
            name_lines, nl = [], []
            for w in name_words:
                test = " ".join(nl + [w])
                if c.stringWidth(test, "Helvetica-Bold", 10) <= text_max_w:
                    nl.append(w)
                else:
                    if nl:
                        name_lines.append(" ".join(nl))
                    nl = [w]
            if nl:
                name_lines.append(" ".join(nl))
            for nl_line in name_lines[:2]:  # max 2 lines
                c.drawString(text_x, text_y, nl_line)
                text_y -= 13 * pt

            # Supplier
            c.setFont("Helvetica", 8.5)
            c.setFillColor(MUTED)
            supplier_text = p.supplier[:28] + "…" if len(p.supplier) > 28 else p.supplier
            c.drawString(text_x, text_y, supplier_text)
            text_y -= 13 * pt

            # Category tag
            if p.categories:
                cat_text = p.categories[0]
                tag_w = c.stringWidth(cat_text, "Helvetica", 7.5) + 8 * pt
                _draw_rounded_rect(c, text_x, text_y - 2 * pt, tag_w, 12 * pt, 3 * pt, GOLD_LIGHT)
                c.setFillColor(GOLD)
                c.setFont("Helvetica", 7.5)
                c.drawString(text_x + 4 * pt, text_y + 1 * pt, cat_text)
                text_y -= 15 * pt

            # Price
            price_val = p.price * p.quantity
            price_text = f"{p.currency}{price_val:,.0f}"
            if p.quantity > 1:
                price_text += f"  ×{p.quantity}"
            c.setFont("Helvetica-Bold", 13)
            c.setFillColor(GOLD)
            c.drawString(text_x, card_y + 10 * pt, price_text)

        y_cursor -= CARD_H + 10 * pt

    # ── Footer ────────────────────────────────────────────────────────────────
    FOOTER_H = 48 * pt
    footer_y = 0

    c.setFillColor(FOOTER_BG)
    c.rect(0, footer_y, PAGE_W, FOOTER_H, fill=1, stroke=0)
    c.setStrokeColor(RULE_COLOR)
    c.setLineWidth(0.8)
    c.line(0, FOOTER_H, PAGE_W, FOOTER_H)

    # Total amount
    c.setFont("Times-Bold", 18)
    c.setFillColor(BROWN_DARK)
    total_label = "Total"
    c.drawString(MARGIN, FOOTER_H - 28 * pt, total_label)
    total_value = f"{req.currency}{req.total:,.0f}"
    c.setFillColor(GOLD)
    c.drawRightString(PAGE_W - MARGIN, FOOTER_H - 28 * pt, total_value)

    # Product count
    c.setFont("Helvetica", 8.5)
    c.setFillColor(MUTED)
    count_text = f"{len(req.products)} product{'s' if len(req.products) != 1 else ''} · Curated by Intake"
    c.drawString(MARGIN, FOOTER_H - 40 * pt, count_text)

    # Bottom gold band
    c.setFillColor(BROWN_DARK)
    c.rect(0, 0, PAGE_W, 4 * pt, fill=1, stroke=0)

    c.save()
    return buf.getvalue()


@app.post("/api/generate-brochure")
async def generate_brochure(req: BrochureRequest):
    try:
        pdf_bytes = generate_brochure_pdf(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Brochure generation failed: {str(e)}")

    safe_title = re.sub(r"[^a-zA-Z0-9\-_ ]", "", req.title).strip().replace(" ", "_")[:40] or "brochure"
    filename = f"{safe_title}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/health")
def health():
    return {"status": "ok"}
