from datetime import datetime

from loguru import logger

from src.turri_data_hub.db import TurriDB
from src.turri_data_hub.woocommerce.models import (
    Customer,
)

from .utils import fetch_list


async def fetch_create_and_save_customers(db: TurriDB, per_page: int = 50):
    customers = fetch_list("wp-json/wc/v3/customers", per_page=per_page)

    for data in customers:
        try:
            data["date_created"] = datetime.fromisoformat(data["date_created"])
            await db.save(Customer(**data))
        except Exception as e:
            logger.error(f"Failed to save customer: {e} | Data: {data}")
