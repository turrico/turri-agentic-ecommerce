from datetime import datetime
from typing import Optional

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class PageGoogleAnalyticsData(SQLModel, table=True):
    url: str = Field(index=True, primary_key=True)
    producer_id: Optional[int] = Field(index=True)
    product_id: Optional[int] = Field(index=True)

    visits_over_time: Optional[dict] = Field(
        sa_column=Column(JSONB), default_factory=dict
    )
    user_and_regions: Optional[dict] = Field(
        sa_column=Column(JSONB), default_factory=dict
    )
    last_updated: datetime
