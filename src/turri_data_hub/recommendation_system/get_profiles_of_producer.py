from sqlalchemy import distinct, select

from ..db import TurriDB
from ..woocommerce.models import LineItem, Order, Product
from .models import UserBehavior


async def get_customer_profiles_of_producer(
    db: TurriDB, producer_id: int
) -> list[UserBehavior]:
    product_ids = await db.query_table(
        Product, where_clauses=[Product.producer_id == producer_id], mode="all"
    )
    product_ids = [p.id for p in product_ids]
    if not product_ids:
        return []

    # 2. Get all customer ids who have ordered these products
    # We need to join Order -> LineItem -> Product, but for simplicity, we can use a raw query
    async with db.session_maker() as session:
        stmt = (
            select(distinct(Order.customer_id))
            .join(Order.line_items)
            .where(LineItem.product_id.in_(product_ids))
        )
        result = await session.execute(stmt)
        customer_ids = [row[0] for row in result.fetchall() if row[0] is not None]

    if not customer_ids:
        return []

    # 3. Get all UserBehavior for these customer ids
    res: list[UserBehavior] = await db.query_table(
        UserBehavior, where_clauses=[UserBehavior.user_id.in_(customer_ids)], mode="all"
    )
    for profile in res:
        profile.embedding = profile.embedding.tolist()
        profile.taste_embedding = profile.taste_embedding.tolist()

    return res
