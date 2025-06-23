import asyncio
from datetime import datetime

import requests
from loguru import logger
from tqdm import tqdm

from src.turri_data_hub.db import TurriDB
from src.turri_data_hub.embedding import compute_embeddings
from src.turri_data_hub.recommendation_system.taste_categories import TASTE_KEYS
from src.turri_data_hub.woocommerce.models import (
    Producer,
    Product,
    ProductCategory,
    ProductTag,
)

from .utils import fetch_list, get_text


async def generate_product(
    data: dict,
    db: TurriDB,
) -> Product:
    category_ids = [cat["id"] for cat in data["categories"]]
    categories = await db.query_table(
        ProductCategory, where_clauses=[ProductCategory.id.in_(category_ids)]
    )

    tag_ids = [cat["id"] for cat in data["tags"]]
    tags = await db.query_table(ProductTag, where_clauses=[ProductTag.id.in_(tag_ids)])

    meta_box = data["meta_box"]
    producer_id = (
        int(meta_box["producto-productor-relationship_from"][0])
        if meta_box["producto-productor-relationship_from"]
        else None
    )

    producer = (
        await db.query_table(
            Producer, where_clauses=[Producer.id == producer_id], mode="first"
        )
        if producer_id
        else None
    )

    img = data.get("images")
    img = img[0]["src"] if isinstance(img, list) and img and "src" in img[0] else None

    resp = await asyncio.to_thread(
        requests.get, f"https://turri.cr/wp-json/wp/v2/product/{data['id']}"
    )
    resp.raise_for_status()
    product_json = resp.json()

    date_created = datetime.fromisoformat(data["date_created"])
    date_modified = datetime.fromisoformat(data["date_modified"])

    discard = [
        "id",
        "permalink",
        "name",
        "tags",
        "categories",
        "date_created",
        "date_modified",
        "price",
        "stock_quantity",
        "total_sales",
    ]
    stripped = {i: a for i, a in data.items() if i not in discard}

    embeddings = await compute_embeddings(
        [
            get_text(
                product_json["content"]["rendered"], product_json["excerpt"]["rendered"]
            )
        ]
    )

    product = Product(
        id=int(data["id"]),
        link=data["permalink"],
        title=data["name"],
        content=product_json["content"]["rendered"],
        excerpt=product_json["excerpt"]["rendered"],
        img_url=img,
        categories=categories,
        tags=tags,
        producer=producer,
        producer_id=producer_id,
        date_created=date_created,
        date_modified=date_modified,
        price=float(data["price"]),
        stock_quantity=(
            int(data["stock_quantity"]) if data.get("stock_quantity") else None
        ),
        total_sales=int(data["total_sales"]),
        embedding=embeddings[0],
        taste_embedding=[0] * len(TASTE_KEYS),
        **stripped,
    )
    await db.save(product)


async def fetch_generate_and_save_products(db: TurriDB, per_page=50):
    products = fetch_list(
        url="/wp-json/wc/v3/products",
        per_page=per_page,
    )

    for product in tqdm(products):
        try:
            await generate_product(product, db)
        except Exception as e:
            logger.error(
                f"Error processing product {product.get('id', 'unknown')}: {e}"
            )
