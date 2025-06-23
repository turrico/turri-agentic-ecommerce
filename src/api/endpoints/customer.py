from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from loguru import logger

from src.agents.customer_agent.main import (
    get_normal_conversation_response,
    get_onboarding_conversation_response,
)
from src.turri_data_hub.db import TurriDB
from src.turri_data_hub.recommendation_system.get_recommendations import (
    get_top_k_producers,
    get_top_k_products,
)
from src.turri_data_hub.recommendation_system.models import UserBehavior
from src.turri_data_hub.recommendation_system.process_onboarding import (
    process_onboarding,
)

from ..models import (
    ChatAnswer,
    ChatRequestFrontend,
    PlainText,
    ProducerComponent,
    ProductComponent,
)
from ..rate_limiter import RateLimiter

customer_router = APIRouter(
    prefix="/customer",
    tags=["customer"],
)


@customer_router.post("/chat")
async def customer_chat(req: ChatRequestFrontend, request: Request):
    """
    Handles incoming chat messages, applies rate limiting, processes the request
    through the chatbot graph, and returns the AI's answer.
    """

    logger.debug(f"Got new requst: {req.message}")

    rate_limiter: RateLimiter = request.app.state.rate_limiter

    if not rate_limiter.check(req.user_id):
        raise HTTPException(429, "rate limit exceeded")

    new_session = req.session_uuid is None
    session_uuid = req.session_uuid or uuid4()

    components = await get_normal_conversation_response(
        user_id=req.user_id,
        session_id=str(session_uuid),
        message=req.message,
        new_session=new_session,
    )

    return ChatAnswer(
        session_uuid=session_uuid,
        answer=components,
        answered_at=datetime.now(),
    )


@customer_router.get("/is-onboarded")
async def customer_is_onboared(user_id: int, request: Request) -> bool:
    db: TurriDB = request.app.state.db

    behaviour: UserBehavior = await db.query_table(
        UserBehavior, where_clauses=[UserBehavior.user_id == user_id], mode="first"
    )

    return behaviour is not None and behaviour.is_onboarded


@customer_router.post("/onboarding-chat")
async def onboarding_chat(req: ChatRequestFrontend, request: Request):
    logger.debug(f"Got new requst: {req.message}")

    rate_limiter: RateLimiter = request.app.state.rate_limiter

    if not rate_limiter.check(req.user_id):
        raise HTTPException(429, "rate limit exceeded")

    new_session = req.session_uuid is None
    session_uuid = req.session_uuid or uuid4()

    components, state = await get_onboarding_conversation_response(
        user_id=req.user_id,
        session_id=str(session_uuid),
        message=req.message,
        new_session=new_session,
    )

    if not state.get("stop_onboarding", False):
        return ChatAnswer(
            session_uuid=session_uuid,
            answer=components,
            answered_at=datetime.now(),
        )

    try:
        await process_onboarding(
            db=request.app.state.db,
            user_id=req.user_id,
            user_profile_description=state["user_profile_description"],
            taste_embeddings=state["taste_embeddings"],
        )
        return ChatAnswer(
            session_uuid=session_uuid,
            answer=components,
            answered_at=datetime.now(),
            stop_chat=True,
        )
    except Exception as e:
        logger.exception(f"Failed to process onbaroding: {e}")
    return ChatAnswer(
        session_uuid=session_uuid,
        answer=[PlainText(text="Something went wrong, try again!")],
        answered_at=datetime.now(),
        stop_chat=True,
    )


@customer_router.get("/recommendations/products")
async def customer_product_recommendations(
    user_id: int,
    k: int,
    request: Request,
) -> list[ProductComponent]:
    """
    Returns top-k product recommendations for a customer.
    """
    db: TurriDB = request.app.state.db
    behaviour: UserBehavior = await db.query_table(
        UserBehavior, where_clauses=[UserBehavior.user_id == user_id], mode="first"
    )
    if not behaviour or not behaviour.is_onboarded:
        raise HTTPException(404, "User not onboarded or not found")
    products = await get_top_k_products(db, behaviour, k)
    return [
        ProductComponent(
            product_id=p.id,
            display_content=None,
            link=p.link,
            img_url=p.img_url,
            producer_link=p.producer.link if p.producer else "",
            producer_name=p.producer.title if p.producer else "",
            title=p.title,
        )
        for p in products
    ]


@customer_router.get("/recommendations/producers")
async def customer_producer_recommendations(
    user_id: int,
    k: int,
    request: Request,
) -> list[ProducerComponent]:
    """
    Returns top-k producer recommendations for a customer.
    """
    db: TurriDB = request.app.state.db
    behaviour: UserBehavior = await db.query_table(
        UserBehavior, where_clauses=[UserBehavior.user_id == user_id], mode="first"
    )
    if not behaviour or not behaviour.is_onboarded:
        raise HTTPException(404, "User not onboarded or not found")
    producers = await get_top_k_producers(db, behaviour, k)
    return [
        ProducerComponent(
            producer_id=p.id,
            display_content=None,
            link=p.link,
            img_url=p.img_url,
            title=p.title,
        )
        for p in producers
    ]
