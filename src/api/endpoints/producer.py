from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Request
from loguru import logger

from src.agents.producer_agent.main import get_producer_conversation_response
from src.turri_data_hub.db import TurriDB
from src.turri_data_hub.recommendation_system.get_profiles_of_producer import (
    get_customer_profiles_of_producer,
)
from src.turri_data_hub.recommendation_system.models import UserBehavior

from ..models import ChatAnswer, ChatRequestFrontend

producer_router = APIRouter(
    prefix="/producer",
    tags=["producer"],
)


@producer_router.get("/customer-profiles")
async def get_user_beavhoiours(
    producer_id: int, request: Request
) -> list[UserBehavior]:
    """
    For all users who have ever ordered any product of the producer,
    if they have a user behavior (old users don't), return the user behavior.
    """
    db: TurriDB = request.app.state.db

    return await get_customer_profiles_of_producer(db=db, producer_id=producer_id)


@producer_router.post("/chat")
async def producer_chat(req: ChatRequestFrontend, request: Request) -> ChatAnswer:
    """
    Handles incoming chat messages for the producer agent and returns a plain text response.
    """
    logger.debug(f"Got new producer chat request: {req.message}")

    new_session = req.session_uuid is None
    session_uuid = req.session_uuid or uuid4()

    response = await get_producer_conversation_response(
        producer_id=req.user_id,
        session_id=str(session_uuid),
        message=req.message,
        new_session=new_session,
    )
    return ChatAnswer(
        session_uuid=session_uuid,
        answer=response,
        answered_at=datetime.now(),
    )
