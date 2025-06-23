from datetime import datetime
from typing import Literal

from google.genai import types
from loguru import logger

from src.agents.utils import gemini_only_text

from ..db import TurriDB
from ..embedding import compute_embeddings
from .models import UserBehavior

ALPHA = 0.8


UPDATE_USER_DESCRIPTIONS_SYSTEM_PROMPT = f"""
You are helping to update the user profile descriptions of our online website.
This is the current description of the user's browsing, ordering, and chatbot behavior.
Your job is to update the user behavior based on new data. Try to keep
the user behavior concise, maximum 3 sentences like:

The user likes dark coffee, mainly orders it at our website. He says himself that he values organic and traditional approaches
and spends most time browsing on the website of ''.

When updating the old text to the new, try to keep around {ALPHA * 100:.2f}% of the content of the old text.
"""


async def update_user_profile(
    db: TurriDB,
    user_id: TurriDB,
    new_description: str,
    new_taste_embedding: list[float],
    source: Literal["chatbot", "woocommerce", "google"],
):
    if source not in ["chatbot", "woocommerce", "google"]:
        raise ValueError("source was wrong")

    source_to_keys = {
        "chatbot": "last_chatbot_update",
        "woocommerce": "last_woocommerce_update",
        "google": "last_google_update",
    }

    profile: UserBehavior = await db.query_table(
        UserBehavior, where_clauses=[UserBehavior.user_id == user_id], mode="first"
    )

    if not profile:
        logger.debug(f"No profile found for {user_id}, creating new one")
        embeddings = await compute_embeddings([new_description])

        date_kwargs = {source_to_keys[source]: datetime.now()}

        profile = UserBehavior(
            user_id=user_id,
            description=new_description,
            embedding=embeddings[0],
            taste_embedding=new_taste_embedding,
            **date_kwargs,
        )
        await db.save(profile)
        return

    old_description = profile.description
    profile.description = await gemini_only_text(
        "gemini-2.0-flash",
        contents=[
            types.Content(
                parts=[
                    types.Part(text=f"The old description: {profile.description}"),
                    types.Part(text=f"The new description: {new_description}"),
                ]
            )
        ],
        system_message=UPDATE_USER_DESCRIPTIONS_SYSTEM_PROMPT,
    )

    logger.debug(
        f"Updated user profile for user {user_id}. Old descriptions:\n{old_description}\nNew:\n{new_description}\nUpdated:\n{profile.description}"
    )

    embeddings = await compute_embeddings([profile.description])
    profile.embedding = embeddings[0]
    profile.taste_embedding = [
        old * ALPHA + new * (1 - ALPHA)
        for old, new in zip(profile.taste_embedding, new_taste_embedding)
    ]

    setattr(profile, source_to_keys[source], datetime.now())

    await db.save(profile)
