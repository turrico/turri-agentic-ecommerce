import asyncio
from typing import Optional

import pandas as pd
from google.cloud import bigquery

from ..settings import GoogleCloudSettings

settings = GoogleCloudSettings()


async def get_pageviews_over_time(
    page_prefix: str, start_date: Optional[str] = None
) -> pd.DataFrame:
    sql = f"""
    WITH events AS (
      SELECT
        (SELECT ep.value.string_value
         FROM UNNEST(event_params) AS ep
         WHERE ep.key="page_location") AS page_location,
        EXTRACT(DATE FROM TIMESTAMP_MICROS(event_timestamp)) AS date
      FROM `{settings.ANALYTICS_BG_TABLE_NAME}`
      WHERE event_name="page_view"
    )
    SELECT
      date,
      COUNT(*) AS pageviews
    FROM events
    WHERE STARTS_WITH(page_location, @page_prefix)
      {"AND date>=@start_date" if start_date else ""}
    GROUP BY date
    ORDER BY date
    """
    params = [bigquery.ScalarQueryParameter("page_prefix", "STRING", page_prefix)]
    if start_date:
        params.append(bigquery.ScalarQueryParameter("start_date", "DATE", start_date))
    job_config = bigquery.QueryJobConfig(query_parameters=params)

    def _async_func():
        client = bigquery.Client(project=settings.GC_PROJECT_ID)

        return client.query(sql, job_config=job_config).to_dataframe()

    return await asyncio.to_thread(_async_func)


async def get_unique_users_and_regions(
    page_prefix: str,
    start_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Fetch distinct users (preferring logged-in user_id over pseudo_id) and their regions for page views.

    Args:
        page_prefix (str): Prefix to filter page_location.
        start_date (Optional[str]): ISO date (`YYYY-MM-DD`) to filter events on or after this date.

    Returns:
        pd.DataFrame: Columns [`user_id`, `region`] sorted by region and user_id.
    """
    sql = f"""
    WITH events AS (
      SELECT
        user_id,
        user_pseudo_id,
        geo.region AS region,
        EXTRACT(DATE FROM TIMESTAMP_MICROS(event_timestamp)) AS date,
        (SELECT ep.value.string_value
         FROM UNNEST(event_params) AS ep
         WHERE ep.key="page_location") AS page_location
      FROM `{settings.ANALYTICS_BG_TABLE_NAME}`
      WHERE event_name="page_view"
    )
    SELECT DISTINCT
      COALESCE(user_id, user_pseudo_id) AS user_id,
      region
    FROM events
    WHERE STARTS_WITH(page_location, @page_prefix)
      {"AND date>=@start_date" if start_date else ""}
    ORDER BY region, user_id
    """
    params: list[bigquery.ScalarQueryParameter] = [
        bigquery.ScalarQueryParameter("page_prefix", "STRING", page_prefix)
    ]
    if start_date:
        params.append(bigquery.ScalarQueryParameter("start_date", "DATE", start_date))
    job_config = bigquery.QueryJobConfig(query_parameters=params)

    def _async_func() -> pd.DataFrame:
        client = bigquery.Client(project=settings.GC_PROJECT_ID)
        return client.query(sql, job_config=job_config).to_dataframe()

    return await asyncio.to_thread(_async_func)
