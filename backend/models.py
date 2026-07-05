import uuid
import enum
from datetime import datetime
from sqlalchemy import (
    Column, String, Float, Integer, Text,
    Boolean, DateTime, ForeignKey, Index
)
from sqlalchemy import JSON
from sqlalchemy.orm import relationship
from database import Base


def _default_uuid():
    return str(uuid.uuid4())


class Supplier(Base):
    __tablename__ = "suppliers"

    id                = Column(String(36), primary_key=True, default=_default_uuid)
    supplier_name     = Column(String(255), nullable=False)
    supplier_location = Column(String(255))
    city              = Column(String(100))
    state             = Column(String(100))
    phone_number      = Column(String(20))
    email             = Column(String(255))
    gst_number        = Column(String(20))
    contact_person    = Column(String(255))
    terms             = Column(String(255))
    confidence        = Column(JSON)   # per-field confidence: {name, contact, email, phone, location, terms}
    created_at        = Column(DateTime, default=datetime.utcnow)
    updated_at        = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    catalogues  = relationship("Catalogue", back_populates="supplier")
    products    = relationship("Product", back_populates="supplier")
    temp_products = relationship("TempProduct", back_populates="supplier")


class Catalogue(Base):
    __tablename__ = "catalogues"

    id                     = Column(String(36), primary_key=True, default=_default_uuid)
    catalogue_file_name    = Column(String(255), nullable=False)
    catalogue_s3_url       = Column(Text)
    file_hash              = Column(String(64), unique=True, index=True, nullable=True)
    supplier_id            = Column(String(36), ForeignKey("suppliers.id"), nullable=False)
    status                 = Column(String(20), default="Uploaded")   # Uploaded | Processed
    category               = Column(String(100))
    type                   = Column(String(30), nullable=False, default="Product Catalogue")
    reference_catalogue_id = Column(String(36), ForeignKey("catalogues.id"), nullable=True)
    raw_extraction         = Column(Text)    # raw Claude JSON response stored as string
    page_count             = Column(Integer)
    cover_image            = Column(Text)    # base64 data URI thumbnail of first product image
    uploaded_at            = Column(DateTime, default=datetime.utcnow)
    created_at             = Column(DateTime, default=datetime.utcnow)
    updated_at             = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    supplier            = relationship("Supplier", back_populates="catalogues")
    reference_catalogue = relationship("Catalogue", remote_side="Catalogue.id",
                                       foreign_keys=[reference_catalogue_id])
    temp_products       = relationship("TempProduct", back_populates="catalogue")
    products            = relationship("Product", back_populates="catalogue")


class TempProduct(Base):
    """Staging table — products land here after API 3, promoted to Product later."""
    __tablename__ = "temp_products"

    id             = Column(String(36), primary_key=True, default=_default_uuid)
    catalogue_id   = Column(String(36), ForeignKey("catalogues.id"), nullable=False)
    supplier_id    = Column(String(36), ForeignKey("suppliers.id"), nullable=False)
    product_name   = Column(String(255), nullable=False)
    product_code   = Column(String(100))
    dealer_price   = Column(Float)
    mrp            = Column(Float)
    description    = Column(Text)
    category       = Column(String(100))
    sub_category   = Column(JSON)
    features       = Column(JSON)
    ideal_keywords = Column(JSON)
    source_page    = Column(Integer)
    currency       = Column(String(5), default="₹")
    moq            = Column(String(50))
    lead_time      = Column(String(50))
    thumbnail      = Column(Text)   # base64 data URI
    confidence     = Column(JSON)   # per-field confidence: {name, sku, price, moq, specs}
    raw_json       = Column(JSON)   # full product JSON from Claude extraction
    status         = Column(String(10), default="Active")   # Active | Inactive
    created_at     = Column(DateTime, default=datetime.utcnow)
    updated_at     = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    catalogue = relationship("Catalogue", back_populates="temp_products")
    supplier  = relationship("Supplier", back_populates="temp_products")

    __table_args__ = (
        Index("ix_temp_products_catalogue_id", "catalogue_id"),
        Index("ix_temp_products_supplier_id", "supplier_id"),
        Index("ix_temp_products_category", "category"),
        Index("ix_temp_products_dealer_price", "dealer_price"),
        Index("ix_temp_products_mrp", "mrp"),
        Index("ix_temp_products_status", "status"),
    )


class Product(Base):
    """Final product table — promoted from TempProduct after review."""
    __tablename__ = "products"

    id             = Column(String(36), primary_key=True, default=_default_uuid)
    catalogue_id   = Column(String(36), ForeignKey("catalogues.id"), nullable=False)
    supplier_id    = Column(String(36), ForeignKey("suppliers.id"), nullable=False)
    product_name   = Column(String(255), nullable=False)
    product_code   = Column(String(100))
    dealer_price   = Column(Float)
    mrp            = Column(Float)
    description    = Column(Text)
    category       = Column(String(100))
    sub_category   = Column(JSON)
    features       = Column(JSON)
    ideal_keywords = Column(JSON)
    source_page    = Column(Integer)
    currency       = Column(String(5), default="₹")
    moq            = Column(String(50))
    lead_time      = Column(String(50))
    thumbnail      = Column(Text)   # base64 data URI
    confidence     = Column(JSON)   # per-field confidence: {name, sku, price, moq, specs}
    embedding      = Column(Text)   # JSON string; replaced with Vector(1024) on PostgreSQL
    created_at     = Column(DateTime, default=datetime.utcnow)
    updated_at     = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    catalogue = relationship("Catalogue", back_populates="products")
    supplier  = relationship("Supplier", back_populates="products")

    __table_args__ = (
        Index("ix_products_catalogue_id", "catalogue_id"),
        Index("ix_products_supplier_id", "supplier_id"),
        Index("ix_products_category", "category"),
        Index("ix_products_dealer_price", "dealer_price"),
        Index("ix_products_mrp", "mrp"),
    )


class CategoryDetails(Base):
    __tablename__ = "category_details"

    id             = Column(String(36), primary_key=True, default=_default_uuid)
    category       = Column(String(100), nullable=False, unique=True)
    sub_categories = Column(JSON)
    created_at     = Column(DateTime, default=datetime.utcnow)
    updated_at     = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PriceList(Base):
    """A single price-list PDF upload and the catalogue product updates it produced."""
    __tablename__ = "price_lists"

    id                 = Column(String(36), primary_key=True, default=_default_uuid)
    file_name          = Column(String(255), nullable=False)
    supplier_name      = Column(String(255))
    products_extracted = Column(Integer, default=0)
    updates            = Column(JSON)   # list of {catalogueId, catalogueFile, productId, productName, oldPrice, newPrice, currency, matchType}
    uploaded_at        = Column(DateTime, default=datetime.utcnow)
