import pandas as pd
from google.adk.tools.tool_context import ToolContext
from loguru import logger

from src.turri_data_hub.google_analytics.models import PageGoogleAnalyticsData

from ...db import db
from ...utils import format_tool_args, make_numpy_values_serialiable


async def get_product_website_views(
    product_id: int, from_date: str, to_date: str, agregate_by: str
):
    """
    Retrieve aggregated page view data for a specific product, grouped by day, month, or quarter.

    This function fetches Google Analytics page view data for the product identified by `product_id`.
    The data is sourced from Google Analytics data of your webpage.
    The data is filtered by the optional `from_date` and `to_date` (inclusive, in ISO format YYYY-MM-DD).
    The results are aggregated by the specified period: "day", "month", or "quarter".

    Args:
        product_id (int): The ID of the product to retrieve analytics for.
        from_date (str): ISO format date string (YYYY-MM-DD) for the start of the aggregation period. If "" includes all dates.
        to_date (str): ISO format date string (YYYY-MM-DD) for the end of the aggregation period. If "" includes all dates.
        agregate_by (str): The aggregation period. Must be one of "day", "month", or "quarter".

    Returns:
        dict: {
            "status": "success",
            "aggregation": [
                {
                    "period": str,      # e.g., "2024-06-01" for day, "2024-06" for month, "2024-Q2" for quarter
                    "total_views": int, # Total page views for the period
                },
                ...
            ]
        }
        or
        dict: {"status": "error", "error_message": str} on failure.
    """
    logger.info(
        format_tool_args(
            "get_product_website_views",
            product_id=product_id,
            from_date=from_date,
            to_date=to_date,
            agregate_by=agregate_by,
        )
    )
    try:
        if agregate_by not in {"day", "month", "quarter", "year"}:
            raise ValueError("agregate_by must be day, month, quarter or year")

        page = await db.query_table(
            PageGoogleAnalyticsData,
            where_clauses=[PageGoogleAnalyticsData.product_id == product_id],
            mode="first",
        )
        if not page:
            raise ValueError("analytics for product not found")
        if not page.visits_over_time:
            return {"status": "sucess", "info": "No Visits for Page found!"}

        df = pd.DataFrame.from_dict(page.visits_over_time)
        df["date"] = pd.to_datetime(df["date"])

        if from_date:
            df = df[df["date"] >= pd.to_datetime(from_date)]
        if to_date:
            df = df[df["date"] <= pd.to_datetime(to_date)]

        if agregate_by == "day":
            df["period"] = df["date"].dt.strftime("%Y-%m-%d")
        elif agregate_by == "month":
            df["period"] = df["date"].dt.strftime("%Y-%m")
        elif agregate_by == "quarter":
            df["period"] = (
                df["date"].dt.to_period("Q").astype(str).str.replace("Q", "-Q")
            )
        elif agregate_by == "year":
            df["period"] = df["date"].dt.strftime("%Y")
        else:
            return {"status": "error", "error_message": "Invalid agregate_by"}

        agg = (
            df.groupby("period")["pageviews"]
            .sum()
            .reset_index()
            .rename(columns={"pageviews": "total_views"})
        )

        result = [
            {"period": row["period"], "total_views": int(row["total_views"])}
            for _, row in agg.iterrows()
        ]
        return make_numpy_values_serialiable(
            {"status": "success", "aggregation": result}
        )
    except Exception as e:
        logger.error(f"\U0001f6e0 [TOOL] get_product_website_views error: {e}")
        return {"status": "error", "error_message": str(e)}


