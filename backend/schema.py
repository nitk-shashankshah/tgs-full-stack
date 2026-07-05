from pydantic import BaseModel, field_validator, model_validator
from typing import Optional, List, Any
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

class SupplierResponse(BaseModel):
    id:                str
    supplier_name:     str
    supplier_location: Optional[str]
    city:              Optional[str]
    state:             Optional[str]
    phone_number:      Optional[str]
    email:             Optional[str]
    gst_number:        Optional[str]
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
    uploaded_at:    datetime
    class Config:
        from_attributes = True

class CatalogueProcessRequest(BaseModel):
    catalogue_id:     str
    catalogue_s3_url: str

class CatalogueProcessResponse(BaseModel):
    catalogue_id: str
    supplier_id:  str
    status:       str
    products:     List[Any]   # raw extracted product list from Claude


# ── TempProduct ───────────────────────────────────────────────────────────────

class TempProductItem(BaseModel):
    """Schema for a single product — used both in API 3 input and as validator."""
    product_name:   str
    product_code:   Optional[str]       = None
    dealer_price:   Optional[float]     = None
    mrp:            Optional[float]     = None
    description:    Optional[str]       = None
    category:       Optional[str]       = None
    sub_category:   Optional[List[str]] = []
    features:       Optional[List[str]] = []
    ideal_keywords: Optional[List[str]] = []
    source_page:    Optional[int]       = None

    @field_validator("product_name")
    @classmethod
    def name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("product_name cannot be empty")
        return v.strip()

    @field_validator("dealer_price", "mrp")
    @classmethod
    def price_positive(cls, v):
        if v is not None and v < 0:
            raise ValueError("price cannot be negative")
        return v

    @model_validator(mode="after")
    def mrp_gte_dealer(self):
        if self.dealer_price and self.mrp and self.mrp < self.dealer_price:
            raise ValueError("mrp cannot be less than dealer_price")
        return self

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
