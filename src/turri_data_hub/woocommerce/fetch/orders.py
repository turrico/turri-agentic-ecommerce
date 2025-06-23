from datetime import datetime

from loguru import logger
from tqdm import tqdm

from src.turri_data_hub.db import TurriDB
from src.turri_data_hub.woocommerce.models import (
    Customer,
    LineItem,
    Order,
)

from .utils import fetch_list


async def fetch_create_and_save_order(
    data: dict,
    db: TurriDB,
):
    customer = await db.query_table(
        Customer, [Customer.id == data["customer_id"]], mode="first"
    )

    if customer is None:
        logger.info(f"Skipping order {data['id']} because we can't find customer")

    line_items = [
        LineItem(
            id=int(item["id"]),
            order_id=int(data["id"]),
            product_id=int(item["product_id"]),
            quantity=int(item["quantity"]),
            price=float(item["price"]),
        )
        for item in data["line_items"]
    ]

    order = Order(
        id=data["id"],
        date_created=datetime.fromisoformat(data["date_created"]),
        status=data["status"],
        customer_id=data["customer_id"],
        currency=data["currency"],
        total=float(data["total"]),
        total_tax=float(data["total_tax"]),
        prices_include_tax=data["prices_include_tax"],
        line_items=line_items,
        customer=customer,
    )
    await db.save(order)


async def fetch_create_and_save_orders(db: TurriDB, per_page: int = 50):
    orders = fetch_list("wp-json/wc/v3/orders", per_page=per_page)

    for data in tqdm(orders):
        try:
            await fetch_create_and_save_order(data, db)
        except Exception as e:
            logger.error(f"Failed to save order: {e} | Data: {data.get('id')}")
