from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from src.api.endpoints.admin import admin_router
from src.api.endpoints.customer import customer_router
from src.api.endpoints.producer import producer_router
from src.api.rate_limiter import RateLimiter
from src.api.settings import settings
from src.turri_data_hub.db import TurriDB


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager for application startup and shutdown events.
    Initializes database, rate limiter, and observability tools.
    """
    logger.info("Application startup: Initializing resources...")

    app.state.rate_limiter = RateLimiter(
        redis_host=settings.REDIS_HOST,
        redis_port=settings.REDIS_PORT,
        per_day=settings.MESSAGES_PER_DAY,
        per_minute=settings.MESSAGES_PER_MINUTE,
    )
    assert app.state.rate_limiter.check_health()
    app.state.db = TurriDB()
    assert await app.state.db.check_health()
    await app.state.db.initialize_db()
    yield

    logger.info("Application shutdown complete.")


app = FastAPI(lifespan=lifespan)
app.include_router(customer_router)
app.include_router(producer_router)
app.include_router(admin_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to your domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check(request: Request):
    db: TurriDB = request.app.state.db

    db_healthy = await db.check_health()

    if not db_healthy:
        raise HTTPException(status_code=503, detail="Database connection failed")

    rate_limiter: RateLimiter = app.state.rate_limiter
    rate_limiter_healthy = rate_limiter.check_health()

    if not rate_limiter_healthy:
        raise HTTPException(
            status_code=503, detail="Ratelimiter Redis connection failed"
        )

    return {"status": "ok", "database_status": "ok", "rate_limiter_status": "ok"}
