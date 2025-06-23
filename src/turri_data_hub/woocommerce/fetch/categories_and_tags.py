from typing import Type

import requests
from loguru import logger
from sqlmodel import SQLModel

from src.turri_data_hub.db import TurriDB
from src.turri_data_hub.settings import WoocommerceSettings
from src.turri_data_hub.woocommerce.models import ProductCategory, ProductTag


async def fetch_create_and_save_simple(
    db: TurriDB, model: Type[SQLModel], last_url_part: str
):
    settings = WoocommerceSettings()

    logger.info(f"Fetching {last_url_part} from WooCommerce")
    params = {"per_page": 100, "page": 1}  # this should always sufice

    resp = requests.get(
        f"{settings.url}/wp-json/wc/v3/products/{last_url_part}",
        params=params,
        auth=(settings.WOOCOMERCE_CLIENT_KEY, settings.WOOCOMERCE_SECRET_KEY),
    )
    resp.raise_for_status()
    items = [model(**cat) for cat in resp.json()]
    await db.save_all(items)
    logger.success(f"Saved {len(items)} {last_url_part}")


async def fetch_create_and_save_categories(db: TurriDB):
    await fetch_create_and_save_simple(
        db=db, model=ProductCategory, last_url_part="categories"
    )


async def fetch_create_and_save_tags(db: TurriDB):
    await fetch_create_and_save_simple(db=db, model=ProductTag, last_url_part="tags")
