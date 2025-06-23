from datetime import datetime
from typing import Any, List, Optional

from pgvector.sqlalchemy import Vector
from sqlmodel import Column, Field, Relationship, SQLModel

from src.turri_data_hub.embedding import EMBEDDING_DIM

from ..recommendation_system.taste_categories import TASTE_KEYS


class ProductTagLink(SQLModel, table=True):
    product_id: int = Field(foreign_key="product.id", primary_key=True)
    tag_id: int = Field(foreign_key="producttag.id", primary_key=True)


class ProductCategoryLink(SQLModel, table=True):
    product_id: int = Field(foreign_key="product.id", primary_key=True)
    category_id: int = Field(foreign_key="productcategory.id", primary_key=True)


class ProductTag(SQLModel, table=True):
    id: int = Field(primary_key=True, index=True)
    description: str
    name: str
    slug: str = Field(index=True)
    products: List["Product"] = Relationship(
        back_populates="tags", link_model=ProductTagLink
    )


class ProductCategory(SQLModel, table=True):
    id: int = Field(primary_key=True, index=True)
    description: str
    name: str
    slug: str = Field(index=True)
    products: List["Product"] = Relationship(
        back_populates="categories", link_model=ProductCategoryLink
    )


class Producer(SQLModel, table=True):
    id: int = Field(primary_key=True, index=True)
    link: str
    title: str
    content: str
    excerpt: str
    slug: str = Field(index=True)
    img_url: Optional[str] = None
    products: List["Product"] = Relationship(back_populates="producer")
    embedding: Any = Field(
        sa_column=Column(Vector(EMBEDDING_DIM)),
        default=None,
    )
    taste_embedding: list[float] = Field(sa_column=Column(Vector(len(TASTE_KEYS))))


class Product(SQLModel, table=True):
    id: int = Field(primary_key=True, index=True)
    link: str
    title: str
    content: str
    slug: str = Field(index=True)
    excerpt: str
    description: str
    img_url: Optional[str] = None
    producer_id: int = Field(foreign_key="producer.id")
    producer: Optional[Producer] = Relationship(back_populates="products")
    taste_embedding: list[float] = Field(sa_column=Column(Vector(len(TASTE_KEYS))))
    categories: List[ProductCategory] = Relationship(
        back_populates="products", link_model=ProductCategoryLink
    )
    tags: List[ProductTag] = Relationship(
        back_populates="products", link_model=ProductTagLink
    )

    embedding: Any = Field(
        sa_column=Column(Vector(EMBEDDING_DIM)),
        default=None,
    )

    stock_quantity: Optional[int] = None
    date_created: datetime
    date_modified: datetime
    type: str
    status: str
    catalog_visibility: str
    featured: bool
    price: float
    total_sales: int

    def customer_information(self):
        return self.model_dump(exclude=["link", "img_url", "products", "embedding"])


class LineItem(SQLModel, table=True):
    id: int = Field(primary_key=True, index=True)
    order_id: int = Field(foreign_key="order.id")
    product_id: int
    quantity: int
    price: float
    order: Optional["Order"] = Relationship(back_populates="line_items")


class Customer(SQLModel, table=True):
    id: int = Field(primary_key=True, index=True)
    date_created: datetime
    email: str
    username: str
    last_ordered: Optional[datetime] = None
    orders: List["Order"] = Relationship(back_populates="customer")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class Order(SQLModel, table=True):
    id: int = Field(primary_key=True, index=True)
    date_created: datetime
    status: str
    customer_id: Optional[int] = Field(foreign_key="customer.id")
    currency: str
    total: float
    total_tax: float
    prices_include_tax: bool
    line_items: list[LineItem] = Relationship(back_populates="order")
    customer: Optional[Customer] = Relationship(back_populates="orders")
