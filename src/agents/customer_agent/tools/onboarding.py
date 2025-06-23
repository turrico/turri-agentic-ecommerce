import json

from google.adk.tools import ToolContext
from loguru import logger

from src.turri_data_hub.recommendation_system.taste_categories import TASTE_KEYS

from ...utils import format_tool_args


def finish_onboarding_process(
    user_profile_description: str, user_categorization: str, tool_context: ToolContext
):
    """Calling this function marks the stop of the onboarding process.

    Args:
        user_profile_description (str): A description of the User's Profile
        user_categorization (str):  A float categorization of 0-1 (0 = no interest, 1 = highest interest), for all these categories in json format:
            Gourmet, Orgánico, Saludable, Sin, Sostenible, Tradicional, Café, Bebidas, Dulces, Lácteos, Huevos, Queso Turrialba, Salsas,
    """
    logger.info(
        format_tool_args(
            "finish_onboarding_process",
            user_profile_description=user_profile_description,
            user_categorization=user_categorization,
            tool_context=tool_context,
        )
    )
    try:
        taste_embeddings = json.loads(user_categorization)
        if not isinstance(taste_embeddings, dict):
            raise ValueError(
                "user_categorization must be a JSON object (dict) with taste keys as fields."
            )
    except Exception as e:
        logger.error(f"\U0001f6e0 [TOOL] finish_onboarding_process error: {e}")
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

    tool_context.state["stop_onboarding"] = True
    tool_context.state["user_profile_description"] = user_profile_description
    tool_context.state["taste_embeddings"] = [
        taste_embeddings[key] for key in TASTE_KEYS
    ]
    logger.success(
        f"Onboarding for user: {tool_context.state.get('user:user_id')} finished!\n"
        f"user_profile_description: {user_profile_description}\n"
        f"taste_embeddings: {taste_embeddings}\n"
    )

    return {"status": "complete"}
