from datetime import datetime

from google.adk.tools.tool_context import ToolContext
from loguru import logger
from sqlalchemy.orm import selectinload

from src.turri_data_hub.woocommerce.models import LineItem, Order, Product

from ...db import db
from ...utils import format_tool_args, make_numpy_values_serialiable


def _products_to_dict(products):
    dicts = []
    for p in products:
        p_dict = p.model_dump(exclude="embedding")
        p_dict["tags"] = [tag.model_dump() for tag in p.tags]
        p_dict["categories"] = [tag.model_dump() for tag in p.categories]

        dicts.append(p_dict)
    return dicts


async def get_products(tool_context: ToolContext) -> dict:
    """Fetches all products for the current producer from the database.

    Use this tool to retrieve the list of products associated with the producer specified in the tool context state.

    Returns:
        dict: {'status': 'success', 'products': [product_dicts]} on success,
              {'status': 'error', 'error_message': str} on failure.
    """
    logger.info(format_tool_args("get_products", tool_context=tool_context))

    producer_id = tool_context.state.get("producer_id")
    if not producer_id:
        raise RuntimeError("state.producer_id must be set")

    try:
        products = await db.query_table(
            Product,
            where_clauses=[
                Product.producer_id == producer_id,
            ],
            options=[selectinload(Product.categories), selectinload(Product.tags)],
        )

        result = {
            "status": "success",
            "products": _products_to_dict(products),
        }
        return make_numpy_values_serialiable(result)
    except Exception as e:
        logger.error(f"\U0001f6e0 [TOOL] get_products error: {e}")
        return {"status": "error", "error_message": str(e)}


async def get_orders_of_product(
    product_id: int, from_date: str, to_date: str, agregate_by: str
):
    """
    Retrieve aggregated sales data for a specific product, grouped by day, month, or quarter.

    Args:
        product_id (int): The ID of the product to aggregate orders for.
        from_date (str): ISO format date string (YYYY-MM-DD) for the start of the aggregation period. If "", includes all dates.
        to_date (str): ISO format date string (YYYY-MM-DD) for the end of the aggregation period. If "" includes all dates.
        agregate_by (str): The aggregation period. Must be one of "day", "month", "quarter" or "year".

    Returns:
        dict: {
            "status": "success",
            "aggregation": [
                {
                    "period": str,  # e.g., "2024-06-01" for day, "2024-06" for month, "2024-Q2" for quarter
                    "total_sales": float,  # Sum of prices for the period
                    "total_quantity": int, # Sum of quantities for the period
                },
                ...
                For all periouds with values, those with None or None.
            ]
        }
        or
        dict: {"status": "error", "error_message": str} on failure.
    """
    logger.info(
        format_tool_args(
            "get_orders_of_product",
            product_id=product_id,
            from_date=from_date,
            to_date=to_date,
            agregate_by=agregate_by,
        )
    )

    try:
        if agregate_by not in ["day", "month", "quarter", "year"]:
            raise ValueError("agregate_by must be day, month, quarter or year")

        where_clauses = [
            LineItem.product_id == product_id,
            LineItem.order.has(Order.status == "completed"),
        ]

        if from_date:
            from_date_dt = datetime.fromisoformat(from_date)
            where_clauses.append(LineItem.order.has(Order.date_created >= from_date_dt))

        if to_date:
            to_date_dt = datetime.fromisoformat(to_date)
            where_clauses.append(LineItem.order.has(Order.date_created <= to_date_dt))

        line_items = await db.query_table(
            LineItem,
            where_clauses=where_clauses,
            options=[selectinload(LineItem.order)],
        )

        # Aggregate by period
        aggregation = {}
        for item in line_items:
            order_date = item.order.date_created
            if agregate_by == "day":
                period = order_date.strftime("%Y-%m-%d")
            elif agregate_by == "month":
                period = order_date.strftime("%Y-%m")
            elif agregate_by == "quarter":
                quarter = (order_date.month - 1) // 3 + 1
                period = f"{order_date.year}-Q{quarter}"
            elif agregate_by == "year":
                period = order_date.strftime("%Y")
            else:
                continue  # Should not happen due to earlier check

            if period not in aggregation:
                aggregation[period] = {"total_sales": 0.0, "total_quantity": 0}
            aggregation[period]["total_sales"] += item.price
            aggregation[period]["total_quantity"] += item.quantity

        # If no transactions, return empty aggregation
        result = [
            {
                "period": period,
                "total_sales": round(values["total_sales"], 2),
                "total_quantity": values["total_quantity"],
            }
            for period, values in sorted(aggregation.items())
        ]

        return {"status": "success", "aggregation": result}
    except Exception as e:
        logger.error(f"\U0001f6e0 [TOOL] get_orders_of_product error: {e}")
        return {"status": "error", "error_message": str(e)}
