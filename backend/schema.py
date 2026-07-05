from pydantic import BaseModel, field_validator, model_validator
from typing import Optional, List, Any, Dict
from datetime import datetime


# ── Supplier ──────────────────────────────────────────────────────────────────

class SupplierCreate(BaseModel):
    supplier_name:     str
    supplier_location: Optional[str] = None
    city:              Optional[str] = None
    state:             Optional[str] = None
    phone_number:      Optional[str] = None
    email:             Optional[str] = None
    gst_number:        Optional[str] = None
    contact_person:    Optional[str] = None
    terms:             Optional[str] = None

class SupplierResponse(BaseModel):
    id:                str
    supplier_name:     str
    supplier_location: Optional[str]
    city:              Optional[str]
    state:             Optional[str]
    phone_number:      Optional[str]
    email:             Optional[str]
    gst_number:        Optional[str]
    contact_person:    Optional[str]
    terms:             Optional[str]
    confidence:        Optional[Any]
    created_at:        datetime
    updated_at:        datetime
    class Config:
        from_attributes = True


# ── Catalogue ─────────────────────────────────────────────────────────────────

class CatalogueUploadResponse(BaseModel):
    catalogue_id:     str
    supplier_id:      str
    file_name:        str
    catalogue_s3_url: Optional[str]
    category:         Optional[str]
    status:           str
    uploaded_at:      datetime
    class Config:
        from_attributes = True

class CatalogueProcessRequest(BaseModel):
    catalogue_id:     str
    catalogue_s3_url: str


class SupplierExtracted(BaseModel):
    """Supplier info as extracted by Claude — same shape the frontend's ReviewScreen renders."""
    name:     str = ""
    contact:  str = ""
    email:    str = ""
    phone:    str = ""
    location: str = ""
    terms:    str = ""
    conf:     Dict[str, str] = {}

class ProductExtracted(BaseModel):
    """A single extracted product — same shape the frontend's ReviewScreen/CataloguesScreen render."""
    id:         str
    name:       str = ""
    sku:        str = ""
    price:      str = ""
    currency:   str = ""
    moq:        str = ""
    specs:      str = ""
    lead:       str = ""
    categories: List[str] = []
    conf:       Dict[str, str] = {}
    image:      Optional[str] = None
    thumbnail:  Optional[str] = None
    reviewed:   bool = False

class CatalogueProcessResponse(BaseModel):
    catalogue_id: str
    supplier_id:  str
    status:       str
    page_count:   int
    cover_image:  Optional[str] = None
    supplier:     SupplierExtracted
    products:     List[ProductExtracted]


class CatalogueStatusUpdate(BaseModel):
    status: str

class ProductSummary(BaseModel):
    """A persisted TempProduct shaped for the catalogue list/detail screens."""
    id:         str
    name:       str
    sku:        Optional[str] = ""
    price:      Optional[float] = None
    currency:   Optional[str] = "₹"
    moq:        Optional[str] = ""
    lead:       Optional[str] = ""
    specs:      Optional[str] = ""
    categories: List[str] = []
    image:      Optional[str] = None
    thumbnail:  Optional[str] = None

class SupplierSummary(BaseModel):
    name:     str = ""
    location: str = ""
    email:    str = ""
    terms:    str = ""

class CatalogueSummary(BaseModel):
    id:          str
    file:        str
    uploadedAt:  int
    pageCount:   Optional[int] = None
    status:      str
    coverImage:  Optional[str] = None
    supplier:    SupplierSummary
    products:    List[ProductSummary]


# ── TempProduct ───────────────────────────────────────────────────────────────

class TempProductItem(BaseModel):
    """A reviewed product from the frontend — input to API 3 (temp-bulk save)."""
    name:       str
    sku:        Optional[str]       = ""
    price:      Optional[str]       = ""
    currency:   Optional[str]       = "₹"
    moq:        Optional[str]       = ""
    lead:       Optional[str]       = ""
    specs:      Optional[str]       = ""
    categories: Optional[List[str]] = []
    image:      Optional[str]       = None
    thumbnail:  Optional[str]       = None
    conf:       Optional[Dict[str, str]] = {}

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("name cannot be empty")
        return v.strip()

    @field_validator("price", mode="before")
    @classmethod
    def price_to_string(cls, v):
        return "" if v is None else str(v)

    def parsed_price(self) -> Optional[float]:
        try:
            val = float(self.price)
        except (TypeError, ValueError):
            return None
        if val < 0:
            raise ValueError("price cannot be negative")
        return val

class AddProductsRequest(BaseModel):
    catalogue_id: str
    products:     List[TempProductItem]

class TempProductResponse(BaseModel):
    id:            str
    catalogue_id:  str
    supplier_id:   str
    product_name:  str
    product_code:  Optional[str]
    dealer_price:  Optional[float]
    mrp:           Optional[float]
    description:   Optional[str]
    category:      Optional[str]
    sub_category:  Optional[Any]
    features:      Optional[Any]
    ideal_keywords: Optional[Any]
    source_page:   Optional[int]
    currency:      Optional[str]
    moq:           Optional[str]
    lead_time:     Optional[str]
    thumbnail:     Optional[str]
    confidence:    Optional[Any]
    raw_json:      Optional[Any]
    status:        str
    created_at:    datetime
    class Config:
        from_attributes = True

class AddProductsResponse(BaseModel):
    catalogue_id:   str
    supplier_id:    str
    saved:          int
    rejected:       int
    errors:         List[str]
    products:       List[TempProductResponse]


# ── Category ──────────────────────────────────────────────────────────────────

class CategoryCreate(BaseModel):
    category:       str
    sub_categories: Optional[List[str]] = []

class CategoryResponse(BaseModel):
    id:             str
    category:       str
    sub_categories: Optional[Any]
    created_at:     datetime
    class Config:
        from_attributes = True


# ── Price lists ───────────────────────────────────────────────────────────────

class PriceListUpdate(BaseModel):
    catalogueId:   str
    catalogueFile: str
    productId:     str
    productName:   str
    oldPrice:      Optional[float] = None
    newPrice:      float
    currency:      str
    matchType:     str   # "sku" | "name"

class PriceListResult(BaseModel):
    id:                str
    file:              str
    uploadedAt:        int
    supplierName:      str
    productsExtracted: int
    updates:           List[PriceListUpdate]


# ── Combinations ──────────────────────────────────────────────────────────────
# Note: the response is Claude's raw JSON dict, returned unvalidated (no response_model)
# so a slightly malformed LLM response doesn't 500 the request — only the input is typed.

class CombinationsRequest(BaseModel):
    query: str


# ── Brochure ──────────────────────────────────────────────────────────────────

class BrochureProduct(BaseModel):
    name:       str
    price:      float
    currency:   str = "₹"
    quantity:   int = 1
    supplier:   str = ""
    categories: List[str] = []
    thumbnail:  Optional[str] = None

class BrochureRequest(BaseModel):
    title:       str
    description: str = ""
    currency:    str = "₹"
    total:       float
    products:    List[BrochureProduct]
