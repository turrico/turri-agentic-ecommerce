import sys

sys.path.append(".")
import asyncio
from datetime import datetime

from loguru import logger
from sqlalchemy.orm import selectinload
from tqdm import tqdm

from src.turri_data_hub.db import TurriDB
from src.turri_data_hub.google_analytics.fetch import (
    get_pageviews_over_time,
    get_unique_users_and_regions,
)
from src.turri_data_hub.google_analytics.models import PageGoogleAnalyticsData
from src.turri_data_hub.woocommerce.models import Producer, Product


def df_to_json(records_df) -> list[dict]:
    records_df = records_df.copy()
    if "date" in records_df:
        records_df["date"] = records_df["date"].astype(str)
    return records_df.to_dict(orient="records")


async def fetch_for_product(
    product: Product, producer_id: int
) -> PageGoogleAnalyticsData:
    users_and_regions = await get_unique_users_and_regions(product.link)
    visits_over_time = await get_pageviews_over_time(product.link)
    return PageGoogleAnalyticsData(
        url=product.link,
        product_id=product.id,
        producer_id=producer_id,
        user_and_regions=df_to_json(users_and_regions),
        visits_over_time=df_to_json(visits_over_time),
        last_updated=datetime.now(),
    )


async def fetch_for_producer(db: TurriDB, producer: Producer):
    users_and_regions = await get_unique_users_and_regions(producer.link)
    visits_over_time = await get_pageviews_over_time(producer.link)
    producer_page = PageGoogleAnalyticsData(
        url=producer.link,
        producer_id=producer.id,
        user_and_regions=df_to_json(users_and_regions),
        visits_over_time=df_to_json(visits_over_time),
        last_updated=datetime.now(),
    )
    await db.save(producer_page)

    try:
        product_pages = await asyncio.gather(
            *[fetch_for_product(product, producer.id) for product in producer.products]
        )
        await db.save_all(product_pages)
    except Exception as e:
        logger.error(
            f"Error fetching or saving product pages for producer {producer.id}: {e}"
        )


async def fetch_google_analytics_data(db: TurriDB):
    producers = await db.query_table(
        Producer, options=[selectinload(Producer.products)]
    )

    for p in tqdm(producers):
        try:
            await fetch_for_producer(db, p)
        except Exception as e:
            logger.error(f"Error processing producer {p.id}: {e}")
