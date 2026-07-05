import os
import uuid
import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import get_db, engine
import models
import schema

models.Base.metadata.create_all(bind=engine)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="TGS Catalogue API", version="2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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

    from azure.storage.blob import BlobServiceClient
    client = BlobServiceClient.from_connection_string(conn_str)
    blob = client.get_blob_client(container=container, blob=filename)
    blob.upload_blob(file_bytes, overwrite=True)
    return blob.url


# ── Claude extraction helper ───────────────────────────────────────────────────

EXTRACTION_PROMPT = """You are a product data extraction assistant.
Extract all products from this catalogue PDF page by page.

For each product return a JSON object with these fields:
- product_name (string, required)
- product_code (string or null)
- dealer_price (number or null)
- mrp (number or null)
- description (string or null)
- category (string or null)
- sub_category (list of strings, default [])
- features (list of strings, default [])
- ideal_keywords (list of strings, default [])
- source_page (integer, the page number)

Rules:
- Skip supplier names, headers, footers, contact info, and page decorations
- Skip items with no product_name
- Do NOT invent prices — leave null if not clearly stated
- Return ONLY a JSON array of product objects, no explanation
"""

def extract_products_from_pdf(pdf_url: str) -> list:
    """Download PDF from URL and send to Claude for extraction."""
    import anthropic
    import urllib.request
    import base64

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    # Download PDF bytes
    if pdf_url.startswith("local://"):
        local_path = pdf_url[len("local://"):]
        with open(local_path, "rb") as f:
            pdf_bytes = f.read()
    else:
        with urllib.request.urlopen(pdf_url) as resp:
            pdf_bytes = resp.read()

    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=8192,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_b64,
                        },
                    },
                    {"type": "text", "text": EXTRACTION_PROMPT},
                ],
            }
        ],
    )

    raw_text = response.content[0].text.strip()

    # Strip markdown code fences if present
    if "```" in raw_text:
        raw_text = raw_text.split("```", 1)[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.rsplit("```", 1)[0]

    # Extract JSON array — find first [ and last ]
    start = raw_text.find("[")
    end = raw_text.rfind("]")
    if start == -1 or end == -1:
        raise ValueError("No JSON array found in Claude response")
    raw_text = raw_text[start:end+1]

    try:
        products = json.loads(raw_text)
    except json.JSONDecodeError:
        # Claude sometimes emits unescaped quotes inside strings — use json_repair as fallback
        try:
            import json_repair
            products = json_repair.loads(raw_text)
        except Exception:
            raise ValueError("Could not parse Claude response as JSON")

    if not isinstance(products, list):
        raise ValueError("Claude did not return a JSON array")
    return products


# ── API 1: Upload Catalogue ────────────────────────────────────────────────────

@app.post("/api/catalogues/upload", response_model=schema.CatalogueUploadResponse)
async def upload_catalogue(
    file:        UploadFile = File(...),
    supplier_id: str        = Form(...),
    category:    Optional[str] = Form(None),
    db:          Session    = Depends(get_db),
):
    """
    Upload a supplier PDF to cloud storage and create a Catalogue record.
    Returns catalogue_id, supplier_id, status, and upload timestamp.
    """
    supplier = db.query(models.Supplier).filter(models.Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail=f"Supplier {supplier_id} not found")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    unique_name = f"{uuid.uuid4()}_{file.filename}"
    blob_url = upload_to_blob(file_bytes, unique_name)

    catalogue = models.Catalogue(
        catalogue_file_name=file.filename,
        catalogue_s3_url=blob_url,
        supplier_id=supplier_id,
        status="Uploaded",
        category=category,
        type="Product Catalogue",
    )
    db.add(catalogue)
    db.commit()
    db.refresh(catalogue)

    logger.info(f"Catalogue uploaded: {catalogue.id} | supplier: {supplier_id} | file: {file.filename}")

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
def process_catalogue(
    body: schema.CatalogueProcessRequest,
    db:   Session = Depends(get_db),
):
    """
    Send stored catalogue PDF to Claude for extraction.
    Saves raw JSON string to Catalogue.raw_extraction.
    Returns extracted product list — pass this directly to API 3.
    If already processed, returns cached result without calling Claude again.
    """
    catalogue = db.query(models.Catalogue).filter(models.Catalogue.id == body.catalogue_id).first()
    if not catalogue:
        raise HTTPException(status_code=404, detail=f"Catalogue {body.catalogue_id} not found")

    if catalogue.status == "Processed" and catalogue.raw_extraction:
        logger.info(f"Returning cached extraction for catalogue {catalogue.id}")
        products = json.loads(catalogue.raw_extraction)
        return schema.CatalogueProcessResponse(
            catalogue_id=catalogue.id,
            supplier_id=catalogue.supplier_id,
            status=catalogue.status,
            products=products,
        )

    logger.info(f"Sending catalogue {catalogue.id} to Claude for extraction")
    products = extract_products_from_pdf(body.catalogue_s3_url)

    catalogue.raw_extraction = json.dumps(products)
    catalogue.status = "Processed"
    catalogue.catalogue_s3_url = body.catalogue_s3_url
    db.commit()
    db.refresh(catalogue)

    logger.info(f"Extraction complete: {len(products)} products | catalogue {catalogue.id}")

    return schema.CatalogueProcessResponse(
        catalogue_id=catalogue.id,
        supplier_id=catalogue.supplier_id,
        status=catalogue.status,
        products=products,
    )


# ── API 3: Add Products to TempProduct ────────────────────────────────────────

@app.post("/api/products/temp-bulk", response_model=schema.AddProductsResponse)
def add_temp_products(
    body: schema.AddProductsRequest,
    db:   Session = Depends(get_db),
):
    """
    Validate and save extracted products to TempProduct staging table.
    Input: catalogue_id + products list (matches output of /api/catalogues/process).
    Valid products saved as Active. Invalid ones returned in errors list.
    """
    catalogue = db.query(models.Catalogue).filter(models.Catalogue.id == body.catalogue_id).first()
    if not catalogue:
        raise HTTPException(status_code=404, detail=f"Catalogue {body.catalogue_id} not found")

    saved = []
    errors = []

    for idx, product in enumerate(body.products):
        try:
            temp = models.TempProduct(
                catalogue_id=body.catalogue_id,
                supplier_id=catalogue.supplier_id,
                product_name=product.product_name.strip(),
                product_code=product.product_code,
                dealer_price=product.dealer_price,
                mrp=product.mrp,
                description=product.description,
                category=product.category,
                sub_category=product.sub_category or [],
                features=product.features or [],
                ideal_keywords=product.ideal_keywords or [],
                source_page=product.source_page,
                raw_json=product.model_dump(),
                status="Active",
            )
            db.add(temp)
            db.flush()
            saved.append(temp)

        except Exception as e:
            name = getattr(product, "product_name", f"item_{idx}")
            errors.append(f"{name}: {str(e)}")

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
