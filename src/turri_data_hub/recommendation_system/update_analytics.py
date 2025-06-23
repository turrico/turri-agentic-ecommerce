import asyncio
from datetime import datetime

import numpy as np
import pandas as pd
from google.cloud import bigquery
from google.genai import types
from loguru import logger
from sqlalchemy.orm import selectinload
from tqdm import tqdm

from src.agents.utils import gemini_only_text
from src.turri_data_hub.settings import GoogleCloudSettings, WoocommerceSettings

from ..db import TurriDB
from ..woocommerce.models import Producer, Product, ProductCategory
from .taste_categories import TASTE_KEYS
from .update_profile import update_user_profile

gc_settings = GoogleCloudSettings()
BASE_URL = WoocommerceSettings().url


async def fetch_user_page_activity(from_date: datetime) -> pd.DataFrame:
    """
    Fetches user page view and engagement data from Google Analytics.
    It identifies pages as 'product', 'category', or 'producer',
    extracts the entity slug, and returns the full page link.
    """
    # The regex for identifying product pages is now passed as a parameter
    product_page_regex = f"^{BASE_URL}/[^/]+/?$"

    sql = f"""
    WITH events AS (
        SELECT
            user_id,
            SPLIT((SELECT ep.value.string_value FROM UNNEST(event_params) AS ep WHERE ep.key="page_location"), '?')[OFFSET(0)] AS page_location
        FROM `{gc_settings.ANALYTICS_BG_TABLE_NAME}`
        WHERE
            event_date >= FORMAT_DATE('%Y%m%d', @start_date)
            AND user_id IS NOT NULL AND user_id != '0'
            AND event_name IN ('page_view', 'view_item')
    ),
    categorized_events AS (
        SELECT
            user_id,
            CASE
                WHEN STARTS_WITH(page_location, @producer_prefix) THEN 'producer'
                WHEN STARTS_WITH(page_location, @category_prefix) THEN 'category'
                WHEN REGEXP_CONTAINS(page_location, @base_url_regex) THEN 'product'
                ELSE NULL
            END AS page_type,
            REGEXP_EXTRACT(page_location, r'/([^/]+)/?$') AS slug
        FROM events
    )
    SELECT
        user_id,
        page_type,
        slug,
        COUNT(*) AS view_count
    FROM categorized_events
    WHERE page_type IS NOT NULL AND slug IS NOT NULL
    GROUP BY user_id, page_type, slug
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("start_date", "DATE", from_date.date()),
            bigquery.ScalarQueryParameter(
                "category_prefix", "STRING", f"{BASE_URL}/categoria-producto/"
            ),
            bigquery.ScalarQueryParameter(
                "producer_prefix", "STRING", f"{BASE_URL}/productor/"
            ),
            bigquery.ScalarQueryParameter(
                "base_url_regex", "STRING", product_page_regex
            ),
        ]
    )

    def _async_func() -> pd.DataFrame:
        client = bigquery.Client(project=gc_settings.GC_PROJECT_ID)
        return client.query(sql, job_config=job_config).to_dataframe()

    return await asyncio.to_thread(_async_func)


async def update_customer(db: TurriDB, customer_id: int, group: pd.DataFrame):
    taste_embeddings = []
    text = ""

    for _, row in group.iterrows():
        if row.page_type == "product":
            product = await db.query_table(
                Product,
                where_clauses=[Product.slug == row.slug],
                options=[
                    selectinload(Product.producer),
                    selectinload(Product.categories),
                    selectinload(Product.tags),
                ],
                mode="first",
            )

            if not product:
                continue

            taste_embeddings.append(product.taste_embedding)

            text += f"""
                ----------------------------------------------------------------------
                The user visited the of the following Product {row.view_count} times:
                {product.model_dump_json(include=["title", "description", "content"], indent=4)}
                
                Which has these tags: {[tag.name for tag in product.tags]}
                Which has these categories: {[cat.name for cat in product.categories]}
                
                And which of is this Producer:
                {product.producer.model_dump_json(include=["title", "content"], indent=4)}
                """

        elif row.page_type == "producer":
            producer = await db.query_table(
                Producer,
                where_clauses=[Producer.slug == row.slug],
                mode="first",
            )
            if not producer:
                logger.warning(f"Unknown producer: {row.slug}")
                continue

            taste_embeddings.append(producer.taste_embedding)

            text += f"""
                ----------------------------------------------------------------------
                The user visited the of the following producer {row.view_count} times:
                {producer.model_dump_json(include=["title", "content"], indent=4)}
                """

        elif row.page_type == "category":
            category: ProductCategory = await db.query_table(
                ProductCategory,
                where_clauses=[ProductCategory.slug == row.slug],
                mode="first",
            )
            if not category:
                logger.warning(f"Unknown category: {row.slug}")
                continue

            text += f"""
                ----------------------------------------------------------------------
                The user visited the of the following category {row.view_count} times:
                {category.name}
                """

    if not taste_embeddings:
        logger.debug(f"Found no match for uesr {customer_id}")
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
        source="google",
    )


async def update_customer_profiles_based_on_analytics(
    db: TurriDB, from_date: datetime
) -> tuple[int, int]:
    success = 0
    failures = 0
    try:
        df = await fetch_user_page_activity(from_date=from_date)
    except Exception as e:
        logger.error(f"big query query failed with {e}")
        return 0, 0

    for user_id, group in tqdm(df.groupby("user_id")):
        try:
            await update_customer(db=db, customer_id=int(user_id), group=group)
            success += 1
        except Exception as e:
            logger.exception(f"Failed to update customer profile because of {e}")
            failures += 1

    return success, failures
