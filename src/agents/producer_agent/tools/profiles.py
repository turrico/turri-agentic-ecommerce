from google.adk.tools.tool_context import ToolContext
from loguru import logger

from src.turri_data_hub.recommendation_system.get_profiles_of_producer import (
    get_customer_profiles_of_producer,
)
from src.turri_data_hub.recommendation_system.models import UserBehavior

from ...db import db
from ...utils import format_tool_args


async def get_customer_profiles(
    tool_context: ToolContext,
):
    """
    This function returns up to 50 customer profile descriptions of customers who have ordered at least a single
    product from the producer.

        dict: {
            "status": "success",
            "profiles": [str],
        }
        or
        dict: {"status": "error", "error_message": str} on failure.
    """
    logger.info(format_tool_args("get_customer_profiles", tool_context=tool_context))
    try:
        producer_id = tool_context.state.get("producer_id")
        if not producer_id:
            raise RuntimeError("state.producer_id must be set")

        profiles: list[UserBehavior] = await get_customer_profiles_of_producer(
            db=db, producer_id=producer_id
        )

        return {
            "status": "success",
            "profiles": [i.description for i in profiles[:50]],
        }
    except Exception as e:
        logger.error(f"\U0001f6e0 [TOOL] get_customer_profiles error: {e}")
        return {"status": "error", "error_message": str(e)}
