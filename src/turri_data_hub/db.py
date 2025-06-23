from typing import Literal, Type

from loguru import logger
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel, select, text

import src.turri_data_hub.chatbot.models  # noqa: F401
import src.turri_data_hub.google_analytics.models  # noqa: F401
import src.turri_data_hub.recommendation_system.models  # noqa: F401
import src.turri_data_hub.woocommerce.models  # noqa: F401
from src.turri_data_hub.settings import settings


class TurriDB:
    """
    Handles all database operations related to chat requests using SQLModel.
    """

    def __init__(self):
        self.engine = create_async_engine(
            settings.get_postgres_dsn(driver_name="asyncpg")
        )

        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False)

    async def initialize_db(self) -> None:
        """
        Initializes the database schema and ensures the 'vector' extension exists.
        Call this after creating an instance.
        """
        async with self.engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            await conn.run_sync(SQLModel.metadata.create_all)
        logger.info(
            "Database tables created (if they didn't exist), and 'vector' extension ensured."
        )

    async def save_all(self, data: list[Type[SQLModel]]) -> None:
        """
        Saves a list of SQLModel instances to the database.
        """

        async with self.session_maker() as sess:
            for obj in data:
                await sess.merge(obj)
            await sess.commit()

    async def save(self, resp: Type[SQLModel]) -> None:
        async with self.session_maker() as sess:
            await sess.merge(resp)
            await sess.commit()

    async def refresh_all(self):
        """
        Drops all tables and recreates them. Use with caution.
        """
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)
            await conn.run_sync(SQLModel.metadata.create_all)
        logger.info("Database refreshed (all tables dropped and recreated).")

    async def check_health(self) -> bool:
        """
        Performs a simple database health check by executing a trivial query.
        """
        try:
            async with self.engine.connect() as conn:
                await conn.execute(select(1))
            return True
        except Exception as e:
            logger.error(f"DB health check failed: {e}")
            return False

    async def query_table(
        self,
        table_model: Type[SQLModel],
        where_clauses: list = None,
        order_by: list = None,
        limit: None | int = None,
        mode: Literal["all", "first"] = "all",
        options: list = None,
    ) -> list[SQLModel] | SQLModel | None:
        async with self.session_maker() as session:
            statement = select(table_model)
            if options:
                for opt in options:
                    statement = statement.options(opt)
            if where_clauses:
                for clause in where_clauses:
                    statement = statement.where(clause)
            if order_by:
                for order in order_by:
                    statement = statement.order_by(order)
            if limit:
                statement = statement.limit(limit)
            result = await session.execute(statement)
            if mode == "first":
                return result.scalars().first()
            return list(result.scalars().all())
