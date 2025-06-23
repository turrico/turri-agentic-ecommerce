import asyncio

from google.adk.tools.tool_context import ToolContext
from loguru import logger
from sqlalchemy import desc
from sqlalchemy.orm import selectinload

from src.turri_data_hub.woocommerce.models import Order, Product

from ...db import db
from ...utils import format_tool_args, make_numpy_values_serialiable


async def get_active_or_last_orders(tool_context: ToolContext) -> dict:
    """
    Fetches the active (open) orders for the current user. If none are found, returns the most recent order.

    Use this tool to retrieve the user's current active order(s), or their last order if none are active.

    Args:
        tool_context (ToolContext): The tool context containing session state, including user:user_id.

    Returns:
        dict: {'status': 'success', 'orders': [order_dicts]} on success,
              {'status': 'error', 'error_message': str} on failure.
    """
    logger.info(
        format_tool_args("get_active_or_last_orders", tool_context=tool_context)
    )

    async def _dump_order(order: Order):
        val = order.model_dump(
            include=[
                "id",
                "date_created",
                "status",
                "total",
                "currency",
            ]
        )
        val["line_items"] = []
        for line_item in order.line_items:
            product = await db.query_table(
                Product,
                where_clauses=[Product.id == line_item.product_id],
                mode="first",
            )

            item = line_item.model_dump()
            if product:
                item["product"] = product.model_dump(
                    include=[
                        "id",
                        "title",
                        "content",
                        "description",
                        "producer_id",
                        "price",
                        "tags",
                        "categories",
                    ]
                )
            val["line_items"].append(item)

        return val

    try:
        user_id = tool_context.state.get("user:user_id")
        if not user_id:
            return {
                "status": "error",
                "error_message": "No user_id found in session state.",
            }

        # Fetch active orders (status: 'pending', 'processing', 'on-hold')
        active_statuses = ["pending", "processing", "on-hold"]
        active_orders = await db.query_table(
            Order,
            where_clauses=[
                Order.customer_id == user_id,
                Order.status.in_(active_statuses),
            ],
            order_by=[desc(Order.date_created)],
            options=[selectinload(Order.line_items)],
            limit=5,
        )

        if active_orders:
            orders = await asyncio.gather(*[_dump_order(o) for o in active_orders])
            result = {"status": "success", "orders": orders[-1:]}
            return make_numpy_values_serialiable(result)

        # If no active orders, fetch the most recent order
        last_orders = await db.query_table(
            Order,
            where_clauses=[Order.customer_id == user_id],
            order_by=[desc(Order.date_created)],
            options=[selectinload(Order.line_items)],
            limit=1,
        )
        if last_orders:
            orders = await asyncio.gather(*[_dump_order(o) for o in last_orders])
            result = {"status": "success", "orders": orders}
            return make_numpy_values_serialiable(result)

        logger.info(
            "get_active_or_last_orders result: {'status': 'success', 'orders': []}"
        )
        return {"status": "success", "orders": []}
    except Exception as e:
        logger.error(f"\U0001f6e0 [TOOL] get_active_or_last_orders error: {e}")
        return {"status": "error", "error_message": str(e)}
