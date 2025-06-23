import json

from google.adk.tools.tool_context import ToolContext
from loguru import logger

from src.turri_data_hub.recommendation_system.get_recommendations import (
    get_top_k_producers,
    get_top_k_products,
)
from src.turri_data_hub.recommendation_system.models import UserBehavior
from src.turri_data_hub.recommendation_system.taste_categories import TASTE_KEYS
from src.turri_data_hub.recommendation_system.update_profile import (
    update_user_profile as _update_user_profile,
)

from ...db import db
from ...utils import format_tool_args, make_numpy_values_serialiable
from .utils import _products_to_dict, dump_producer


async def get_user_profile(tool_context: ToolContext) -> dict:
    """
    Fetch the recorded User Behavior of the current customer you are chatting with.

    Returns:
        dict: {'status': 'success', 'description': "A text description of the behavior", "tastes": "Ranking of user taste along key word axis from 0 (low) to max of 1"} on success,
              {'status': 'error', 'error_message': str} on failure.
    """
    logger.info(format_tool_args("get_user_profile", tool_context=tool_context))

    try:
        user_id = tool_context.state.get("user:user_id")
        if not user_id:
            return {
                "status": "error",
                "error_message": "No user_id found in session state.",
            }

        profile: UserBehavior = await db.query_table(
            UserBehavior, where_clauses=[UserBehavior.user_id == user_id], mode="first"
        )

        if not profile:
            return {
                "status": "error",
                "error_message": "There exists no profile for the current user.",
            }

        return make_numpy_values_serialiable(
            {
                "status": "success",
                "description": profile.description,
                "tastes": dict(zip(TASTE_KEYS, profile.taste_embedding)),
            }
        )

    except Exception as e:
        logger.error(f"\U0001f6e0 [TOOL] get_user_profile error: {e}")
        return {"status": "error", "error_message": str(e)}


async def update_user_profile(
    user_profile_description: str, user_categorization: str, tool_context: ToolContext
):
    """
    Call this function when you think that the user's current behavior differs significantly
    from their profile and we should update their profile, or when they explicitly wish to receive other recommendations.

    Args:
        user_profile_description (str): A new description of the User's Profile.
        user_categorization (str):  A new float categorization of 0-1 (0 = no interest, 1 = highest interest), for all these categories in JSON format:
            Gourmet, Orgánico, Saludable, Sin, Sostenible, Tradicional, Café, Bebidas, Dulces, Lácteos, Huevos, Queso Turrialba, Salsas.
    Returns:
        dict: {'status': 'complete'} on success, or error dict on failure.
    """
    logger.info(
        format_tool_args(
            "update_user_profile",
            user_profile_description=user_profile_description,
            user_categorization=user_categorization,
            tool_context=tool_context,
        )
    )

    user_id = tool_context.state.get("user:user_id")
    if not user_id:
        return {
            "status": "error",
            "error_message": "No user_id found in session state.",
        }

    try:
        taste_embeddings = json.loads(user_categorization)
        if not isinstance(taste_embeddings, dict):
            raise ValueError(
                "user_categorization must be a JSON object (dict) with taste keys as fields."
            )
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to deserialize user_categorization as JSON: {e}. Input was: {user_categorization}",
        }

    missing = [i for i in TASTE_KEYS if i not in taste_embeddings]
    if missing:
        return {
            "status": "error",
            "error": f"user_categorization is missing required taste keys: {missing}. Received keys: {list(taste_embeddings.keys())}",
        }

    for key, val in taste_embeddings.items():
        if not isinstance(val, (int, float)):
            return {
                "status": "error",
                "error": f"Value for '{key}' must be a number between 0 and 1. Got: {val} ({type(val).__name__})",
            }
        if val < 0 or val > 1:
            return {
                "status": "error",
                "error": f"Value for '{key}' must be between 0 and 1. Got: {val}",
            }

    try:
        await _update_user_profile(
            db=db,
            user_id=user_id,
            new_description=user_profile_description,
            new_taste_embedding=[taste_embeddings[key] for key in TASTE_KEYS],
            source="chatbot",
        )
        return {"status": "complete"}

    except Exception as e:
        logger.error(f"\U0001f6e0 [TOOL] update_user_profile error: {e}")
        return {
            "status": "failure",
            "error": "The updating functionality failed internally; this is independent of you.",
        }


async def get_personalized_product_recommendations_for_user(tool_context: ToolContext):
    """
    Get personalized product recommendations for the current user.

    Returns:
        dict: {'status': 'success', 'products': [product_dicts]} on success,
              {'status': 'failure', 'error': str} on failure.
    """
    logger.info(
        format_tool_args(
            "get_personalized_product_recommendations_for_user",
            tool_context=tool_context,
        )
    )

    user_id = tool_context.state.get("user:user_id")
    if not user_id:
        return {
            "status": "error",
            "error_message": "No user_id found in session state.",
        }

    try:
        profile: UserBehavior = await db.query_table(
            UserBehavior, where_clauses=[UserBehavior.user_id == user_id], mode="first"
        )

        if not profile:
            return {
                "status": "error",
                "error_message": "There exists no profile for the current user.",
            }
        recommendations = await get_top_k_products(db=db, user=profile, k=5)
        result = {"status": "success", "products": _products_to_dict(recommendations)}
        return make_numpy_values_serialiable(result)

    except Exception as e:
        logger.error(
            f"\U0001f6e0 [TOOL] get_personalized_product_recommendations_for_user error: {e}"
        )
        return {
            "status": "failure",
            "error": "The updating functionality failed internally; this is independent of you.",
        }


async def get_personalized_producer_recommendations_for_user(tool_context: ToolContext):
    """
    Get personalized producer recommendations for the current user.

    Returns:
        dict: {'status': 'success', 'producers': [producer_dicts]} on success,
              {'status': 'failure', 'error': str} on failure.
    """
    logger.info(
        format_tool_args(
            "get_personalized_producer_recommendations_for_user",
            tool_context=tool_context,
        )
    )

    user_id = tool_context.state.get("user:user_id")
    if not user_id:
        return {
            "status": "error",
            "error_message": "No user_id found in session state.",
        }

    try:
        profile: UserBehavior = await db.query_table(
            UserBehavior, where_clauses=[UserBehavior.user_id == user_id], mode="first"
        )

        if not profile:
            return {
                "status": "error",
                "error_message": "There exists no profile for the current user.",
            }
        recommendations = await get_top_k_producers(db=db, user=profile, k=5)
        result = {
            "status": "success",
            "producers": [dump_producer(p) for p in recommendations],
        }
        return make_numpy_values_serialiable(result)

    except Exception as e:
        logger.error(
            f"\U0001f6e0 [TOOL] get_personalized_producer_recommendations_for_user error: {e}"
        )
        return {
            "status": "failure",
            "error": "The updating functionality failed internally; this is independent of you.",
        }
