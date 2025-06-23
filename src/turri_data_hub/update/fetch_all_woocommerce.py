from sqlalchemy.orm import selectinload

from src.turri_data_hub.db import TurriDB
from src.turri_data_hub.recommendation_system.compute_taste_embeddings import (
    get_producer_taste_embeddings,
    get_product_taste_embeddings,
)
from src.turri_data_hub.woocommerce.fetch import (
    fetch_create_and_save_categories,
    fetch_create_and_save_customers,
    fetch_create_and_save_orders,
    fetch_create_and_save_tags,
    fetch_generate_and_save_producers,
    fetch_generate_and_save_products,
)
from src.turri_data_hub.woocommerce.models import Producer, Product


async def calc_for_products(db: TurriDB):
    products: list[Product] = await db.query_table(
        Product, options=[selectinload(Product.tags), selectinload(Product.categories)]
    )

    for product in products:
        product.taste_embedding = get_product_taste_embeddings(product)
        await db.save(product)


async def calc_for_producers(db: TurriDB):
    producers: list[Producer] = await db.query_table(
        Producer, options=[selectinload(Producer.products)]
    )

    for producer in producers:
        producer.taste_embedding = get_producer_taste_embeddings(producer)
        await db.save(producer)


async def fetch_all_wocommerce_data():
    db = TurriDB()
    await db.initialize_db()
    await fetch_create_and_save_tags(db)
    await fetch_create_and_save_categories(db)
    await fetch_generate_and_save_producers(db)
    await fetch_generate_and_save_products(db)
    await fetch_create_and_save_customers(db)
    await fetch_create_and_save_orders(db)

    await calc_for_products(db)
    await calc_for_producers(db)