async def get_producer_webiste_views(
    from_date: str,
    to_date: str,
    agregate_by: str,
    tool_context: ToolContext,
):
    """
    Retrieve aggregated page view data for all products of a producer, grouped by day, month, or quarter.

    This function fetches Google Analytics page view data for all products associated with the producer
    specified in the tool context state. The data is sourced from Google Analytics data of your webpage.
    The data is filtered by the optional `from_date` and `to_date` (inclusive, in ISO format YYYY-MM-DD).
    The results are aggregated by the specified period: "day", "month", or "quarter".

    Args:
        from_date (str): ISO format date string (YYYY-MM-DD) for the start of the aggregation period. If "" includes all dates.
        to_date (str): ISO format date string (YYYY-MM-DD) for the end of the aggregation period. If "" includes all dates.
        agregate_by (str): The aggregation period. Must be one of "day", "month", or "quarter".
        tool_context (ToolContext): The tool context containing the producer_id in its state.

    Returns:
        dict: {
            "status": "success",
            "aggregation": [
                {
                    "period": str,      # e.g., "2024-06-01" for day, "2024-06" for month, "2024-Q2" for quarter
                    "total_views": int, # Total page views for the period
                },
                ...
            ]
        }
        or
        dict: {"status": "error", "error_message": str} on failure.
    """
    logger.info(
        format_tool_args(
            "get_producer_webiste_views",
            from_date=from_date,
            to_date=to_date,
            agregate_by=agregate_by,
            tool_context=tool_context,
        )
    )
    try:
        producer_id = tool_context.state.get("producer_id")
        if not producer_id:
            raise RuntimeError("state.producer_id must be set")

        if agregate_by not in {"day", "month", "quarter", "year"}:
            raise ValueError("agregate_by must be day, month, quarter or year")

        pages = await db.query_table(
            PageGoogleAnalyticsData,
            where_clauses=[PageGoogleAnalyticsData.producer_id == producer_id],
        )

        dfs = [
            pd.DataFrame.from_dict(page.visits_over_time)
            for page in pages
            if page.visits_over_time
        ]

        if not dfs:
            return {"status": "sucess", "info": "No Visits found!"}

        df = pd.concat(dfs)
        df["date"] = pd.to_datetime(df["date"])

        if from_date:
            df = df[df["date"] >= pd.to_datetime(from_date)]
        if to_date:
            df = df[df["date"] <= pd.to_datetime(to_date)]

        if agregate_by == "day":
            df["period"] = df["date"].dt.strftime("%Y-%m-%d")
        elif agregate_by == "month":
            df["period"] = df["date"].dt.strftime("%Y-%m")
        elif agregate_by == "quarter":
            df["period"] = (
                df["date"].dt.to_period("Q").astype(str).str.replace("Q", "-Q")
            )
        elif agregate_by == "year":
            df["period"] = df["date"].dt.strftime("%Y")
        else:
            return {"status": "error", "error_message": "Invalid agregate_by"}

        agg = (
            df.groupby("period")["pageviews"]
            .sum()
            .reset_index()
            .rename(columns={"pageviews": "total_views"})
        )

        result = [
            {"period": row["period"], "total_views": int(row["total_views"])}
            for _, row in agg.iterrows()
        ]
        return make_numpy_values_serialiable(
            {"status": "success", "aggregation": result}
        )
    except Exception as e:
        logger.error(f"\U0001f6e0 [TOOL] get_producer_webiste_views error: {e}")
        return {"status": "error", "error_message": str(e)}


async def get_product_website_users_counts_by_region(product_id: int):
    """
    Retrieve the count of users by region for a specific product based on Google Analytics data.

    This function fetches user and region data from Google Analytics for the product identified by `product_id`.
    It returns a dictionary mapping each region to the number of users from that region who visited the product page.

    Args:
        product_id (int): The ID of the product to retrieve user region counts for.

    Returns:
        dict: {
            "status": "success",
            "user_counts_by_region": {
                region (str): user_count (int),
                ...
            }
        }
        or
        dict: {"status": "error", "error_message": str} on failure.
    """
    logger.info(
        format_tool_args(
            "get_product_website_users_counts_by_region", product_id=product_id
        )
    )
    try:
        page: PageGoogleAnalyticsData = await db.query_table(
            PageGoogleAnalyticsData,
            where_clauses=[PageGoogleAnalyticsData.product_id == product_id],
            mode="first",
        )
        if not page:
            raise ValueError("analytics for product not found")
        if not page.user_and_regions:
            return {"status": "sucess", "info": "No Visits for Page found!"}

        df = pd.DataFrame.from_dict(page.user_and_regions)
        val = df.value_counts("region").to_dict()

        return make_numpy_values_serialiable(
            {"status": "success", "user_counts_by_region": val},
        )

    except Exception as e:
        logger.error(
            f"\U0001f6e0 [TOOL] get_product_website_users_counts_by_region error: {e}"
        )
        return {"status": "error", "error_message": str(e)}


async def get_producer_website_users_counts_by_region(
    tool_context: ToolContext,
):
    """
    Retrieve the count of users by region for all products of a producer based on Google Analytics data.

    This function fetches user and region data from Google Analytics for all products associated with the producer
    specified in the tool context state. It returns a dictionary mapping each region to the number of users from that
    region who visited any of the producer's product pages.

    Args:
        tool_context (ToolContext): The tool context containing the producer_id in its state.

    Returns:
        dict: {
            "status": "success",
            "user_counts_by_region": {
                region (str): user_count (int),
                ...
            }
        }
        or
        dict: {"status": "error", "error_message": str} on failure.
    """
    logger.info(
        format_tool_args(
            "get_producer_website_users_counts_by_region", tool_context=tool_context
        )
    )
    try:
        producer_id = tool_context.state.get("producer_id")
        if not producer_id:
            raise RuntimeError("state.producer_id must be set")

        pages: PageGoogleAnalyticsData = await db.query_table(
            PageGoogleAnalyticsData,
            where_clauses=[PageGoogleAnalyticsData.producer_id == producer_id],
        )
        if not pages:
            raise ValueError("analytics for product not found")
        dfs = [
            pd.DataFrame.from_dict(page.user_and_regions)
            for page in pages
            if page.user_and_regions
        ]

        if not dfs:
            return {"status": "sucess", "info": "No Visits found!"}

        df = pd.concat(dfs)

        val = df.value_counts("region").to_dict()

        return make_numpy_values_serialiable(
            {"status": "success", "user_counts_by_region": val},
        )

    except Exception as e:
        logger.error(
            f"\U0001f6e0 [TOOL] get_producer_website_users_counts_by_region error: {e}"
        )
        return {"status": "error", "error_message": str(e)}
