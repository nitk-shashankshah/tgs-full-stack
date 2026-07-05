import os
import re
import io
import time
import uuid
import json
import base64
import hashlib
import logging
import urllib.request
from urllib.parse import unquote
from typing import Optional

import anthropic
import pypdfium2 as pdfium
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
pt = 1.0  # ReportLab's native unit is points

from database import get_db, engine
import models
import schema

models.Base.metadata.create_all(bind=engine)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="TGS Catalogue API", version="2.0")

_default_origins = ["http://localhost:5173", "http://localhost:5174", "http://localhost:5175"]
_extra_origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_default_origins + _extra_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = anthropic.AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


# ── Storage helpers ────────────────────────────────────────────────────────────

def upload_to_blob(file_bytes: bytes, filename: str) -> str:
    """Upload file to Azure Blob. Falls back to local folder when connection string is fake/missing."""
    conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
    container = os.getenv("AZURE_CONTAINER_NAME", "catalogues")

    if not conn_str or conn_str == "fake":
        folder = "test_output/uploads"
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, filename)
        with open(path, "wb") as f:
            f.write(file_bytes)
        return f"local://{path}"

    from azure.core.exceptions import ResourceExistsError
    from azure.storage.blob import BlobServiceClient

    blob_client = BlobServiceClient.from_connection_string(conn_str)
    container_client = blob_client.get_container_client(container)
    try:
        container_client.create_container()
        logger.info(f"Created missing blob container: {container}")
    except ResourceExistsError:
        pass

    blob = blob_client.get_blob_client(container=container, blob=filename)
    blob.upload_blob(file_bytes, overwrite=True)
    return blob.url


def download_bytes(url: str) -> bytes:
    if url.startswith("local://"):
        with open(url[len("local://"):], "rb") as f:
            return f.read()

    conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
    if conn_str and conn_str != "fake":
        # Blob URLs from upload_to_blob point at our own storage account, which denies
        # anonymous reads by default — fetch via the authenticated SDK instead of a bare GET.
        from azure.storage.blob import BlobServiceClient
        container = os.getenv("AZURE_CONTAINER_NAME", "catalogues")
        blob_name = unquote(url.rstrip("/").rsplit("/", 1)[-1])
        blob_client = BlobServiceClient.from_connection_string(conn_str)
        blob = blob_client.get_blob_client(container=container, blob=blob_name)
        return blob.download_blob().readall()

    with urllib.request.urlopen(url) as resp:
        return resp.read()


# ── PDF / image helpers ─────────────────────────────────────────────────────────

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


def crop_product_image(page_b64: str, crop: dict, page_w: int, page_h: int) -> Optional[str]:
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
    """Resize a data-URI image to a square thumbnail. Returns a data URI."""
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


