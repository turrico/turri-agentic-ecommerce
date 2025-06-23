from datetime import datetime

import numpy as np
from google.genai import types
from loguru import logger
from sqlalchemy.orm import selectinload
from tqdm import tqdm

from src.agents.utils import gemini_only_text

from ..db import TurriDB
from ..woocommerce.models import Order, Product
from .taste_categories import TASTE_KEYS
from .update_profile import update_user_profile


async def update_customer(db: TurriDB, from_date: datetime, customer_id: int):
    orders: list[Order] = await db.query_table(
        Order,
        where_clauses=[
            Order.date_created > from_date,
            Order.customer_id == customer_id,
        ],
        options=[selectinload(Order.line_items)],
    )

    taste_embeddings = []
    text = ""

    for order in orders:
        for item in order.line_items:
            product: Product = await db.query_table(
                Product,
                where_clauses=[Product.id == item.product_id],
                mode="first",
                options=[
                    selectinload(Product.producer),
                    selectinload(Product.categories),
                    selectinload(Product.tags),
                ],
            )
            if not product:
                logger.info(f"Could not get product {item.product_id}")
                continue
            taste_embeddings.append(product.taste_embedding)

            text += f"""
                ----------------------------------------------------------------------
                The user ordered {item.quantity} of the following Product:
                {product.model_dump_json(include=["title", "description", "content"], indent=4)}
                
                Which has these tags: {[tag.name for tag in product.tags]}
                Which has these categories: {[cat.name for cat in product.categories]}
                
                And which of is this Producer:
                {product.producer.model_dump_json(include=["title", "content"], indent=4)}
                """

    if not taste_embeddings:
        return

    taste_embedding = np.mean(taste_embeddings, axis=0).tolist()
    new_description = await gemini_only_text(
        "gemini-2.0-flash",
        contents=[types.Content(parts=[types.Part(text=text)])],
        system_message=(
            "Create a brief summary of the users shopping pattern. "
            f"Does he fit in any of these categories {TASTE_KEYS}. "
            "Your sentence will be used to compute an embedding vector so try to have as much information richness and low boilerplate"
        ),
    )

    await update_user_profile(
        db=db,
        user_id=customer_id,
        new_description=new_description,
        new_taste_embedding=taste_embedding,
        source="woocommerce",
    )


async def update_customer_profiles_based_on_orders(
    db: TurriDB, from_date: datetime
) -> tuple[int, int]:
    # could be optmized by sql query directly
    orders_since_then = await db.query_table(
        Order, where_clauses=[Order.date_created > from_date]
    )
    customers = {order.customer_id for order in orders_since_then}

    success = 0
    failures = 0

    for customer_id in tqdm(customers):
        try:
            await update_customer(db=db, from_date=from_date, customer_id=customer_id)
            success += 1
        except Exception as e:
            logger.exception(f"Failed to update customer profile because of {e}")
            failures += 1

    return success, failures
