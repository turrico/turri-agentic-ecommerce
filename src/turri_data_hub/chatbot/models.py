from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Column, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class ChatbotMention(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ts: datetime = Field(index=True)
    entity_type: str = Field(index=True)
    entity_id: int = Field(index=True)
    user_id: Optional[int] = Field(default=None, index=True)
    extra: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSONB))

    __table_args__ = (
        Index("idx_entity_ts", "entity_type", "ts"),
        Index("idx_entity_entity_ts", "entity_type", "entity_id", "ts"),
        Index("idx_entity_entity", "entity_type", "entity_id"),
        Index("idx_user_entity_ts", "user_id", "entity_type", "ts"),
    )
