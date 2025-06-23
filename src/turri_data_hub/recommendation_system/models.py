from datetime import datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlmodel import Column, Field, SQLModel

from ..embedding import EMBEDDING_DIM
from .taste_categories import TASTE_KEYS


class UserBehavior(SQLModel, table=True):
    user_id: int = Field(primary_key=True)
    description: str
    embedding: list[float] = Field(sa_column=Column(Vector(EMBEDDING_DIM)))
    taste_embedding: list[float] = Field(sa_column=Column(Vector(len(TASTE_KEYS))))
    last_google_update: Optional[datetime] = None
    last_woocommerce_update: Optional[datetime] = None
    last_chatbot_update: Optional[datetime] = None
    is_onboarded: bool = Field(False)
