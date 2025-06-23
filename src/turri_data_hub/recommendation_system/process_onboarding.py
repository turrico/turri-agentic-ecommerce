from datetime import datetime

from ..db import TurriDB
from ..embedding import compute_embeddings
from .models import UserBehavior


async def process_onboarding(
    db: TurriDB,
    user_id: int,
    user_profile_description: str,
    taste_embeddings: list[float],
) -> None:
    desc_embedding = await compute_embeddings([user_profile_description])

    behaviour = UserBehavior(
        taste_embedding=taste_embeddings,
        embedding=desc_embedding[0],
        description=user_profile_description,
        last_chatbot_update=datetime.now(),
        is_onboarded=True,
        user_id=user_id,
    )
    await db.save(behaviour)