def parse_json_response(raw_text: str):
    cleaned = clean_json_response(raw_text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        import json_repair
        return json_repair.loads(cleaned)


# ── Claude catalogue extraction (supplier + products, confidence, images) ──────

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


async def extract_catalogue(pdf_bytes: bytes) -> dict:
    """Send a catalogue PDF (+ rendered page images) to Claude and return supplier + products
    with per-field confidence and cropped/thumbnailed product images."""
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")

    pages = render_pdf_pages(pdf_bytes, scale=1.5)
    total_page_count = len(pages)
    pages = pages[:12]

    message_content = [
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
        data = parse_json_response(raw_text)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Claude response was cut off or malformed: {e}")
    except anthropic.APIError as e:
        raise HTTPException(status_code=502, detail=f"Claude API error: {e}")

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

    products = data.get("products", [])
    first_img = next((p["image"] for p in products if p.get("image")), None)
    cover_image = make_thumbnail(first_img, size=80) if first_img else None

    return {
        "supplier": supplier,
        "products": products,
        "page_count": total_page_count,
        "cover_image": cover_image,
    }


# ── API 1: Upload Catalogue ────────────────────────────────────────────────────

@app.post("/api/catalogues/upload", response_model=schema.CatalogueUploadResponse)
async def upload_catalogue(
    file:        UploadFile = File(...),
    supplier_id: Optional[str] = Form(None),
    category:    Optional[str] = Form(None),
    db:          Session    = Depends(get_db),
):
    """
    Upload a supplier PDF to cloud storage and create a Catalogue record.
    If supplier_id is omitted, a placeholder Supplier row is created immediately —
    its fields get filled in by /api/catalogues/process once Claude extracts them.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(file_bytes) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File exceeds 50 MB limit")

    file_hash = hashlib.sha256(file_bytes).hexdigest()
    existing = db.query(models.Catalogue).filter(models.Catalogue.file_hash == file_hash).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=(
                f"This exact file was already uploaded as catalogue {existing.id} "
                f"(supplier: {existing.supplier_id}, uploaded: {existing.uploaded_at})."
            ),
        )

    if supplier_id:
        supplier = db.query(models.Supplier).filter(models.Supplier.id == supplier_id).first()
        if not supplier:
            raise HTTPException(status_code=404, detail=f"Supplier {supplier_id} not found")
    else:
        supplier = models.Supplier(supplier_name=file.filename)
        db.add(supplier)
        db.flush()

    unique_name = f"{uuid.uuid4()}_{file.filename}"
    blob_url = upload_to_blob(file_bytes, unique_name)

    catalogue = models.Catalogue(
        catalogue_file_name=file.filename,
        catalogue_s3_url=blob_url,
        file_hash=file_hash,
        supplier_id=supplier.id,
        status="Uploaded",
        category=category,
        type="Product Catalogue",
    )
    db.add(catalogue)
    db.commit()
    db.refresh(catalogue)

    logger.info(f"Catalogue uploaded: {catalogue.id} | supplier: {supplier.id} | file: {file.filename}")

    return schema.CatalogueUploadResponse(
        catalogue_id=catalogue.id,
        supplier_id=catalogue.supplier_id,
        file_name=catalogue.catalogue_file_name,
        catalogue_s3_url=catalogue.catalogue_s3_url,
        category=catalogue.category,
        status=catalogue.status,
        uploaded_at=catalogue.uploaded_at,
    )


# ── API 2: Process Catalogue ───────────────────────────────────────────────────

@app.post("/api/catalogues/process", response_model=schema.CatalogueProcessResponse)
async def process_catalogue(
    body: schema.CatalogueProcessRequest,
    db:   Session = Depends(get_db),
):
    """
    Send stored catalogue PDF to Claude for extraction (supplier + products, confidence,
    cropped product images). Fills in the catalogue's placeholder supplier row.
    If already processed, returns cached result without calling Claude again.
    """
    catalogue = db.query(models.Catalogue).filter(models.Catalogue.id == body.catalogue_id).first()
    if not catalogue:
        raise HTTPException(status_code=404, detail=f"Catalogue {body.catalogue_id} not found")

    if catalogue.status == "Processed" and catalogue.raw_extraction:
        logger.info(f"Returning cached extraction for catalogue {catalogue.id}")
        cached = json.loads(catalogue.raw_extraction)
        return schema.CatalogueProcessResponse(
            catalogue_id=catalogue.id,
            supplier_id=catalogue.supplier_id,
            status=catalogue.status,
            page_count=catalogue.page_count or 0,
            cover_image=catalogue.cover_image,
            supplier=schema.SupplierExtracted(**cached["supplier"]),
            products=[schema.ProductExtracted(**p) for p in cached["products"]],
        )

    logger.info(f"Sending catalogue {catalogue.id} to Claude for extraction")
    pdf_bytes = download_bytes(body.catalogue_s3_url)
    extraction = await extract_catalogue(pdf_bytes)

    supplier = db.query(models.Supplier).filter(models.Supplier.id == catalogue.supplier_id).first()
    sup_data = extraction["supplier"]
    supplier.supplier_name = sup_data["name"] or supplier.supplier_name
    supplier.contact_person = sup_data["contact"] or None
    supplier.email = sup_data["email"] or None
    supplier.phone_number = sup_data["phone"] or None
    supplier.supplier_location = sup_data["location"] or None
    supplier.terms = sup_data["terms"] or None
    supplier.confidence = sup_data["conf"]

    catalogue.raw_extraction = json.dumps({"supplier": extraction["supplier"], "products": extraction["products"]})
    catalogue.status = "Processed"
    catalogue.catalogue_s3_url = body.catalogue_s3_url
    catalogue.page_count = extraction["page_count"]
    catalogue.cover_image = extraction["cover_image"]
    db.commit()
    db.refresh(catalogue)

    logger.info(f"Extraction complete: {len(extraction['products'])} products | catalogue {catalogue.id}")

    return schema.CatalogueProcessResponse(
        catalogue_id=catalogue.id,
        supplier_id=catalogue.supplier_id,
        status=catalogue.status,
        page_count=catalogue.page_count,
        cover_image=catalogue.cover_image,
        supplier=schema.SupplierExtracted(**extraction["supplier"]),
        products=[schema.ProductExtracted(**p) for p in extraction["products"]],
    )


# ── API 3: Add reviewed products to TempProduct ────────────────────────────────

@app.post("/api/products/temp-bulk", response_model=schema.AddProductsResponse)
def add_temp_products(
    body: schema.AddProductsRequest,
    db:   Session = Depends(get_db),
):
    """
    Persist the user-reviewed products (from the ReviewScreen "Approve & export" step)
    into the TempProduct staging table.
    """
    catalogue = db.query(models.Catalogue).filter(models.Catalogue.id == body.catalogue_id).first()
    if not catalogue:
        raise HTTPException(status_code=404, detail=f"Catalogue {body.catalogue_id} not found")

    saved = []
    errors = []

    for idx, product in enumerate(body.products):
        try:
            categories = product.categories or []
            temp = models.TempProduct(
                catalogue_id=body.catalogue_id,
                supplier_id=catalogue.supplier_id,
                product_name=product.name,
                product_code=product.sku or None,
                dealer_price=product.parsed_price(),
                description=product.specs or None,
                category=categories[0] if categories else None,
                sub_category=categories[1:] if len(categories) > 1 else [],
                features=[],
                ideal_keywords=[],
                source_page=None,
                currency=product.currency or "₹",
                moq=product.moq or None,
                lead_time=product.lead or None,
                thumbnail=product.thumbnail,
                confidence=product.conf or {},
                raw_json=product.model_dump(),
                status="Active",
            )
            db.add(temp)
            db.flush()
            saved.append(temp)

        except Exception as e:
            errors.append(f"{product.name}: {str(e)}")

    db.commit()
    for t in saved:
        db.refresh(t)

    logger.info(
        f"AddProducts: catalogue={body.catalogue_id} saved={len(saved)} rejected={len(errors)}"
    )

    return schema.AddProductsResponse(
        catalogue_id=body.catalogue_id,
        supplier_id=catalogue.supplier_id,
        saved=len(saved),
        rejected=len(errors),
        errors=errors,
        products=[schema.TempProductResponse.model_validate(t) for t in saved],
    )


# ── Catalogues: list / detail / status ─────────────────────────────────────────

def _temp_product_to_summary(p: models.TempProduct) -> schema.ProductSummary:
    categories = ([p.category] if p.category else []) + (p.sub_category or [])
    return schema.ProductSummary(
        id=p.id,
        name=p.product_name,
        sku=p.product_code or "",
        price=p.dealer_price,
        currency=p.currency or "₹",
        moq=p.moq or "",
        lead=p.lead_time or "",
        specs=p.description or "",
        categories=categories,
        image=p.thumbnail,
        thumbnail=p.thumbnail,
    )


def _catalogue_to_summary(c: models.Catalogue, products: list[models.TempProduct]) -> schema.CatalogueSummary:
    ts = c.uploaded_at or c.created_at
    return schema.CatalogueSummary(
        id=c.id,
        file=c.catalogue_file_name,
        uploadedAt=int(ts.timestamp() * 1000) if ts else 0,
        pageCount=c.page_count,
        status=c.status,
        coverImage=c.cover_image,
        supplier=schema.SupplierSummary(
            name=c.supplier.supplier_name or "",
            location=c.supplier.supplier_location or "",
            email=c.supplier.email or "",
            terms=c.supplier.terms or "",
        ),
        products=[_temp_product_to_summary(p) for p in products],
    )


@app.get("/api/catalogues", response_model=list[schema.CatalogueSummary])
def list_catalogues(db: Session = Depends(get_db)):
    catalogues = db.query(models.Catalogue).order_by(models.Catalogue.uploaded_at.desc()).all()
    result = []
    for c in catalogues:
        products = (
            db.query(models.TempProduct)
            .filter(models.TempProduct.catalogue_id == c.id, models.TempProduct.status == "Active")
            .all()
        )
        result.append(_catalogue_to_summary(c, products))
    return result


@app.get("/api/catalogues/{catalogue_id}", response_model=schema.CatalogueSummary)
def get_catalogue(catalogue_id: str, db: Session = Depends(get_db)):
    catalogue = db.query(models.Catalogue).filter(models.Catalogue.id == catalogue_id).first()
    if not catalogue:
        raise HTTPException(status_code=404, detail="Catalogue not found")
    products = (
        db.query(models.TempProduct)
        .filter(models.TempProduct.catalogue_id == catalogue_id, models.TempProduct.status == "Active")
        .all()
    )
    return _catalogue_to_summary(catalogue, products)


@app.get("/api/catalogues/{catalogue_id}/download")
def download_catalogue(catalogue_id: str, db: Session = Depends(get_db)):
    catalogue = db.query(models.Catalogue).filter(models.Catalogue.id == catalogue_id).first()
    if not catalogue:
        raise HTTPException(status_code=404, detail="Catalogue not found")
    if not catalogue.catalogue_s3_url:
        raise HTTPException(status_code=404, detail="No original file stored for this catalogue")

    pdf_bytes = download_bytes(catalogue.catalogue_s3_url)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{catalogue.catalogue_file_name}"'},
    )


@app.patch("/api/catalogues/{catalogue_id}")
def update_catalogue_status(catalogue_id: str, body: schema.CatalogueStatusUpdate, db: Session = Depends(get_db)):
    catalogue = db.query(models.Catalogue).filter(models.Catalogue.id == catalogue_id).first()
    if not catalogue:
        raise HTTPException(status_code=404, detail="Catalogue not found")
    catalogue.status = body.status
    db.commit()
    return {"id": catalogue.id, "status": catalogue.status}


# ── Price lists ──────────────────────────────────────────────────────────────────

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


def match_and_update_products(db: Session, pl_products: list[dict]) -> list[dict]:
    """
    For each price-list product, find TempProduct rows with missing price and update them.
    Match priority: exact product_code (SKU) > name word-overlap ≥ 60%.
    Returns list of update records.
    """
    all_products = (
        db.query(models.TempProduct)
        .filter(models.TempProduct.status == "Active")
        .join(models.Catalogue, models.TempProduct.catalogue_id == models.Catalogue.id)
        .all()
    )
    updates: list[dict] = []

    sku_map: dict[str, list[models.TempProduct]] = {}
    for prod in all_products:
        sku = (prod.product_code or "").strip().upper()
        if sku:
            sku_map.setdefault(sku, []).append(prod)

    for pl_item in pl_products:
        new_price_str = (pl_item.get("price") or "").strip()
        new_currency = (pl_item.get("currency") or "").strip()
        new_moq = (pl_item.get("moq") or "").strip()
        if not new_price_str:
            continue
        try:
            new_price = float(new_price_str)
        except ValueError:
            continue

        pl_sku = (pl_item.get("sku") or "").strip().upper()
        pl_words = _name_words(pl_item.get("name", ""))

        candidates: list[tuple[models.TempProduct, str]] = []

        if pl_sku and pl_sku in sku_map:
            candidates.extend((prod, "sku") for prod in sku_map[pl_sku])

        if not candidates and pl_words:
            for prod in all_products:
                prod_words = _name_words(prod.product_name or "")
                if not prod_words:
                    continue
                overlap = len(pl_words & prod_words)
                ratio = overlap / min(len(pl_words), len(prod_words))
                if ratio >= 0.60:
                    candidates.append((prod, "name"))

        for prod, match_type in candidates:
            if prod.dealer_price is not None:
                continue

            prod.dealer_price = new_price
            if new_currency and not (prod.currency or "").strip():
                prod.currency = new_currency
            if new_moq and not (prod.moq or "").strip():
                prod.moq = new_moq

            updates.append({
                "catalogueId": prod.catalogue_id,
                "catalogueFile": prod.catalogue.catalogue_file_name if prod.catalogue else "",
                "productId": prod.id,
                "productName": prod.product_name,
                "oldPrice": None,
                "newPrice": new_price,
                "currency": prod.currency or new_currency or "₹",
                "matchType": match_type,
            })

    db.commit()
    return updates


@app.post("/api/pricelists/upload", response_model=schema.PriceListResult)
async def upload_pricelist(file: UploadFile = File(...), db: Session = Depends(get_db)):
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
        data = parse_json_response(raw_text)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse price list response: {e}")
    except anthropic.APIError as e:
        raise HTTPException(status_code=502, detail=f"Claude API error: {e}")

    pl_products = data.get("products", [])
    supplier_name = data.get("supplier_name", "")

    updates = match_and_update_products(db, pl_products)

    price_list = models.PriceList(
        file_name=file.filename,
        supplier_name=supplier_name,
        products_extracted=len(pl_products),
        updates=updates,
    )
    db.add(price_list)
    db.commit()
    db.refresh(price_list)

    return schema.PriceListResult(
        id=price_list.id,
        file=price_list.file_name,
        uploadedAt=int(price_list.uploaded_at.timestamp() * 1000),
        supplierName=price_list.supplier_name or "",
        productsExtracted=price_list.products_extracted or 0,
        updates=updates,
    )


@app.get("/api/pricelists", response_model=list[schema.PriceListResult])
def list_pricelists(db: Session = Depends(get_db)):
    rows = db.query(models.PriceList).order_by(models.PriceList.uploaded_at.desc()).all()
    return [
        schema.PriceListResult(
            id=r.id,
            file=r.file_name,
            uploadedAt=int(r.uploaded_at.timestamp() * 1000),
            supplierName=r.supplier_name or "",
            productsExtracted=r.products_extracted or 0,
            updates=r.updates or [],
        )
        for r in rows
    ]


# ── Combinations ───────────────────────────────────────────────────────────────

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
async def find_combinations(body: schema.CombinationsRequest, db: Session = Depends(get_db)):
    rows = (
        db.query(models.TempProduct, models.Supplier.supplier_name)
        .join(models.Supplier, models.TempProduct.supplier_id == models.Supplier.id)
        .filter(models.TempProduct.status == "Active", models.TempProduct.dealer_price.isnot(None))
        .all()
    )

    all_products = []
    for prod, supplier_name in rows:
        categories = ([prod.category] if prod.category else []) + (prod.sub_category or [])
        all_products.append({
            "productId": prod.id,
            "catalogId": prod.catalogue_id,
            "name": prod.product_name,
            "price": prod.dealer_price,
            "currency": prod.currency or "₹",
            "categories": categories,
            "supplier": supplier_name or "Unknown",
            "thumbnail": prod.thumbnail,
        })

    if not all_products:
        raise HTTPException(status_code=400, detail="No priced products found. Upload and approve some catalogues first.")

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
        data = parse_json_response(raw_text)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse combinations response: {e}")
    except anthropic.APIError as e:
        raise HTTPException(status_code=502, detail=f"Claude API error: {e}")

    thumbnail_map = {(p["productId"], p["catalogId"]): p.get("thumbnail") for p in all_products}
    for combo in data.get("combinations", []):
        for prod in combo.get("products", []):
            key = (prod.get("productId"), prod.get("catalogId"))
            prod["thumbnail"] = thumbnail_map.get(key)

    return data


# ── Brochure generation ────────────────────────────────────────────────────────

def _decode_thumbnail(data_uri: Optional[str]) -> Optional[Image.Image]:
    """Decode a data URI thumbnail into a PIL Image, or return None."""
    if not data_uri or not data_uri.startswith("data:"):
        return None
    try:
        _header, b64data = data_uri.split(",", 1)
        raw = base64.standard_b64decode(b64data)
        return Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception:
        return None


def _draw_rounded_rect(c: rl_canvas.Canvas, x: float, y: float, w: float, h: float,
                        r: float, fill_color: HexColor, stroke_color: Optional[HexColor] = None):
    p = c.beginPath()
    p.roundRect(x, y, w, h, r)
    c.setFillColor(fill_color)
    if stroke_color:
        c.setStrokeColor(stroke_color)
        c.drawPath(p, fill=1, stroke=1)
    else:
        c.drawPath(p, fill=1, stroke=0)


def generate_brochure_pdf(req: schema.BrochureRequest) -> bytes:
    """Generate a warm-luxury styled PDF brochure for a product combination."""
    buf = io.BytesIO()
    PAGE_W, PAGE_H = A4  # 595.27 x 841.89 pts
    MARGIN = 36 * pt  # ~12.7mm

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

    c.setFillColor(CREAM)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    BAND_H = 6 * pt
    c.setFillColor(BROWN_DARK)
    c.rect(0, PAGE_H - BAND_H, PAGE_W, BAND_H, fill=1, stroke=0)

    c.setStrokeColor(GOLD)
    c.setLineWidth(0.8)
    c.line(MARGIN, PAGE_H - BAND_H - 6, PAGE_W - MARGIN, PAGE_H - BAND_H - 6)

    HEADER_TOP = PAGE_H - BAND_H - 28 * pt

    c.setFont("Times-Bold", 28)
    c.setFillColor(BROWN_DARK)
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
    for text_line in lines:
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

    y_cursor -= 4 * pt
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.7)
    rule_y = y_cursor + 6 * pt
    c.line(MARGIN, rule_y, PAGE_W - MARGIN, rule_y)
    mid_x = PAGE_W / 2
    c.setFillColor(GOLD)
    c.circle(mid_x, rule_y, 2.5, fill=1, stroke=0)
    y_cursor -= 6 * pt

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

    COLS = 2
    GUTTER = 12 * pt
    CARD_W = (PAGE_W - 2 * MARGIN - GUTTER) / 2
    IMG_SIZE = 56 * pt
    CARD_H = IMG_SIZE + 24 * pt

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

            _draw_rounded_rect(c, card_x, card_y, CARD_W, CARD_H, 6 * pt, CARD_BG, CARD_BORDER)

            img_pad = 10 * pt
            img_x = card_x + img_pad
            img_y = card_y + (CARD_H - IMG_SIZE) / 2
            thumb_pil = _decode_thumbnail(p.thumbnail)
            if thumb_pil:
                thumb_pil.thumbnail((int(IMG_SIZE), int(IMG_SIZE)), Image.LANCZOS)
                img_buf = io.BytesIO()
                thumb_pil.save(img_buf, format="JPEG", quality=85)
                img_buf.seek(0)
                c.saveState()
                c.drawImage(ImageReader(img_buf), img_x, img_y, IMG_SIZE, IMG_SIZE,
                            preserveAspectRatio=True, anchor="c", mask="auto")
                c.restoreState()
            else:
                c.setFillColor(GOLD_LIGHT)
                c.rect(img_x, img_y, IMG_SIZE, IMG_SIZE, fill=1, stroke=0)
                c.setFillColor(RULE_COLOR)
                c.setFont("Helvetica", 8)
                c.drawCentredString(img_x + IMG_SIZE / 2, img_y + IMG_SIZE / 2 - 4, "No image")

            text_x = img_x + IMG_SIZE + 8 * pt
            text_max_w = CARD_W - IMG_SIZE - img_pad - 8 * pt - 8 * pt
            text_y = card_y + CARD_H - 16 * pt

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
            for nl_line in name_lines[:2]:
                c.drawString(text_x, text_y, nl_line)
                text_y -= 13 * pt

            c.setFont("Helvetica", 8.5)
            c.setFillColor(MUTED)
            supplier_text = p.supplier[:28] + "…" if len(p.supplier) > 28 else p.supplier
            c.drawString(text_x, text_y, supplier_text)
            text_y -= 13 * pt

            if p.categories:
                cat_text = p.categories[0]
                tag_w = c.stringWidth(cat_text, "Helvetica", 7.5) + 8 * pt
                _draw_rounded_rect(c, text_x, text_y - 2 * pt, tag_w, 12 * pt, 3 * pt, GOLD_LIGHT)
                c.setFillColor(GOLD)
                c.setFont("Helvetica", 7.5)
                c.drawString(text_x + 4 * pt, text_y + 1 * pt, cat_text)
                text_y -= 15 * pt

            price_val = p.price * p.quantity
            price_text = f"{p.currency}{price_val:,.0f}"
            if p.quantity > 1:
                price_text += f"  ×{p.quantity}"
            c.setFont("Helvetica-Bold", 13)
            c.setFillColor(GOLD)
            c.drawString(text_x, card_y + 10 * pt, price_text)

        y_cursor -= CARD_H + 10 * pt

    FOOTER_H = 48 * pt
    footer_y = 0

    c.setFillColor(FOOTER_BG)
    c.rect(0, footer_y, PAGE_W, FOOTER_H, fill=1, stroke=0)
    c.setStrokeColor(RULE_COLOR)
    c.setLineWidth(0.8)
    c.line(0, FOOTER_H, PAGE_W, FOOTER_H)

    c.setFont("Times-Bold", 18)
    c.setFillColor(BROWN_DARK)
    c.drawString(MARGIN, FOOTER_H - 28 * pt, "Total")
    total_value = f"{req.currency}{req.total:,.0f}"
    c.setFillColor(GOLD)
    c.drawRightString(PAGE_W - MARGIN, FOOTER_H - 28 * pt, total_value)

    c.setFont("Helvetica", 8.5)
    c.setFillColor(MUTED)
    count_text = f"{len(req.products)} product{'s' if len(req.products) != 1 else ''} · Curated by Intake"
    c.drawString(MARGIN, FOOTER_H - 40 * pt, count_text)

    c.setFillColor(BROWN_DARK)
    c.rect(0, 0, PAGE_W, 4 * pt, fill=1, stroke=0)

    c.save()
    return buf.getvalue()


@app.post("/api/catalogues/generate-brochure")
async def generate_brochure(req: schema.BrochureRequest):
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


# ── Health ─────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0"}


# ── Supplier helpers ───────────────────────────────────────────────────────────

@app.post("/api/suppliers", response_model=schema.SupplierResponse)
def create_supplier(body: schema.SupplierCreate, db: Session = Depends(get_db)):
    supplier = models.Supplier(**body.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier

@app.get("/api/suppliers/{supplier_id}", response_model=schema.SupplierResponse)
def get_supplier(supplier_id: str, db: Session = Depends(get_db)):
    supplier = db.query(models.Supplier).filter(models.Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier
